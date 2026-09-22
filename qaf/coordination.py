"""Reservas atomicas de archivos para agentes que comparten un working tree.

AGENTS.md es la vista humana. Esta base SQLite ignorada por git es la fuente
operativa: dos procesos no pueden adquirir el mismo archivo a la vez. Las
reservas vencen solo despues de ``stale_minutes`` sin heartbeat; toda toma,
liberacion o recuperacion queda en el historial local.
"""
import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .io import ROOT


DEFAULT_STALE_MINUTES = 120


class ClaimConflict(RuntimeError):
    """Uno o mas archivos ya tienen una reserva vigente de otro agente."""


def _utcnow():
    return datetime.now(timezone.utc)


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _paths(root, paths):
    root = Path(root).resolve()
    normalized = []
    for value in paths:
        candidate = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
        try:
            relative = candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Ruta fuera del repositorio: {value}") from error
        key = relative.as_posix()
        if not key or key == ".":
            raise ValueError("Se requieren archivos concretos; no se puede reservar la raiz")
        normalized.append(key.casefold())
    if not normalized:
        raise ValueError("Se requiere al menos un archivo")
    if len(normalized) != len(set(normalized)):
        raise ValueError("La lista contiene rutas duplicadas")
    return sorted(normalized)


class Coordination:
    def __init__(self, root=ROOT, db_path=None):
        self.root = Path(root).resolve()
        path = Path(db_path) if db_path else self.root / "state/coordination.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=15000")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS active_claims(
                path TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                objective TEXT NOT NULL,
                started_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS claim_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL,
                event TEXT NOT NULL,
                path TEXT NOT NULL,
                agent TEXT NOT NULL,
                detail TEXT
            );
            """
        )

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def claim(self, agent, paths, objective, now=None, stale_minutes=DEFAULT_STALE_MINUTES):
        if not agent.strip() or not objective.strip():
            raise ValueError("agent y objective no pueden estar vacios")
        paths = _paths(self.root, paths)
        now = now or _utcnow()
        cutoff = now - timedelta(minutes=stale_minutes)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = {
                row["path"]: row
                for row in self.db.execute(
                    f"SELECT * FROM active_claims WHERE path IN ({','.join('?' for _ in paths)})", paths
                )
            }
            conflicts = []
            for path, row in rows.items():
                heartbeat = datetime.fromisoformat(row["heartbeat_at"])
                if row["agent"] != agent and heartbeat >= cutoff:
                    conflicts.append(f"{path} reservado por {row['agent']} desde {row['started_at']}")
            if conflicts:
                raise ClaimConflict("; ".join(conflicts))
            stamp = _stamp(now)
            for path in paths:
                previous = rows.get(path)
                if previous and previous["agent"] != agent:
                    self.db.execute(
                        "INSERT INTO claim_events(at,event,path,agent,detail) VALUES(?,?,?,?,?)",
                        (stamp, "STALE_TAKEOVER", path, agent, f"reserva anterior de {previous['agent']}")
                    )
                self.db.execute(
                    "INSERT INTO active_claims(path,agent,objective,started_at,heartbeat_at) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(path) DO UPDATE SET agent=excluded.agent, objective=excluded.objective, "
                    "started_at=CASE WHEN active_claims.agent=excluded.agent THEN active_claims.started_at ELSE excluded.started_at END, "
                    "heartbeat_at=excluded.heartbeat_at",
                    (path, agent, objective, stamp, stamp),
                )
                self.db.execute(
                    "INSERT INTO claim_events(at,event,path,agent,detail) VALUES(?,?,?,?,?)",
                    (stamp, "CLAIM", path, agent, objective),
                )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return self.for_agent(agent)

    def heartbeat(self, agent, paths=None, now=None):
        selected = _paths(self.root, paths) if paths else None
        stamp = _stamp(now or _utcnow())
        self.db.execute("BEGIN IMMEDIATE")
        try:
            query = "SELECT path FROM active_claims WHERE agent=?"
            args = [agent]
            if selected:
                query += f" AND path IN ({','.join('?' for _ in selected)})"
                args.extend(selected)
            owned = [row[0] for row in self.db.execute(query, args)]
            if selected and set(owned) != set(selected):
                missing = sorted(set(selected) - set(owned))
                raise ClaimConflict(f"{agent} no posee: {', '.join(missing)}")
            for path in owned:
                self.db.execute("UPDATE active_claims SET heartbeat_at=? WHERE path=?", (stamp, path))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return owned

    def release(self, agent, paths=None, result="terminado", now=None):
        selected = _paths(self.root, paths) if paths else None
        stamp = _stamp(now or _utcnow())
        self.db.execute("BEGIN IMMEDIATE")
        try:
            query = "SELECT path FROM active_claims WHERE agent=?"
            args = [agent]
            if selected:
                query += f" AND path IN ({','.join('?' for _ in selected)})"
                args.extend(selected)
            owned = [row[0] for row in self.db.execute(query, args)]
            if selected and set(owned) != set(selected):
                missing = sorted(set(selected) - set(owned))
                raise ClaimConflict(f"{agent} no puede liberar una reserva ajena o inexistente: {', '.join(missing)}")
            for path in owned:
                self.db.execute("DELETE FROM active_claims WHERE path=?", (path,))
                self.db.execute(
                    "INSERT INTO claim_events(at,event,path,agent,detail) VALUES(?,?,?,?,?)",
                    (stamp, "RELEASE", path, agent, result),
                )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return owned

    def active(self, now=None, stale_minutes=DEFAULT_STALE_MINUTES):
        cutoff = (now or _utcnow()) - timedelta(minutes=stale_minutes)
        rows = []
        for row in self.db.execute("SELECT * FROM active_claims ORDER BY path"):
            item = dict(row)
            item["stale"] = datetime.fromisoformat(item["heartbeat_at"]) < cutoff
            rows.append(item)
        return rows

    def for_agent(self, agent):
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM active_claims WHERE agent=? ORDER BY path", (agent,)
        )]


def main():
    parser = argparse.ArgumentParser(description="Reservas atomicas para agentes en un working tree compartido")
    sub = parser.add_subparsers(dest="command", required=True)
    claim = sub.add_parser("claim")
    claim.add_argument("paths", nargs="+")
    claim.add_argument("--agent", required=True)
    claim.add_argument("--objective", required=True)
    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("paths", nargs="*")
    heartbeat.add_argument("--agent", required=True)
    release = sub.add_parser("release")
    release.add_argument("paths", nargs="*")
    release.add_argument("--agent", required=True)
    release.add_argument("--result", default="terminado")
    sub.add_parser("status")
    args = parser.parse_args()
    try:
        with Coordination() as coordination:
            if args.command == "claim":
                output = coordination.claim(args.agent, args.paths, args.objective)
            elif args.command == "heartbeat":
                output = coordination.heartbeat(args.agent, args.paths or None)
            elif args.command == "release":
                output = coordination.release(args.agent, args.paths or None, args.result)
            else:
                output = coordination.active()
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (ClaimConflict, ValueError) as error:
        print(json.dumps({"error": str(error)}, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
