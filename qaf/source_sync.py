"""Safe, metadata-only discovery of strategy candidates.

The command stops before evidence review. It scans arXiv completely, samples
Crossref explicitly by relevance, scans a complete GitHub tree, writes
immutable snapshots only for real actions, and serializes every mutating run
with the repository coordination lease.
"""
import argparse
import json
import os
import re
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4
from xml.etree import ElementTree

from .catalog import add_candidate, candidate_path, list_candidates
from .coordination import ClaimConflict, Coordination
from .io import ROOT, digest, read_json, write_json_exclusive
from .registry import Registry


AUTOMATED_TYPES = {"arxiv_atom", "crossref_rest", "github_tree"}
SAFE_AUTOMATION = {"metadata_only", "permissive_code_metadata"}
VOLATILE_RECORD_FIELDS = ("source_url", "source_revision")
ARXIV_ID = re.compile(r"arxiv\.org/abs/(?P<base>.+?)(?P<version>v\d+)?$")
SHA256 = re.compile(r"[0-9a-f]{64}")
SOURCE_STATE_SCHEMA = 1
SOURCE_SYNC_CLAIMS = ("catalog/candidates", "catalog/discoveries")


def _fingerprint(record):
    return digest({key: value for key, value in record.items() if key not in VOLATILE_RECORD_FIELDS})


def _now(value=None):
    return value or datetime.now(timezone.utc)


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_segment(value):
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", str(value).casefold()).strip("-")
    if not cleaned:
        raise ValueError("Identificador de proveedor vacío")
    return cleaned[:80]


def _canonical_url(value):
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"URL externa inválida: {value!r}")
    path = parsed.path.rstrip("/") or "/"
    return parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower(), path=path, fragment="").geturl()


class HttpTransport:
    """Small HTTP client with bounded retry/backoff and no credential storage."""

    def __init__(self, timeout=30, attempts=3):
        self.timeout = timeout
        self.attempts = attempts

    def _get(self, url, headers):
        for attempt in range(self.attempts):
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except HTTPError as error:
                if error.code not in {429, 503} or attempt + 1 >= self.attempts:
                    raise
                retry_after = error.headers.get("Retry-After")
                delay = min(60, int(retry_after)) if retry_after and retry_after.isdigit() else 2 ** attempt
                time.sleep(delay)

    def get_json(self, url, headers):
        return json.loads(self._get(url, headers).decode("utf-8"))

    def get_text(self, url, headers):
        return self._get(url, headers).decode("utf-8")

    def pause(self, seconds):
        if seconds:
            time.sleep(seconds)


class _GlobalSyncLease:
    def __init__(self, root, coordination_factory=Coordination):
        self.root = Path(root)
        self.coordination = coordination_factory(self.root)
        self.agent = f"source-sync:{os.getpid()}:{uuid4().hex}"

    def __enter__(self):
        self.coordination.claim(
            self.agent,
            SOURCE_SYNC_CLAIMS,
            "Cosecha global y deduplicación del catálogo",
        )
        return self

    def checkpoint(self):
        owned = self.coordination.heartbeat(self.agent, SOURCE_SYNC_CLAIMS)
        if set(owned) != set(SOURCE_SYNC_CLAIMS):
            raise ClaimConflict("source-sync perdió su reserva global")

    def __exit__(self, exc_type, *_):
        try:
            self.coordination.release(self.agent, SOURCE_SYNC_CLAIMS, "source-sync finalizado")
        except ClaimConflict:
            if exc_type is None:
                raise
        finally:
            self.coordination.close()
        return False


class _DryRunLease:
    def __enter__(self):
        return self

    def checkpoint(self):
        return None

    def __exit__(self, *_):
        return False


