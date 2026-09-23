import json
import sqlite3
import threading
from datetime import datetime, timezone

import pytest

import qaf.io as io_module
import qaf.source_sync as source_sync_module
from qaf.catalog import acknowledge_refresh
from qaf.coordination import ClaimConflict
from qaf.io import read_json, write_json_exclusive
from qaf.registry import Registry
from qaf.source_sync import sync_sources, validate_provider_config


class FakeTransport:
    def __init__(self, payloads):
        self.payloads = payloads
        self.urls = []
        self.pauses = []

    def get_json(self, url, headers):
        self.urls.append(url)
        for marker, value in self.payloads.items():
            if marker in url:
                return value() if callable(value) else value
        raise AssertionError(f"URL inesperada: {url}")

    def get_text(self, url, headers):
        self.urls.append(url)
        for marker, value in self.payloads.items():
            if marker in url:
                return value() if callable(value) else value
        raise AssertionError(f"URL inesperada: {url}")

    def pause(self, seconds):
        self.pauses.append(seconds)


def _root(tmp_path, providers):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/source_providers.json").write_text(
        json.dumps({"version": 2, "mode": "manual_batch", "providers": providers}), encoding="utf-8"
    )
    (tmp_path / "config/instruments.json").write_text("{}", encoding="utf-8")


def _crossref_provider():
    return {
        "id": "crossref_test",
        "name": "Crossref Test",
        "type": "crossref_rest",
        "endpoint": "https://api.crossref.org/works",
        "query": "systematic trading",
        "automation_status": "metadata_only",
        "initial_created_from": "2023-01-01",
        "created_overlap_days": 7,
        "minimum_score": 1.0,
        "refresh_known_dois": False,
        "sort": "relevance",
        "max_results": 10,
        "enabled": True,
    }


def _crossref_payload(title="A documented trading rule"):
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/example",
                    "title": [title],
                    "author": [{"given": "Ada", "family": "Researcher"}],
                    "published": {"date-parts": [[2024, 5, 2]]},
                    "URL": "https://doi.org/10.1234/example",
                    "type": "journal-article",
                    "score": 10.0,
                }
            ]
        }
    }


def test_periodic_sync_is_idempotent_and_queues_only_new_candidates(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    transport = FakeTransport({"api.crossref.org": _crossref_payload()})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)

    first = sync_sources(tmp_path, limit=5, transport=transport, now=now)
    second = sync_sources(tmp_path, limit=5, transport=transport, now=now)

    candidates = list((tmp_path / "catalog/candidates").glob("*.json"))
    snapshots = list((tmp_path / "catalog/discoveries/crossref_test").glob("*.json"))
    registry = Registry(tmp_path / "state/research.sqlite3")
    try:
        tasks = registry.tasks()
    finally:
        registry.close()
    assert first["created"] == 1 and second["unchanged"] == 1
    assert len(candidates) == 1 and len(snapshots) == 1
    assert len([task for task in tasks if task["stage"] == "evidence_review"]) == 1
    candidate = read_json(candidates[0])
    assert candidate["status"] == "captured"
    assert candidate["provenance"]["evidence_status"] == "unverified_discovery"
    assert "sin reglas verificadas" in candidate["rules_summary"]
    assert not (tmp_path / "config/hypotheses.json").exists()
    assert not (tmp_path / "config/strategies").exists()
    assert not (tmp_path / "reports").exists()


