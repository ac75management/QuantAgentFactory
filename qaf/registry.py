import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


class Registry:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,timeout=30,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS trials (run_id TEXT PRIMARY KEY, day TEXT NOT NULL, campaign TEXT NOT NULL, status TEXT NOT NULL, spec_json TEXT NOT NULL, result_path TEXT, error TEXT, reserved_at TEXT, attempt_id TEXT)')
        columns = {row['name'] for row in self.db.execute('PRAGMA table_info(trials)')}
        for column in ('reserved_at', 'attempt_id'):
            if column not in columns:
                self.db.execute(f'ALTER TABLE trials ADD COLUMN {column} TEXT')
        self._leases = {}

    def reserve(self,run_id,day,campaign,spec_json,daily_budget,total_budget,stale_after_seconds=3600):
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(seconds=stale_after_seconds)).isoformat()
        attempt_id = uuid4().hex
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT status, reserved_at FROM trials WHERE run_id=?',(run_id,)).fetchone()
            if row:
                # Una reserva RUNNING mas vieja que el umbral se asume abandonada
                # (proceso caido entre reserve() y finish()): se recupera en vez
                # de bloquear ese run_id para siempre.
                stale = row['status']=='RUNNING' and (not row['reserved_at'] or row['reserved_at']<cutoff)
                if not stale:
                    self.db.execute('COMMIT');return 'DUPLICATE'
                self.db.execute('DELETE FROM trials WHERE run_id=?',(run_id,))
            daily=self.db.execute('SELECT count(*) FROM trials WHERE day=? AND campaign=? AND NOT (status="RUNNING" AND (reserved_at IS NULL OR reserved_at<?))',(day,campaign,cutoff)).fetchone()[0]
            total=self.db.execute('SELECT count(*) FROM trials WHERE campaign=? AND NOT (status="RUNNING" AND (reserved_at IS NULL OR reserved_at<?))',(campaign,cutoff)).fetchone()[0]
            if daily>=daily_budget or total>=total_budget:
                self.db.execute('COMMIT');return 'BUDGET'
            self.db.execute('INSERT INTO trials (run_id,day,campaign,status,spec_json,result_path,error,reserved_at,attempt_id) VALUES (?,?,?,?,?,?,?,?,?)',(run_id,day,campaign,'RUNNING',spec_json,None,None,now.isoformat(),attempt_id))
            self.db.execute('COMMIT')
            self._leases[run_id] = attempt_id
            return 'RESERVED'
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def finish(self,run_id,status,path,error=None):
        attempt_id = self._leases.get(run_id)
        if not attempt_id:
            raise RuntimeError(f"No hay lease local para finalizar {run_id}")
        cursor = self.db.execute('UPDATE trials SET status=?,result_path=?,error=? WHERE run_id=? AND attempt_id=? AND status="RUNNING"',(status,str(path),error,run_id,attempt_id))
        if cursor.rowcount != 1:
            raise RuntimeError(f"Lease perdido para {run_id}; otro proceso recupero la reserva")
        self._leases.pop(run_id, None)

    def rows(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM trials ORDER BY day,run_id')]

    def close(self):
        self.db.close()
