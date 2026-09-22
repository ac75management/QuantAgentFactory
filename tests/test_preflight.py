import json

from qaf.preflight import REQUIRED, audit


def _minimal_repo(root):
    for name in REQUIRED:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    (root / "config/hypotheses.json").write_text(json.dumps({"hypotheses": []}), encoding="utf-8")
    (root / "docs/hypotheses").mkdir(parents=True)
    (root / "docs/hypotheses/_registry.md").write_text("", encoding="utf-8")
    (root / "docs/specs").mkdir(parents=True)
    (root / "config/strategies").mkdir(parents=True)


def test_preflight_passes_minimal_coherent_repo(tmp_path):
    _minimal_repo(tmp_path)
    result = audit(tmp_path, include_git=False)
    assert result["status"] == "PASS"
    assert all(row["status"] == "PASS" for row in result["checks"])
    assert not (tmp_path / "state").exists()  # preflight es realmente de solo lectura


def test_preflight_fails_when_authoritative_file_is_missing(tmp_path):
    _minimal_repo(tmp_path)
    (tmp_path / "config/instruments.json").unlink()
    result = audit(tmp_path, include_git=False)
    required = next(row for row in result["checks"] if row["check"] == "required_files")
    assert result["status"] == "FAIL"
    assert required["status"] == "FAIL"
    assert "config/instruments.json" in required["evidence"]


def test_large_project_state_is_warning_not_false_failure(tmp_path):
    _minimal_repo(tmp_path)
    (tmp_path / "PROJECT_STATE.md").write_text("x\n" * 251, encoding="utf-8")
    result = audit(tmp_path, include_git=False)
    assert result["status"] == "WARN"
    assert next(row for row in result["checks"] if row["check"] == "state_log")["status"] == "WARN"