def test_source_change_creates_snapshot_and_refresh_task_without_overwrite(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    current = {"title": "Original title"}
    transport = FakeTransport({"api.crossref.org": lambda: _crossref_payload(current["title"])})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    sync_sources(tmp_path, transport=transport, now=now)
    candidate_file = next((tmp_path / "catalog/candidates").glob("*.json"))
    before = read_json(candidate_file)

    current["title"] = "Revised upstream title"
    result = sync_sources(tmp_path, transport=transport, now=now)
    after = read_json(candidate_file)
    registry = Registry(tmp_path / "state/research.sqlite3")
    try:
        refresh = [task for task in registry.tasks() if task["stage"] == "evidence_refresh"]
    finally:
        registry.close()

    assert result["updates_queued"] == 1
    assert len(list((tmp_path / "catalog/discoveries/crossref_test").glob("*.json"))) == 2
    assert after == before
    assert len(refresh) == 1 and refresh[0]["owner"] == "investigator"


def test_github_discovery_pins_exact_commit_without_copying_code(tmp_path):
    provider = {
        "id": "lean_test",
        "name": "LEAN Test",
        "type": "github_tree",
        "repository": "QuantConnect/Lean",
        "branch": "master",
        "path_prefix": "Algorithm.Python/",
        "include_regex": "MomentumAlgorithm\\.py$",
        "automation_status": "permissive_code_metadata",
        "license": "Apache-2.0",
        "enabled": True,
    }
    _root(tmp_path, [provider])
    commit = "a" * 40
    transport = FakeTransport({
        "/commits/master": {"sha": commit},
        "/git/trees/": {"tree": [
            {"path": "Algorithm.Python/FuturesMomentumAlgorithm.py", "type": "blob", "sha": "b" * 40},
            {"path": "Algorithm.Python/Readme.md", "type": "blob", "sha": "c" * 40},
        ]},
    })

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))
    candidate = read_json(next((tmp_path / "catalog/candidates").glob("*.json")))

    assert result["created"] == 1
    assert candidate["code_available"] is True
    assert candidate["provenance"]["source_revision"] == commit
    assert f"/blob/{commit}/" in candidate["source_url"]
    assert not list(tmp_path.rglob("FuturesMomentumAlgorithm.py"))


def test_cross_provider_doi_is_deduplicated(tmp_path):
    first = _crossref_provider()
    second = {**_crossref_provider(), "id": "crossref_second", "name": "Crossref Second"}
    _root(tmp_path, [first, second])
    transport = FakeTransport({"api.crossref.org": _crossref_payload()})

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    assert result["created"] == 1 and result["duplicates"] == 1
    assert len(list((tmp_path / "catalog/candidates").glob("*.json"))) == 1
    assert len(list((tmp_path / "catalog/discoveries").rglob("*.json"))) == 1


def test_manual_provider_cannot_be_enabled_as_automatic():
    with pytest.raises(ValueError, match="solo conectores implementados"):
        validate_provider_config({
            "version": 2,
            "providers": [{
                "id": "ssrn_manual", "name": "SSRN", "type": "manual_source",
                "automation_status": "manual_only", "enabled": True,
            }],
        })


def test_malformed_external_response_fails_without_candidate(tmp_path):
    provider = {
        "id": "lean_bad",
        "name": "LEAN Bad",
        "type": "github_tree",
        "repository": "QuantConnect/Lean",
        "branch": "master",
        "path_prefix": "Algorithm.Python/",
        "automation_status": "permissive_code_metadata",
        "enabled": True,
    }
    _root(tmp_path, [provider])
    transport = FakeTransport({"/commits/master": {"sha": "not-a-commit"}})

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    assert result["failed"] == 1
    assert "commit SHA" in result["providers"][0]["reason"]
    assert not list((tmp_path / "catalog/candidates").glob("*.json"))
    assert not (tmp_path / "state/research.sqlite3").exists()


def _arxiv_provider():
    return {
        "id": "arxiv_test",
        "name": "arXiv Test",
        "type": "arxiv_atom",
        "endpoint": "https://export.arxiv.org/api/query",
        "query": "cat:q-fin.TR",
        "automation_status": "metadata_only",
        "max_results": 2000,
        "enabled": True,
    }


def _atom(version, updated):
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
        '<opensearch:totalResults>1</opensearch:totalResults><entry>'
        f'<id>http://arxiv.org/abs/2401.12345{version}</id><updated>{updated}</updated>'
        '<published>2024-01-01T00:00:00Z</published><title>Momentum in gold</title>'
        f'<author><name>A B</name></author><link href="http://arxiv.org/abs/2401.12345{version}" rel="alternate"/>'
        '</entry></feed>'
    )


