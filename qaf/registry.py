import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Registry:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,timeout=30,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS trials (run_id TEXT PRIMARY KEY, day TEXT NOT NULL, campaign TEXT NOT NULL, status TEXT NOT NULL, spec_json TEXT NOT NULL, result_path TEXT, error TEXT)')

    def reserve(self,run_id,day,campaign,spec_json,daily_budget,total_budget):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute('SELECT 1 FROM trials WHERE run_id=?',(run_id,)).fetchone():
                self.db.execute('COMMIT');return 'DUPLICATE'
            daily=self.db.execute('SELECT count(*) FROM trials WHERE day=? AND campaign=?',(day,campaign)).fetchone()[0]
            total=self.db.execute('SELECT count(*) FROM trials WHERE campaign=?',(campaign,)).fetchone()[0]
            if daily>=daily_budget or total>=total_budget:
                self.db.execute('COMMIT');return 'BUDGET'
            self.db.execute('INSERT INTO trials VALUES (?,?,?,?,?,?,?)',(run_id,day,campaign,'RUNNING',spec_json,None,None))
            self.db.execute('COMMIT');return 'RESERVED'
        except BaseException:
            self.db.execute('ROLLBACK');raise

    def finish(self,run_id,status,path,error=None):
        self.db.execute('UPDATE trials SET status=?,result_path=?,error=? WHERE run_id=?',(status,str(path),error,run_id))

    def rows(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM trials ORDER BY day,run_id')]

    def close(self):
        self.db.close()
