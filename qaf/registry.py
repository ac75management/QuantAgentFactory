import sqlite3
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
        self.db.execute('CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, run_id TEXT, hypothesis_id TEXT, stage TEXT NOT NULL, owner TEXT NOT NULL, status TEXT NOT NULL, reason_code TEXT, reason_text TEXT, input_refs TEXT NOT NULL DEFAULT "[]", output_refs TEXT NOT NULL DEFAULT "[]", started_at TEXT, heartbeat_at TEXT, finished_at TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, created_at TEXT NOT NULL, event_type TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT "{}")')
        self.db.execute('CREATE INDEX IF NOT EXISTS events_task_created ON events(task_id,created_at)')
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

    def start_task(self,task_id,run_id,hypothesis_id,stage,owner,input_refs='[]'):
        now=datetime.now(timezone.utc).isoformat()
        self.db.execute(
            'INSERT INTO tasks (task_id,run_id,hypothesis_id,stage,owner,status,input_refs,started_at,heartbeat_at) VALUES (?,?,?,?,?,?,?,?,?) '
            'ON CONFLICT(task_id) DO UPDATE SET run_id=excluded.run_id,hypothesis_id=excluded.hypothesis_id,stage=excluded.stage,owner=excluded.owner,status="running",reason_code=NULL,reason_text=NULL,input_refs=excluded.input_refs,started_at=excluded.started_at,heartbeat_at=excluded.heartbeat_at,finished_at=NULL',
            (task_id,run_id,hypothesis_id,stage,owner,'running',input_refs,now,now),
        )
        self.emit_event(task_id,'started',{'stage':stage,'owner':owner})

    def queue_task(self,task_id,hypothesis_id,stage,owner,input_refs='[]',reason_text=None):
        """Register requested work without pretending that an agent is running."""
        now=datetime.now(timezone.utc).isoformat()
        cursor=self.db.execute(
            'INSERT INTO tasks (task_id,run_id,hypothesis_id,stage,owner,status,reason_text,input_refs,heartbeat_at) VALUES (?,?,?,?,?,?,?,?,?) '
            'ON CONFLICT(task_id) DO NOTHING',
            (task_id,None,hypothesis_id,stage,owner,'queued',reason_text,input_refs,now),
        )
        if cursor.rowcount:
            self.emit_event(task_id,'queued',{'stage':stage,'owner':owner})
            return True
        return False

    def finish_task(self,task_id,status,reason_code=None,reason_text=None,output_refs='[]'):
        if status not in {'blocked','failed','completed','cancelled'}:
            raise ValueError('Estado final de tarea invalido')
        now=datetime.now(timezone.utc).isoformat()
        cursor=self.db.execute(
            'UPDATE tasks SET status=?,reason_code=?,reason_text=?,output_refs=?,heartbeat_at=?,finished_at=? WHERE task_id=?',
            (status,reason_code,reason_text,output_refs,now,now,task_id),
        )
        if cursor.rowcount!=1:
            raise RuntimeError(f'Tarea inexistente: {task_id}')
        self.emit_event(task_id,status,{'reason_code':reason_code,'reason_text':reason_text})

    def emit_event(self,task_id,event_type,payload):
        import json
        now=datetime.now(timezone.utc).isoformat()
        self.db.execute('INSERT INTO events (task_id,created_at,event_type,payload_json) VALUES (?,?,?,?)',(task_id,now,event_type,json.dumps(payload,ensure_ascii=False,sort_keys=True)))

    def tasks(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM tasks ORDER BY COALESCE(started_at,"") DESC,task_id')]

    def events(self,limit=200):
        return [dict(r) for r in self.db.execute('SELECT * FROM events ORDER BY event_id DESC LIMIT ?',(int(limit),))]

    def close(self):
        self.db.close()
