import hashlib
import json
import math
import os
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


def code_hash():
    paths = sorted((ROOT / "qaf").glob("*.py"))
    return digest({p.name: file_hash(p) for p in paths})


def load_registered_hypothesis_ids(root):
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