def validate_provider_config(payload):
    if not isinstance(payload, dict) or payload.get("version") != 2:
        raise ValueError("config/source_providers.json requiere version 2")
    providers = payload.get("providers")
    if not isinstance(providers, list):
        raise ValueError("source_providers requiere una lista providers")
    ids = set()
    for provider in providers:
        if not isinstance(provider, dict):
            raise ValueError("Cada proveedor debe ser un objeto")
        provider_id = provider.get("id")
        if not isinstance(provider_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,60}", provider_id):
            raise ValueError("Proveedor con id inválido")
        if provider_id in ids:
            raise ValueError(f"Proveedor duplicado: {provider_id}")
        ids.add(provider_id)
        provider_type = provider.get("type")
        if provider_type in AUTOMATED_TYPES and provider.get("automation_status") not in SAFE_AUTOMATION:
            raise ValueError(f"{provider_id}: un conector automático requiere una política segura")
        if provider.get("enabled") and provider_type not in AUTOMATED_TYPES:
            raise ValueError(f"{provider_id}: solo conectores implementados pueden estar habilitados")
        if provider_type == "arxiv_atom" and provider.get("enabled"):
            maximum = int(provider.get("max_results", 0))
            if maximum < 1 or maximum > 2000:
                raise ValueError(f"{provider_id}: max_results de arXiv debe estar entre 1 y 2000")
        if provider_type == "crossref_rest" and provider.get("enabled"):
            try:
                date.fromisoformat(provider["initial_created_from"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{provider_id}: initial_created_from debe ser YYYY-MM-DD") from error
            overlap = int(provider.get("created_overlap_days", 0))
            if overlap < 0 or overlap > 30:
                raise ValueError(f"{provider_id}: created_overlap_days debe estar entre 0 y 30")
            if provider.get("refresh_known_dois") is not False:
                raise ValueError(f"{provider_id}: refresh_known_dois debe declarar false mientras no exista consulta DOI directa")
            if provider.get("sort") != "relevance":
                raise ValueError(f"{provider_id}: Crossref solo admite sort=relevance en este muestreo")
            maximum = int(provider.get("max_results", 0))
            if maximum < 1 or maximum > 200:
                raise ValueError(f"{provider_id}: max_results de Crossref debe estar entre 1 y 200")
            try:
                float(provider.get("minimum_score"))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{provider_id}: minimum_score debe ser numérico") from error
    return payload


def _headers(provider):
    agent = provider.get("user_agent", "QuantAgentFactory/1.0 (periodic metadata discovery)")
    headers = {"Accept": "application/json", "User-Agent": agent}
    token_env = provider.get("token_env")
    if token_env and os.environ.get(token_env):
        headers["Authorization"] = f"Bearer {os.environ[token_env]}"
    return headers


def _arxiv_records(provider, limit, transport, now, window=None):
    query = provider.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"{provider['id']}: falta query")
    maximum = int(provider["max_results"])
    params = urlencode({
        "search_query": query,
        "start": 0,
        "max_results": maximum,
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending",
    })
    text = transport.get_text(provider["endpoint"] + "?" + params, {**_headers(provider), "Accept": "application/atom+xml"})
    root = ElementTree.fromstring(text)
    atom = "{http://www.w3.org/2005/Atom}"
    arxiv = "{http://arxiv.org/schemas/atom}"
    opensearch = "{http://a9.com/-/spec/opensearch/1.1/}"
    total_text = root.findtext(opensearch + "totalResults")
    try:
        total = int(total_text)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{provider['id']}: arXiv no declaró totalResults válido") from error
    if total > maximum:
        raise ValueError(f"{provider['id']}: arXiv reportó {total} resultados; supera el límite completo {maximum}")
    records = []
    for entry in root.findall(atom + "entry"):
        entry_id = _clean_text(entry.findtext(atom + "id"))
        match = ARXIV_ID.search(entry_id)
        if not match:
            raise ValueError(f"{provider['id']}: id de arXiv no reconocido: {entry_id!r}")
        arxiv_id = match.group("base")
        doi = _clean_text(entry.findtext(arxiv + "doi")) or None
        records.append({
            "upstream_id": arxiv_id,
            "arxiv_id": arxiv_id,
            "version": match.group("version"),
            "title": _clean_text(entry.findtext(atom + "title")),
            "source_url": f"https://arxiv.org/abs/{quote(arxiv_id)}",
            "doi": doi,
            "authors": [_clean_text(author.findtext(atom + "name")) for author in entry.findall(atom + "author")],
            "publication_date": _clean_text(entry.findtext(atom + "published"))[:10] or None,
            "categories": [item.get("term") for item in entry.findall(atom + "category") if item.get("term")],
            "source_revision": _clean_text(entry.findtext(atom + "updated")) or None,
            "code_available": False,
            "access_level": "public",
            "license": "per_record_review_required",
        })
    unique = {record["upstream_id"] for record in records}
    if len(records) != total or len(unique) != total:
        raise ValueError(
            f"{provider['id']}: respuesta incompleta de arXiv; totalResults={total}, entradas={len(records)}, únicas={len(unique)}"
        )
    return records


def _crossref_date(item):
    parts = item.get("published", {}).get("date-parts", [[]])[0]
    if not parts:
        return None
    values = list(parts) + [1, 1]
    try:
        return date(values[0], values[1], values[2]).isoformat()
    except (TypeError, ValueError):
        return None


def _crossref_records(provider, limit, transport, now, window=None):
    query = provider.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"{provider['id']}: falta query")
    if not window:
        raise ValueError(f"{provider['id']}: falta ventana de creación")
    params = {
        "query.bibliographic": query,
        "rows": min(limit, int(provider.get("max_results", limit))),
        "select": "DOI,title,author,published,URL,type,license,link,container-title,score,created",
    }
    filters = [f"from-created-date:{window[0]}", f"until-created-date:{window[1]}"]
    if provider.get("type_filter"):
        filters.append("type:" + provider["type_filter"])
    params["filter"] = ",".join(filters)
    contact_env = provider.get("contact_email_env")
    if contact_env and os.environ.get(contact_env):
        params["mailto"] = os.environ[contact_env]
    payload = transport.get_json(provider["endpoint"] + "?" + urlencode(params), _headers(provider))
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise ValueError(f"{provider['id']}: respuesta Crossref sin message.items")
    minimum_score = float(provider.get("minimum_score", 0))
    records = []
    for item in message["items"]:
        try:
            score = float(item.get("score", 0))
        except (TypeError, ValueError):
            continue
        if score < minimum_score:
            continue
        doi = _clean_text(item.get("DOI")) or None
        titles = item.get("title") or []
        title = _clean_text(titles[0] if titles else "")
        if not doi or not title:
            continue
        published = _crossref_date(item)
        if published and published > now.date().isoformat():
            continue
        authors = []
        for author in item.get("author") or []:
            name = _clean_text(" ".join([author.get("given", ""), author.get("family", "")]))
            if name:
                authors.append(name)
        venues = item.get("container-title") or []
        records.append({
            "upstream_id": doi.lower(),
            "title": title,
            "source_url": f"https://doi.org/{doi}",
            "doi": doi.lower(),
            "authors": authors,
            "publication_date": published,
            "venue": _clean_text(venues[0]) if venues else None,
            "categories": [item.get("type")] if item.get("type") else [],
            "source_revision": None,
            "code_available": False,
            "access_level": "unknown",
            "license": "metadata_open_content_license_per_record",
        })
    return records