def _atom_many(count, declared_total=None):
    entries = []
    for number in range(count):
        entries.append(
            f'<entry><id>http://arxiv.org/abs/2401.{number:05d}v1</id>'
            f'<updated>2024-01-{number + 1:02d}T00:00:00Z</updated>'
            f'<published>2024-01-{number + 1:02d}T00:00:00Z</published>'
            f'<title>Documented strategy number {number}</title><author><name>A Researcher</name></author></entry>'
        )
    total = count if declared_total is None else declared_total
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
        f'<opensearch:totalResults>{total}</opensearch:totalResults>' + "".join(entries) + "</feed>"
    )


def _refresh_tasks(root):
    registry = Registry(root / "state/research.sqlite3")
    try:
        return [task for task in registry.tasks() if task["stage"] == "evidence_refresh"]
    finally:
        registry.close()


def test_arxiv_new_version_is_a_refresh_not_a_second_candidate(tmp_path):
    _root(tmp_path, [_arxiv_provider()])
    current = {"atom": _atom("v1", "2024-01-01T00:00:00Z")}
    transport = FakeTransport({"arxiv.org": lambda: current["atom"]})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)

    first = sync_sources(tmp_path, transport=transport, now=now)
    rerun = sync_sources(tmp_path, transport=transport, now=now)
    current["atom"] = _atom("v2", "2024-03-01T00:00:00Z")
    upgraded = sync_sources(tmp_path, transport=transport, now=now)

    candidates = list((tmp_path / "catalog/candidates").glob("*.json"))
    assert first["created"] == 1 and rerun["unchanged"] == 1
    assert upgraded["created"] == 0 and upgraded["duplicates"] == 0 and upgraded["updates_queued"] == 1
    assert len(candidates) == 1
    candidate = read_json(candidates[0])
    assert candidate["source_url"] == "https://arxiv.org/abs/2401.12345"
    assert "arxiv:2401.12345" in candidate["provenance"]["identity_keys"]
    assert len(_refresh_tasks(tmp_path)) == 1


def _lean_provider(**extra):
    return {
        "id": "lean_test",
        "name": "LEAN Test",
        "type": "github_tree",
        "repository": "QuantConnect/Lean",
        "branch": "master",
        "path_prefix": "Algorithm.Python/",
        "include_regex": r"Momentum[^/]*\.py$",
        "automation_status": "permissive_code_metadata",
        "license": "Apache-2.0",
        "enabled": True,
        **extra,
    }


def test_github_new_commit_same_file_is_unchanged_but_content_change_is_refreshed(tmp_path):
    _root(tmp_path, [_lean_provider()])
    state = {"commit": "a" * 40, "blob": "b" * 40}
    transport = FakeTransport({
        "/commits/master": lambda: {"sha": state["commit"]},
        "/git/trees/": lambda: {"tree": [{"path": "Algorithm.Python/FuturesMomentumAlgorithm.py", "type": "blob", "sha": state["blob"]}]},
    })
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)

    sync_sources(tmp_path, transport=transport, now=now)
    candidate_file = next((tmp_path / "catalog/candidates").glob("*.json"))
    before = read_json(candidate_file)
    state["commit"] = "c" * 40
    same_content = sync_sources(tmp_path, transport=transport, now=now)
    state["commit"], state["blob"] = "d" * 40, "e" * 40
    changed = sync_sources(tmp_path, transport=transport, now=now)

    assert same_content["unchanged"] == 1 and same_content["updates_queued"] == 0 and same_content["duplicates"] == 0
    assert changed["updates_queued"] == 1 and changed["created"] == 0 and changed["duplicates"] == 0
    assert read_json(candidate_file) == before
    assert before["provenance"]["source_revision"] == "a" * 40
    assert len(list((tmp_path / "catalog/candidates").glob("*.json"))) == 1
    assert len(_refresh_tasks(tmp_path)) == 1


