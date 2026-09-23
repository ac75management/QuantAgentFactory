import json
from datetime import datetime, timezone

import pytest

from qaf.io import read_json
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
    assert len(list((tmp_path / "catalog/discoveries").rglob("*.json"))) == 2


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

    with pytest.raises(ValueError, match="commit SHA"):
        sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

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
        "enabled": True,
    }


def _atom(version, updated):
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
        f'<id>http://arxiv.org/abs/2401.12345{version}</id><updated>{updated}</updated>'
        '<published>2024-01-01T00:00:00Z</published><title>Momentum in gold</title>'
        f'<author><name>A B</name></author><link href="http://arxiv.org/abs/2401.12345{version}" rel="alternate"/>'
        '</entry></feed>'
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


def test_crossref_uses_relevance_bounded_dates_and_unknown_access(tmp_path):
    _root(tmp_path, [{**_crossref_provider(), "type_filter": "journal-article", "lookback_days": 365}])
    payload = _crossref_payload()
    payload["message"]["items"].append({
        "DOI": "10.9999/future", "title": ["Title Pending 5823"],
        "published": {"date-parts": [[2115, 7, 1]]}, "type": "journal-article",
    })
    transport = FakeTransport({"api.crossref.org": payload})

    result = sync_sources(tmp_path, transport=transport, now=datetime(2026, 9, 22, tzinfo=timezone.utc))

    url = transport.urls[0]
    assert "sort=" not in url
    assert "until-pub-date%3A2026-09-22" in url and "type%3Ajournal-article" in url
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
