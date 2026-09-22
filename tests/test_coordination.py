from datetime import datetime, timedelta, timezone

import pytest

from qaf.coordination import ClaimConflict, Coordination


NOW = datetime(2026, 9, 22, 20, 0, tzinfo=timezone.utc)


def test_claim_is_atomic_and_blocks_another_agent(tmp_path):
    with Coordination(tmp_path) as coordination:
        coordination.claim("claude", ["qaf/a.py", "tests/test_a.py"], "cambio", now=NOW)
        with pytest.raises(ClaimConflict):
            coordination.claim("codex", ["docs/free.md", "qaf/a.py"], "otro", now=NOW)
        assert [row["path"] for row in coordination.active(now=NOW)] == ["qaf/a.py", "tests/test_a.py"]


def test_same_agent_can_refresh_without_changing_start(tmp_path):
    with Coordination(tmp_path) as coordination:
        first = coordination.claim("codex", ["qaf/a.py"], "inicio", now=NOW)[0]
        later = coordination.claim("codex", ["qaf/a.py"], "ajuste", now=NOW + timedelta(minutes=10))[0]
        assert later["started_at"] == first["started_at"]
        assert later["heartbeat_at"] != first["heartbeat_at"]
        assert later["objective"] == "ajuste"


def test_stale_claim_can_be_recovered_and_is_audited(tmp_path):
    with Coordination(tmp_path) as coordination:
        coordination.claim("claude", ["qaf/a.py"], "inicio", now=NOW)
        coordination.claim("codex", ["qaf/a.py"], "recuperar", now=NOW + timedelta(minutes=121))
        assert coordination.active(now=NOW + timedelta(minutes=121))[0]["agent"] == "codex"
        events = [row[0] for row in coordination.db.execute("SELECT event FROM claim_events ORDER BY id")]
        assert "STALE_TAKEOVER" in events


def test_heartbeat_and_release_require_ownership(tmp_path):
    with Coordination(tmp_path) as coordination:
        coordination.claim("codex", ["qaf/a.py"], "inicio", now=NOW)
        with pytest.raises(ClaimConflict):
            coordination.heartbeat("claude", ["qaf/a.py"], now=NOW)
        with pytest.raises(ClaimConflict):
            coordination.release("claude", ["qaf/a.py"])
        assert coordination.release("codex", ["qaf/a.py"], "121 tests") == ["qaf/a.py"]
        assert coordination.active(now=NOW) == []


def test_paths_outside_repo_and_duplicates_are_rejected(tmp_path):
    with Coordination(tmp_path) as coordination:
        with pytest.raises(ValueError):
            coordination.claim("codex", [tmp_path.parent / "outside.py"], "mal", now=NOW)
        with pytest.raises(ValueError):
            coordination.claim("codex", ["qaf/a.py", "QAF/A.py"], "duplicado", now=NOW)