def test_github_exclude_regex_drops_regression_suites(tmp_path):
    _root(tmp_path, [_lean_provider(exclude_regex="Regression|Test")])
    transport = FakeTransport({
        "/commits/master": {"sha": "a" * 40},
        "/git/trees/": {"tree": [
            {"path": "Algorithm.Python/FuturesMomentumAlgorithm.py", "type": "blob", "sha": "b" * 40},
            {"path": "Algorithm.Python/MomentumRegressionAlgorithm.py", "type": "blob", "sha": "c" * 40},
        ]},
    })
    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))
    assert result["created"] == 1
    assert "Regression" not in read_json(next((tmp_path / "catalog/candidates").glob("*.json")))["name"]


def test_crossref_uses_relevance_created_window_and_unknown_access(tmp_path):
    _root(tmp_path, [{**_crossref_provider(), "type_filter": "journal-article"}])
    payload = _crossref_payload()
    payload["message"]["items"].append({
        "DOI": "10.9999/future", "title": ["Title Pending 5823"],
        "published": {"date-parts": [[2115, 7, 1]]}, "type": "journal-article", "score": 10.0,
    })
    transport = FakeTransport({"api.crossref.org": payload})

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    url = transport.urls[0]
    assert "sort=" not in url
    assert "from-created-date%3A2023-01-01" in url
    assert "until-created-date%3A2026-09-22" in url and "type%3Ajournal-article" in url
    assert result["created"] == 1
    candidate = read_json(next((tmp_path / "catalog/candidates").glob("*.json")))
    assert candidate["access_level"] == "unknown"
    assert candidate["publication_date"] == "2024-05-02"


def test_same_work_under_two_dois_is_flagged_not_dropped(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    item = _crossref_payload()["message"]["items"][0]
    journal = {**item, "DOI": "10.1111/journal.1", "title": ["Time-Series Momentum in Futures Markets"]}
    proceedings = {**item, "DOI": "10.2222/proc.2", "title": ["Time series momentum in futures markets."]}
    other_author = {**item, "DOI": "10.3333/other.3", "title": ["Time series momentum in futures markets"],
                    "author": [{"given": "Otro", "family": "Autor"}]}
    transport = FakeTransport({"api.crossref.org": {"message": {"items": [journal, proceedings, other_author]}}})

    summary = sync_sources(tmp_path, limit=5, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    candidates = {c["provenance"]["upstream_id"]: c for c in map(read_json, (tmp_path / "catalog/candidates").glob("*.json"))}
    assert summary["created"] == 3 and summary["duplicates"] == 0 and summary["possible_duplicates"] == 1
    first = candidates["10.1111/journal.1"]
    assert "possible_duplicate_of" not in first["provenance"]
    assert candidates["10.2222/proc.2"]["provenance"]["possible_duplicate_of"] == first["candidate_id"]
    assert "possible_duplicate_of" not in candidates["10.3333/other.3"]["provenance"]


def test_catalog_fails_loudly_on_unreadable_candidate_and_ignores_legacy_folder(tmp_path):
    from qaf.catalog import list_candidates
    (tmp_path / "state/catalog").mkdir(parents=True)
    (tmp_path / "state/catalog/IDEA-OLD1.json").write_text('{"candidate_id": "IDEA-OLD1"}', encoding="utf-8")
    (tmp_path / "catalog/candidates").mkdir(parents=True)
    (tmp_path / "catalog/candidates/IDEA-GOOD.json").write_text('{"candidate_id": "IDEA-GOOD"}', encoding="utf-8")
    assert [row["candidate_id"] for row in list_candidates(tmp_path)] == ["IDEA-GOOD"]

    (tmp_path / "catalog/candidates/IDEA-BROKEN.json").write_text("{no es json", encoding="utf-8")
    with pytest.raises(ValueError, match="IDEA-BROKEN"):
        list_candidates(tmp_path)


def test_arxiv_complete_scan_drains_more_actions_than_limit_without_cursor(tmp_path):
    _root(tmp_path, [_arxiv_provider()])
    transport = FakeTransport({"arxiv.org": _atom_many(5)})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)

    first = sync_sources(tmp_path, limit=2, transport=transport, now=now)
    second = sync_sources(tmp_path, limit=2, transport=transport, now=now)
    third = sync_sources(tmp_path, limit=2, transport=transport, now=now)

    assert [first["created"], second["created"], third["created"]] == [2, 2, 1]
    assert len(list((tmp_path / "catalog/candidates").glob("*.json"))) == 5
    registry = Registry(tmp_path / "state/research.sqlite3")
    try:
        assert len([task for task in registry.tasks() if task["stage"] == "evidence_review"]) == 5
    finally:
        registry.close()


def test_arxiv_incomplete_total_fails_closed(tmp_path):
    _root(tmp_path, [_arxiv_provider()])
    transport = FakeTransport({"arxiv.org": _atom_many(1, declared_total=2)})

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    assert result["failed"] == 1
    assert "respuesta incompleta" in result["providers"][0]["reason"]
    assert not list((tmp_path / "catalog/candidates").glob("*.json"))


def test_github_truncated_tree_fails_closed(tmp_path):
    _root(tmp_path, [_lean_provider()])
    transport = FakeTransport({
        "/commits/master": {"sha": "a" * 40},
        "/git/trees/": {"truncated": True, "tree": []},
    })

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    assert result["failed"] == 1
    assert "árbol truncado" in result["providers"][0]["reason"]


def test_github_full_tree_applies_limit_after_processed_paths(tmp_path):
    _root(tmp_path, [_lean_provider()])
    tree = {
        "truncated": False,
        "tree": [
            {"path": f"Algorithm.Python/Momentum{number}Algorithm.py", "type": "blob", "sha": str(number) * 40}
            for number in range(1, 4)
        ],
    }
    transport = FakeTransport({"/commits/master": {"sha": "a" * 40}, "/git/trees/": tree})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)

    results = [sync_sources(tmp_path, limit=1, transport=transport, now=now) for _ in range(3)]

    assert [item["created"] for item in results] == [1, 1, 1]
    assert len(list((tmp_path / "catalog/candidates").glob("*.json"))) == 3