def _humanize_filename(path):
    stem = Path(path).stem
    return _clean_text(re.sub(r"(?<!^)(?=[A-Z])", " ", stem).replace("_", " ").replace("-", " "))


def _github_records(provider, limit, transport, now, window=None):
    repo = provider.get("repository")
    branch = provider.get("branch", "master")
    if not isinstance(repo, str) or not re.fullmatch(r"[^/\s]+/[^/\s]+", repo):
        raise ValueError(f"{provider['id']}: repository debe ser owner/repo")
    headers = _headers(provider)
    commit = transport.get_json(f"https://api.github.com/repos/{repo}/commits/{quote(branch)}", headers)
    commit_sha = commit.get("sha")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise ValueError(f"{provider['id']}: GitHub no devolvió un commit SHA")
    tree = transport.get_json(f"https://api.github.com/repos/{repo}/git/trees/{commit_sha}?recursive=1", headers)
    if tree.get("truncated") is True:
        raise ValueError(f"{provider['id']}: GitHub devolvió un árbol truncado; no se acepta una cosecha parcial")
    if not isinstance(tree.get("tree"), list):
        raise ValueError(f"{provider['id']}: GitHub no devolvió una lista tree")
    prefix = provider.get("path_prefix", "")
    pattern = re.compile(provider.get("include_regex", r"Algorithm\.py$"), re.IGNORECASE)
    exclude = re.compile(provider["exclude_regex"], re.IGNORECASE) if provider.get("exclude_regex") else None
    records = []
    for item in sorted(tree["tree"], key=lambda value: str(value.get("path", "")).casefold()):
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.startswith(prefix) or not pattern.search(path):
            continue
        if exclude and exclude.search(path):
            continue
        blob_sha = item.get("sha")
        if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", blob_sha):
            raise ValueError(f"{provider['id']}: blob SHA inválido para {path}")
        records.append({
            "upstream_id": f"{repo}:{path}",
            "title": _humanize_filename(path),
            "source_url": f"https://github.com/{repo}/blob/{commit_sha}/{path}",
            "doi": None,
            "authors": [],
            "publication_date": None,
            "categories": ["source_code"],
            "source_revision": commit_sha,
            "repository_url": f"https://github.com/{repo}",
            "source_path": path,
            "blob_sha": blob_sha,
            "code_available": True,
            "access_level": "public",
            "license": provider.get("license", "license_review_required"),
        })
    return records


