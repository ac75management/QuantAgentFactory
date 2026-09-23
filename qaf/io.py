import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def canonical(value):
    return json.dumps(clean(value), sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(clean(value), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    os.replace(temp, path)


def write_json_exclusive(path, value):
    """Create a JSON artifact exactly once; never replace an existing path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(clean(value), stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def code_hash():
    paths = sorted((ROOT / "qaf").glob("*.py"))
    return digest({p.name: file_hash(p) for p in paths})


def load_hypotheses(root):
    structured = Path(root) / "config/hypotheses.json"
    if structured.exists():
        payload = read_json(structured)
        rows = payload.get("hypotheses") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("config/hypotheses.json requiere una lista hypotheses")
        ids = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
                raise ValueError("Cada hipotesis requiere id string no vacio")
            ids.append(row["id"].strip())
        if len(ids) != len(set(ids)):
            raise ValueError("IDs duplicados en config/hypotheses.json")
        return {row["id"].strip(): row for row in rows}
    return None


def load_registered_hypothesis_ids(root):
    hypotheses = load_hypotheses(root)
    if hypotheses is not None:
        return set(hypotheses)
    path = Path(root) / "docs/hypotheses/_registry.md"
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        if not cell or cell == "#" or set(cell) <= {"-"}:
            continue
        ids.add(cell)
    return ids