def test_existing_refresh_task_does_not_consume_limit_again(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    current = {"title": "Original documented strategy"}
    transport = FakeTransport({"api.crossref.org": lambda: _crossref_payload(current["title"])})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    sync_sources(tmp_path, limit=1, transport=transport, now=now)
    current["title"] = "Revised documented strategy"

    first_refresh = sync_sources(tmp_path, limit=1, transport=transport, now=now)
    repeated = sync_sources(tmp_path, limit=1, transport=transport, now=now)

    assert first_refresh["updates_queued"] == 1
    assert repeated["updates_queued"] == 0 and repeated["unchanged"] == 1


def test_acknowledged_refresh_survives_lost_sqlite_without_reopening_refresh(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    current = {"title": "Original documented strategy"}
    transport = FakeTransport({"api.crossref.org": lambda: _crossref_payload(current["title"])})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    sync_sources(tmp_path, transport=transport, now=now)
    current["title"] = "Revised documented strategy"
    sync_sources(tmp_path, transport=transport, now=now)
    candidate_file = next((tmp_path / "catalog/candidates").glob("*.json"))
    candidate = read_json(candidate_file)
    original = candidate["provenance"]["metadata_sha256"]
    refresh = next(path.stem for path in (tmp_path / "catalog/discoveries/crossref_test").glob("*.json") if path.stem != original)
    acknowledge_refresh(candidate["candidate_id"], refresh, tmp_path)
    (tmp_path / "state/research.sqlite3").unlink()

    result = sync_sources(tmp_path, transport=transport, now=now)
    registry = Registry(tmp_path / "state/research.sqlite3")
    try:
        tasks = registry.tasks()
    finally:
        registry.close()

    assert result["updates_queued"] == 0
    assert result["tasks_recovered"] == 1
    assert [task["stage"] for task in tasks] == ["evidence_review"]


def test_corrupt_snapshot_fails_closed(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    transport = FakeTransport({"api.crossref.org": _crossref_payload()})
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    sync_sources(tmp_path, transport=transport, now=now)
    snapshot = next((tmp_path / "catalog/discoveries/crossref_test").glob("*.json"))
    snapshot.write_text('{"metadata_sha256":"false"}', encoding="utf-8")

    result = sync_sources(tmp_path, transport=transport, now=now)

    assert result["failed"] == 1
    assert "Snapshot corrupto" in result["providers"][0]["reason"]


def test_dry_run_without_databases_creates_no_state(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    transport = FakeTransport({"api.crossref.org": _crossref_payload()})

    result = sync_sources(
        tmp_path,
        limit=1,
        dry_run=True,
        transport=transport,
        now=datetime(2026, 9, 22, tzinfo=timezone.utc),
    )

    assert result["created"] == 1
    assert not (tmp_path / "state/research.sqlite3").exists()
    assert not (tmp_path / "state/coordination.sqlite3").exists()
    assert not (tmp_path / "catalog").exists()


def test_corrupt_crossref_cursor_fails_closed(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    state = tmp_path / "state/research.sqlite3"
    state.parent.mkdir()
    connection = sqlite3.connect(state)
    connection.execute(
        "CREATE TABLE source_sync_state(provider_id TEXT PRIMARY KEY,schema_version INTEGER,cursor_json TEXT,updated_at TEXT)"
    )
    connection.execute(
        "INSERT INTO source_sync_state VALUES(?,?,?,?)",
        ("crossref_test", 999, "{}", "2026-09-22T00:00:00+00:00"),
    )
    connection.commit()
    connection.close()

    result = sync_sources(
        tmp_path,
        dry_run=True,
        transport=FakeTransport({"api.crossref.org": _crossref_payload()}),
        now=datetime(2026, 9, 22, tzinfo=timezone.utc),
    )

    assert result["failed"] == 1
    assert "versión de cursor desconocida" in result["providers"][0]["reason"]


def test_lost_global_lease_stops_before_next_write(tmp_path):
    _root(tmp_path, [_crossref_provider()])

    class LostLeaseCoordination:
        def __init__(self, root):
            self.heartbeats = 0

        def claim(self, *args, **kwargs):
            return []

        def heartbeat(self, agent, paths):
            self.heartbeats += 1
            if self.heartbeats >= 3:
                raise ClaimConflict("reserva recuperada")
            return list(paths)

        def release(self, *args, **kwargs):
            return []

        def close(self):
            return None

    with pytest.raises(ClaimConflict, match="recuperada"):
        sync_sources(
            tmp_path,
            transport=FakeTransport({"api.crossref.org": _crossref_payload()}),
            now=datetime(2026, 9, 22, tzinfo=timezone.utc),
            coordination_factory=LostLeaseCoordination,
        )

    assert len(list((tmp_path / "catalog/discoveries").rglob("*.json"))) == 1
    assert not list((tmp_path / "catalog/candidates").glob("*.json"))
    assert not (tmp_path / "state/research.sqlite3").exists()


def test_global_lease_serializes_parallel_providers_with_same_doi(tmp_path):
    first = _crossref_provider()
    second = {**first, "id": "crossref_second", "name": "Crossref Second"}
    _root(tmp_path, [first, second])
    entered = threading.Event()
    finish = threading.Event()

    class BlockingTransport(FakeTransport):
        def get_json(self, url, headers):
            entered.set()
            assert finish.wait(timeout=5)
            return _crossref_payload()

    errors = []

    def run_first():
        try:
            sync_sources(
                tmp_path,
                provider_ids=["crossref_test"],
                transport=BlockingTransport({}),
                now=datetime(2026, 9, 22, tzinfo=timezone.utc),
            )
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=run_first)
    thread.start()
    assert entered.wait(timeout=5)
    with pytest.raises(ClaimConflict):
        sync_sources(
            tmp_path,
            provider_ids=["crossref_second"],
            transport=FakeTransport({"api.crossref.org": _crossref_payload()}),
            now=datetime(2026, 9, 22, tzinfo=timezone.utc),
        )
    finish.set()
    thread.join(timeout=5)

    assert not errors
    assert len(list((tmp_path / "catalog/candidates").glob("*.json"))) == 1


def test_reconciles_missing_candidate_task_without_refetching_record(tmp_path):
    _root(tmp_path, [_crossref_provider()])
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    sync_sources(tmp_path, transport=FakeTransport({"api.crossref.org": _crossref_payload()}), now=now)
    (tmp_path / "state/research.sqlite3").unlink()

    result = sync_sources(
        tmp_path,
        limit=1,
        transport=FakeTransport({"api.crossref.org": {"message": {"items": []}}}),
        now=now,
    )

    assert result["tasks_recovered"] == 1
    assert result["providers"][0]["fetched"] == 0
    registry = Registry(tmp_path / "state/research.sqlite3")
    try:
        assert [task["task_id"] for task in registry.tasks()] == [
            "catalog:" + next((tmp_path / "catalog/candidates").glob("*.json")).stem
        ]
    finally:
        registry.close()


def test_exclusive_json_is_linked_only_after_complete_fsync(tmp_path, monkeypatch):
    target = tmp_path / "artifact.json"
    original_link = io_module.os.link
    observed = {}

    def checked_link(temporary, final):
        observed["payload"] = read_json(temporary)
        observed["final_absent"] = not target.exists()
        original_link(temporary, final)

    monkeypatch.setattr(io_module.os, "link", checked_link)
    write_json_exclusive(target, {"complete": True})

    assert observed == {"payload": {"complete": True}, "final_absent": True}
    assert read_json(target) == {"complete": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_arxiv_prioritizes_last_updated_descending(tmp_path):
    _root(tmp_path, [_arxiv_provider()])
    transport = FakeTransport({"arxiv.org": _atom_many(0)})

    sync_sources(tmp_path, dry_run=True, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    assert "sortBy=lastUpdatedDate" in transport.urls[0]
    assert "sortOrder=descending" in transport.urls[0]


def test_provider_failure_does_not_block_later_provider(tmp_path):
    _root(tmp_path, [_arxiv_provider(), _lean_provider()])
    tree = {
        "truncated": False,
        "tree": [{"path": "Algorithm.Python/MomentumAlgorithm.py", "type": "blob", "sha": "b" * 40}],
    }
    transport = FakeTransport({
        "arxiv.org": _atom_many(1, declared_total=2),
        "/commits/master": {"sha": "a" * 40},
        "/git/trees/": tree,
    })

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    assert result["failed"] == 1 and result["created"] == 1
    assert [row["status"] for row in result["providers"]] == ["failed", "ok"]


def test_failed_crossref_does_not_advance_cursor(tmp_path):
    _root(tmp_path, [_crossref_provider()])

    result = sync_sources(
        tmp_path,
        transport=FakeTransport({"api.crossref.org": {"unexpected": True}}),
        now=datetime(2026, 9, 22, tzinfo=timezone.utc),
    )

    assert result["failed"] == 1
    assert not (tmp_path / "state/research.sqlite3").exists()


def test_main_returns_nonzero_when_any_provider_failed(monkeypatch, capsys):
    monkeypatch.setattr(source_sync_module, "sync_sources", lambda **kwargs: {"failed": 1})
    monkeypatch.setattr("sys.argv", ["source-sync"])

    assert source_sync_module.main() == 1
    assert '"failed": 1' in capsys.readouterr().out


def test_http_transport_retries_timeouts_then_gives_up(monkeypatch):
    import qaf.source_sync as source_sync
    calls = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self):
            return b'{"ok": true}'

    def flaky(request, timeout):
        calls.append(timeout)
        if len(calls) < 3:
            raise TimeoutError("The read operation timed out")
        return Response()

    monkeypatch.setattr(source_sync, "urlopen", flaky)
    monkeypatch.setattr(source_sync.time, "sleep", lambda seconds: None)
    assert source_sync.HttpTransport(attempts=3).get_json("https://example.org", {}) == {"ok": True}
    assert len(calls) == 3

    calls.clear()
    monkeypatch.setattr(source_sync, "urlopen", lambda request, timeout: (_ for _ in ()).throw(TimeoutError("siempre")))
    with pytest.raises(TimeoutError):
        source_sync.HttpTransport(attempts=2).get_json("https://example.org", {})