def fetch_provider(provider, limit, transport, now, window=None):
    functions = {"arxiv_atom": _arxiv_records, "crossref_rest": _crossref_records, "github_tree": _github_records}
    provider_type = provider.get("type")
    if provider_type not in functions:
        raise ValueError(f"Conector no implementado: {provider_type}")
    return functions[provider_type](provider, limit, transport, now, window)


def _identity_keys(record):
    keys = []
    doi = _clean_text(record.get("doi")).casefold()
    if doi:
        keys.append("doi:" + doi)
    arxiv_id = _clean_text(record.get("arxiv_id")).casefold()
    if arxiv_id:
        keys.append("arxiv:" + arxiv_id)
    repository = _clean_text(record.get("repository_url")).rstrip("/").casefold()
    source_path = _clean_text(record.get("source_path")).casefold()
    if repository and source_path:
        keys.append(f"repo-path:{repository}:{source_path}")
    url = _canonical_url(record.get("source_url"))
    if url:
        keys.append("url:" + url.casefold())
    return sorted(set(keys))


def _work_key(record):
    authors = record.get("authors") or []
    words = re.findall(r"\w+", _clean_text(record.get("title")).casefold())
    surname = re.findall(r"\w+", _clean_text(authors[0]).casefold()) if authors else []
    if len(words) < 4 or not surname:
        return None
    return "work:" + " ".join(words) + "|" + surname[-1]


def _candidate_from_record(provider, record, fingerprint, snapshot_path, now):
    provider_id = provider["id"]
    candidate_id = "IDEA-SRC-" + digest({"provider": provider_id, "upstream_id": record["upstream_id"]})[:12].upper()
    source_url = _canonical_url(record["source_url"])
    return {
        "candidate_id": candidate_id, "name": record["title"], "source_name": provider["name"],
        "source_url": source_url, "primary_source_url": source_url,
        "publication_date": record.get("publication_date"), "access_level": record.get("access_level", "unknown"),
        "content_type": "strategy", "original_asset_classes": ["unknown"], "instruments": [],
        "original_timeframes": ["UNSPECIFIED"], "proposed_targets": [], "data_requirements": [],
        "rules_summary": "Descubrimiento automático sin reglas verificadas. Investigator debe revisar la fuente primaria, clasificar el contenido y extraer reglas sin inventar parámetros.",
        "code_available": bool(record.get("code_available")), "status": "captured",
        "provenance": {
            "provider_id": provider_id, "upstream_id": record["upstream_id"], "first_seen_at": now.isoformat(),
            "metadata_sha256": fingerprint, "snapshot_path": snapshot_path.as_posix(),
            "identity_keys": _identity_keys(record), "work_key": _work_key(record),
            "source_revision": record.get("source_revision"), "repository_url": record.get("repository_url"),
            "source_path": record.get("source_path"), "license": record.get("license"),
            "evidence_status": "unverified_discovery", "acknowledged_fingerprints": [],
        },
    }


def _candidate_identity_index(candidates):
    index = {}
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        keys = list(candidate.get("provenance", {}).get("identity_keys", []))
        for value in (candidate.get("primary_source_url"), candidate.get("source_url")):
            try:
                url = _canonical_url(value)
            except ValueError:
                url = None
            if url:
                keys.append("url:" + url.casefold())
        for key in keys:
            index.setdefault(key, candidate_id)
    return index


def _refresh_task_id(candidate_id, fingerprint):
    return f"catalog-refresh:{candidate_id}:{fingerprint}"


def _readonly_connection(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def _task_status(root, task_id):
    path = Path(root) / "state/research.sqlite3"
    if not path.exists():
        return None
    connection = _readonly_connection(path)
    connection.row_factory = sqlite3.Row
    try:
        try:
            row = connection.execute("SELECT status FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        except sqlite3.OperationalError as error:
            if "no such table" in str(error).lower():
                return None
            raise
        return row["status"] if row else None
    finally:
        connection.close()


def _queue_evidence(root, candidate_id, candidate_file, before_write):
    before_write()
    registry = Registry(Path(root) / "state/research.sqlite3")
    try:
        return registry.queue_task(
            "catalog:" + candidate_id, candidate_id, "evidence_review", "investigator",
            json.dumps([str(candidate_file.relative_to(root))], ensure_ascii=False),
            "Idea catalogada; revisar fuente primaria y reglas antes de crear una hipótesis.",
        )
    finally:
        registry.close()


def _queue_refresh(root, candidate_id, fingerprint, candidate_file, snapshot_file, before_write):
    before_write()
    registry = Registry(Path(root) / "state/research.sqlite3")
    try:
        return registry.queue_task(
            _refresh_task_id(candidate_id, fingerprint), candidate_id, "evidence_refresh", "investigator",
            json.dumps([str(candidate_file.relative_to(root)), str(snapshot_file.relative_to(root))], ensure_ascii=False),
            "La fuente publicó metadatos nuevos; revisar sin sobrescribir la evidencia existente.",
        )
    finally:
        registry.close()


def validate_snapshot_file(path, expected_fingerprint, provider_id=None):
    path = Path(path)
    if not isinstance(expected_fingerprint, str) or path.stem != expected_fingerprint or not SHA256.fullmatch(expected_fingerprint):
        raise ValueError(f"Snapshot inconsistente con su nombre: {path.name}")
    try:
        payload = read_json(path)
    except (OSError, ValueError) as error:
        raise ValueError(f"Snapshot ilegible: {path}") from error
    record = payload.get("record") if isinstance(payload, dict) else None
    if (
        payload.get("schema_version") != 1 or payload.get("metadata_sha256") != expected_fingerprint
        or not isinstance(record, dict) or _fingerprint(record) != expected_fingerprint
        or (provider_id is not None and payload.get("provider_id") != provider_id)
    ):
        raise ValueError(f"Snapshot corrupto o con huella falsa: {path}")
    return payload


def _ensure_snapshot(snapshot_file, snapshot, fingerprint, provider_id, before_write):
    if snapshot_file.exists():
        validate_snapshot_file(snapshot_file, fingerprint, provider_id)
        return False
    before_write()
    try:
        write_json_exclusive(snapshot_file, snapshot)
    except FileExistsError:
        validate_snapshot_file(snapshot_file, fingerprint, provider_id)
        return False
    return True


def _load_crossref_cursor(root, provider_id):
    path = Path(root) / "state/research.sqlite3"
    if not path.exists():
        return None
    connection = _readonly_connection(path)
    connection.row_factory = sqlite3.Row
    try:
        try:
            row = connection.execute("SELECT schema_version,cursor_json FROM source_sync_state WHERE provider_id=?", (provider_id,)).fetchone()
        except sqlite3.OperationalError as error:
            if "no such table" in str(error).lower():
                return None
            raise
    finally:
        connection.close()
    if not row:
        return None
    if row["schema_version"] != SOURCE_STATE_SCHEMA:
        raise ValueError(f"{provider_id}: versión de cursor desconocida {row['schema_version']}")
    try:
        payload = json.loads(row["cursor_json"])
        date.fromisoformat(payload["last_window_end"])
    except (TypeError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"{provider_id}: cursor corrupto") from error
    return payload


def _save_crossref_cursor(root, provider_id, window_end, before_write):
    before_write()
    path = Path(root) / "state/research.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS source_sync_state(provider_id TEXT PRIMARY KEY,schema_version INTEGER NOT NULL,cursor_json TEXT NOT NULL,updated_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO source_sync_state(provider_id,schema_version,cursor_json,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(provider_id) DO UPDATE SET schema_version=excluded.schema_version,cursor_json=excluded.cursor_json,updated_at=excluded.updated_at",
            (provider_id, SOURCE_STATE_SCHEMA, json.dumps({"last_window_end": window_end}, sort_keys=True), datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def _crossref_window(root, provider, now):
    cursor = _load_crossref_cursor(root, provider["id"])
    initial = date.fromisoformat(provider["initial_created_from"])
    if cursor:
        previous_end = date.fromisoformat(cursor["last_window_end"])
        if previous_end > now.date():
            raise ValueError(f"{provider['id']}: cursor está en el futuro")
        start = previous_end - timedelta(days=int(provider.get("created_overlap_days", 0)))
    else:
        start = initial
    end = now.date()
    if start > end:
        raise ValueError(f"{provider['id']}: initial_created_from está en el futuro")
    return start.isoformat(), end.isoformat()


def _reconcile_missing_tasks(root, candidates, provider_id, limit, lease):
    recovered = 0
    deferred = 0
    for candidate in candidates:
        provenance = candidate.get("provenance", {})
        if provenance.get("provider_id") != provider_id or candidate.get("status") != "captured":
            continue
        candidate_id = candidate.get("candidate_id")
        if _task_status(root, "catalog:" + candidate_id) is not None:
            continue
        if recovered >= limit:
            deferred += 1
            continue
        fingerprint = provenance.get("metadata_sha256")
        snapshot = root / provenance.get("snapshot_path", "")
        validate_snapshot_file(snapshot, fingerprint, provider_id)
        if _queue_evidence(root, candidate_id, candidate_path(root, candidate_id), lease.checkpoint):
            recovered += 1
    return recovered, deferred


def sync_sources(root=ROOT, provider_ids=None, limit=20, dry_run=False, transport=None, now=None, coordination_factory=Coordination):
    root = Path(root)
    now = _now(now)
    transport = transport or HttpTransport()
    config = validate_provider_config(read_json(root / "config/source_providers.json"))
    selected = set(provider_ids or [])
    known_ids = {item["id"] for item in config["providers"]}
    missing = selected - known_ids
    if missing:
        raise ValueError("Proveedores inexistentes: " + ", ".join(sorted(missing)))
    lease_context = _DryRunLease() if dry_run else _GlobalSyncLease(root, coordination_factory)
    with lease_context as lease:
        candidates = list_candidates(root)
        by_id = {item.get("candidate_id"): item for item in candidates}
        identity_index = _candidate_identity_index(candidates)
        work_index = {}
        for item in candidates:
            work_key = item.get("provenance", {}).get("work_key")
            if work_key:
                work_index.setdefault(work_key, item.get("candidate_id"))
        summary = {
            "started_at": now.isoformat(), "dry_run": dry_run, "providers": [], "created": 0,
            "unchanged": 0, "updates_queued": 0, "tasks_recovered": 0, "duplicates": 0,
            "possible_duplicates": 0, "deferred": 0, "failed": 0,
        }
        for provider in config["providers"]:
            if selected and provider["id"] not in selected:
                continue
            row = {
                "provider_id": provider["id"], "status": "skipped", "fetched": 0, "created": 0,
                "unchanged": 0, "updates_queued": 0, "tasks_recovered": 0, "duplicates": 0,
                "possible_duplicates": 0, "deferred": 0,
            }
            if not provider.get("enabled"):
                row["reason"] = provider.get("disabled_reason", "disabled")
                summary["providers"].append(row)
                continue
            if provider["type"] == "arxiv_atom":
                row["mode"] = "complete_scan"
            elif provider["type"] == "crossref_rest":
                row["mode"] = "relevance_sample"
            else:
                row["mode"] = "complete_tree"
            actions = 0
            try:
                lease.checkpoint()
                if not dry_run:
                    recovered, reconciliation_deferred = _reconcile_missing_tasks(
                        root, candidates, provider["id"], limit, lease
                    )
                    actions += recovered
                    row["tasks_recovered"] += recovered
                    summary["tasks_recovered"] += recovered
                    row["deferred"] += reconciliation_deferred
                    summary["deferred"] += reconciliation_deferred
                window = _crossref_window(root, provider, now) if provider["type"] == "crossref_rest" else None
                if window:
                    row["window"] = {"from_created": window[0], "until_created": window[1]}
                records = fetch_provider(provider, limit, transport, now, window)
                row["fetched"] = len(records)
                for record in records:
                    if not record.get("upstream_id") or not record.get("title") or not record.get("source_url"):
                        raise ValueError(f"{provider['id']}: registro incompleto")
                    fingerprint = _fingerprint(record)
                    provider_dir = Path("catalog/discoveries") / _safe_segment(provider["id"])
                    snapshot_rel = provider_dir / f"{fingerprint}.json"
                    snapshot_file = root / snapshot_rel
                    snapshot = {"schema_version": 1, "provider_id": provider["id"], "retrieved_at": now.isoformat(), "metadata_sha256": fingerprint, "record": record}
                    candidate = _candidate_from_record(provider, record, fingerprint, snapshot_rel, now)
                    candidate_id = candidate["candidate_id"]
                    existing = by_id.get(candidate_id)
                    duplicate_id = next((identity_index[key] for key in candidate["provenance"]["identity_keys"] if key in identity_index and identity_index[key] != candidate_id), None)
                    if duplicate_id and not existing:
                        row["duplicates"] += 1; summary["duplicates"] += 1
                        continue
                    if not existing:
                        if actions >= limit:
                            row["deferred"] += 1; summary["deferred"] += 1
                            continue
                        work_key = candidate["provenance"]["work_key"]
                        if work_key and work_index.get(work_key, candidate_id) != candidate_id:
                            candidate["provenance"]["possible_duplicate_of"] = work_index[work_key]
                            row["possible_duplicates"] += 1; summary["possible_duplicates"] += 1
                        if work_key:
                            work_index.setdefault(work_key, candidate_id)
                        if not dry_run:
                            _ensure_snapshot(snapshot_file, snapshot, fingerprint, provider["id"], lease.checkpoint)
                            stored, _ = add_candidate(candidate, root, before_write=lease.checkpoint)
                        else:
                            stored = candidate
                        by_id[candidate_id] = stored
                        for key in candidate["provenance"]["identity_keys"]:
                            identity_index[key] = candidate_id
                        actions += 1; row["created"] += 1; summary["created"] += 1
                        continue
                    initial_task_id = "catalog:" + candidate_id
                    missing_initial_task = existing.get("status") == "captured" and _task_status(root, initial_task_id) is None
                    if missing_initial_task:
                        if actions >= limit:
                            row["deferred"] += 1; summary["deferred"] += 1
                            continue
                        if not dry_run:
                            original_hash = existing.get("provenance", {}).get("metadata_sha256")
                            original_snapshot = root / existing.get("provenance", {}).get("snapshot_path", "")
                            validate_snapshot_file(original_snapshot, original_hash, existing.get("provenance", {}).get("provider_id"))
                            created = _queue_evidence(root, candidate_id, candidate_path(root, candidate_id), lease.checkpoint)
                        else:
                            created = True
                        if created:
                            actions += 1; row["tasks_recovered"] += 1; summary["tasks_recovered"] += 1
                            continue
                    previous_hash = existing.get("provenance", {}).get("metadata_sha256")
                    if previous_hash == fingerprint:
                        validate_snapshot_file(root / existing["provenance"]["snapshot_path"], fingerprint, provider["id"])
                        row["unchanged"] += 1; summary["unchanged"] += 1
                        continue
                    acknowledged = set(existing.get("provenance", {}).get("acknowledged_fingerprints", []))
                    if fingerprint in acknowledged:
                        validate_snapshot_file(snapshot_file, fingerprint, provider["id"])
                        row["unchanged"] += 1; summary["unchanged"] += 1
                        continue
                    task_id = _refresh_task_id(candidate_id, fingerprint)
                    if _task_status(root, task_id) is not None:
                        validate_snapshot_file(snapshot_file, fingerprint, provider["id"])
                        row["unchanged"] += 1; summary["unchanged"] += 1
                        continue
                    if actions >= limit:
                        row["deferred"] += 1; summary["deferred"] += 1
                        continue
                    if not dry_run:
                        _ensure_snapshot(snapshot_file, snapshot, fingerprint, provider["id"], lease.checkpoint)
                        created = _queue_refresh(root, candidate_id, fingerprint, candidate_path(root, candidate_id), snapshot_file, lease.checkpoint)
                    else:
                        created = True
                    if created:
                        actions += 1; row["updates_queued"] += 1; summary["updates_queued"] += 1
                    else:
                        row["unchanged"] += 1; summary["unchanged"] += 1
                if provider["type"] == "crossref_rest" and not dry_run:
                    _save_crossref_cursor(root, provider["id"], window[1], lease.checkpoint)
                row["status"] = "ok"
            except ClaimConflict:
                raise
            except Exception as error:
                row["status"] = "failed"
                row["reason"] = f"{type(error).__name__}: {error}"
                summary["failed"] += 1
            summary["providers"].append(row)
            transport.pause(float(provider.get("min_interval_seconds", 0)))
        return summary


def main():
    parser = argparse.ArgumentParser(description="Extracción periódica de metadatos para el catálogo")
    parser.add_argument("--provider", action="append", dest="providers", help="ID de proveedor; repetible")
    parser.add_argument("--limit", type=int, default=20, help="máximo de acciones nuevas por proveedor")
    parser.add_argument("--dry-run", action="store_true", help="consulta sin escribir candidatos, snapshots, tareas ni cursores")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 200:
        raise ValueError("--limit debe estar entre 1 y 200")
    result = sync_sources(provider_ids=args.providers, limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
