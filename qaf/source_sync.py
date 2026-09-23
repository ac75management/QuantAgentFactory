"""Periodic, metadata-only discovery of strategy candidates.

This module deliberately stops before evidence review.  It records immutable
metadata snapshots, creates a Git-tracked candidate once, and queues an
investigator.  Re-running it is idempotent and never overwrites a reviewed
candidate or promotes a hypothesis.
"""
import argparse
import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .catalog import add_candidate, candidate_path, list_candidates
from .io import ROOT, digest, read_json, write_json
from .registry import Registry


AUTOMATED_TYPES = {"arxiv_atom", "crossref_rest", "github_tree"}
SAFE_AUTOMATION = {"metadata_only", "permissive_code_metadata"}
# Change on every upstream commit or new arXiv upload even when the content is the
# same; excluded from the fingerprint so they do not trigger refresh tasks. Content
# changes are still caught through title/authors/version (arXiv) or blob_sha (GitHub).
VOLATILE_RECORD_FIELDS = ("source_url", "source_revision")
ARXIV_ID = re.compile(r"arxiv\.org/abs/(?P<base>.+?)(?P<version>v\d+)?$")


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
    return payload


def _headers(provider):
    agent = provider.get("user_agent", "QuantAgentFactory/1.0 (periodic metadata discovery)")
    headers = {"Accept": "application/json", "User-Agent": agent}
    token_env = provider.get("token_env")
    if token_env and os.environ.get(token_env):
        headers["Authorization"] = f"Bearer {os.environ[token_env]}"
    return headers


def _arxiv_records(provider, limit, transport, now):
    query = provider.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"{provider['id']}: falta query")
    params = urlencode({
        "search_query": query,
        "start": 0,
        "max_results": min(limit, int(provider.get("max_results", limit))),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = provider["endpoint"] + "?" + params
    text = transport.get_text(url, {**_headers(provider), "Accept": "application/atom+xml"})
    root = ElementTree.fromstring(text)
    atom = "{http://www.w3.org/2005/Atom}"
    arxiv = "{http://arxiv.org/schemas/atom}"
    records = []
    for entry in root.findall(atom + "entry"):
        entry_id = _clean_text(entry.findtext(atom + "id"))
        match = ARXIV_ID.search(entry_id)
        if not match:
            raise ValueError(f"{provider['id']}: id de arXiv no reconocido: {entry_id!r}")
        # One identity per paper: a new upload (v1 -> v2) is a refresh of the same
        # candidate, never a second candidate.
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


def _crossref_records(provider, limit, transport, now):
    query = provider.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"{provider['id']}: falta query")
    params = {
        "query.bibliographic": query,
        "rows": min(limit, int(provider.get("max_results", limit))),
        "select": "DOI,title,author,published,URL,type,license,link,container-title",
    }
    # Sorting by publication date discards relevance: on 2026-09-22 it returned
    # marketing, medicine and placeholder records dated 2036-2115.
    sort = provider.get("sort", "relevance")
    if sort not in {"relevance", "published"}:
        raise ValueError(f"{provider['id']}: sort debe ser relevance o published")
    if sort == "published":
        params.update(sort="published", order="desc")
    filters = ["until-pub-date:" + now.date().isoformat()]
    lookback_days = int(provider.get("lookback_days", 0))
    if lookback_days:
        filters.append("from-pub-date:" + (now.date() - timedelta(days=lookback_days)).isoformat())
    if provider.get("type_filter"):
        filters.append("type:" + provider["type_filter"])
    params["filter"] = ",".join(filters)
    contact_env = provider.get("contact_email_env")
    if contact_env and os.environ.get(contact_env):
        params["mailto"] = os.environ[contact_env]
    payload = transport.get_json(provider["endpoint"] + "?" + urlencode(params), _headers(provider))
    items = payload.get("message", {}).get("items", [])
    records = []
    for item in items:
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


def _github_records(provider, limit, transport, now):
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
    prefix = provider.get("path_prefix", "")
    pattern = re.compile(provider.get("include_regex", r"Algorithm\.py$"), re.IGNORECASE)
    exclude = re.compile(provider["exclude_regex"], re.IGNORECASE) if provider.get("exclude_regex") else None
    records = []
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.startswith(prefix) or not pattern.search(path):
            continue
        if exclude and exclude.search(path):
            continue
        # Identity is repository + path: a new upstream commit is the same file. The
        # commit stays pinned in source_url/source_revision of the first snapshot and
        # blob_sha (content hash) is what detects a real change.
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
            "blob_sha": item.get("sha"),
            "code_available": True,
            "access_level": "public",
            "license": provider.get("license", "license_review_required"),
        })
        if len(records) >= min(limit, int(provider.get("max_results", limit))):
            break
    return records


def fetch_provider(provider, limit, transport, now):
    functions = {
        "arxiv_atom": _arxiv_records,
        "crossref_rest": _crossref_records,
        "github_tree": _github_records,
    }
    provider_type = provider.get("type")
    if provider_type not in functions:
        raise ValueError(f"Conector no implementado: {provider_type}")
    return functions[provider_type](provider, limit, transport, now)


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
    """Same work under several DOIs (journal + proceedings, preprint + article).

    Title plus first-author surname can collide, so this key only flags a possible
    duplicate for investigator; it never skips a record the way identity keys do.
    """
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
        "candidate_id": candidate_id,
        "name": record["title"],
        "source_name": provider["name"],
        "source_url": source_url,
        "primary_source_url": source_url,
        "publication_date": record.get("publication_date"),
        "access_level": record.get("access_level", "unknown"),
        "content_type": "strategy",
        "original_asset_classes": ["unknown"],
        "instruments": [],
        "original_timeframes": ["UNSPECIFIED"],
        "proposed_targets": [],
        "data_requirements": [],
        "rules_summary": "Descubrimiento automático sin reglas verificadas. Investigator debe revisar la fuente primaria, clasificar el contenido y extraer reglas sin inventar parámetros.",
        "code_available": bool(record.get("code_available")),
        "status": "captured",
        "provenance": {
            "provider_id": provider_id,
            "upstream_id": record["upstream_id"],
            "first_seen_at": now.isoformat(),
            "metadata_sha256": fingerprint,
            "snapshot_path": snapshot_path.as_posix(),
            "identity_keys": _identity_keys(record),
            "work_key": _work_key(record),
            "source_revision": record.get("source_revision"),
            "repository_url": record.get("repository_url"),
            "source_path": record.get("source_path"),
            "license": record.get("license"),
            "evidence_status": "unverified_discovery",
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


def _queue_refresh(root, candidate_id, fingerprint, candidate_file, snapshot_file):
    task_id = f"catalog-refresh:{candidate_id}:{fingerprint[:12]}"
    registry = Registry(Path(root) / "state/research.sqlite3")
    try:
        registry.queue_task(
            task_id, candidate_id, "evidence_refresh", "investigator",
            json.dumps([str(candidate_file.relative_to(root)), str(snapshot_file.relative_to(root))], ensure_ascii=False),
            "La fuente publicó metadatos nuevos; revisar sin sobrescribir la evidencia existente.",
        )
    finally:
        registry.close()


def sync_sources(root=ROOT, provider_ids=None, limit=20, dry_run=False, transport=None, now=None):
    root = Path(root)
    now = _now(now)
    transport = transport or HttpTransport()
    config = validate_provider_config(read_json(root / "config/source_providers.json"))
    selected = set(provider_ids or [])
    known_ids = {item["id"] for item in config["providers"]}
    missing = selected - known_ids
    if missing:
        raise ValueError("Proveedores inexistentes: " + ", ".join(sorted(missing)))
    candidates = list_candidates(root)
    by_id = {item.get("candidate_id"): item for item in candidates}
    identity_index = _candidate_identity_index(candidates)
    work_index = {}
    for item in candidates:
        work_key = item.get("provenance", {}).get("work_key")
        if work_key:
            work_index.setdefault(work_key, item.get("candidate_id"))
    summary = {"started_at": now.isoformat(), "dry_run": dry_run, "providers": [], "created": 0, "unchanged": 0, "updates_queued": 0, "duplicates": 0, "possible_duplicates": 0}

    for provider in config["providers"]:
        if selected and provider["id"] not in selected:
            continue
        row = {"provider_id": provider["id"], "status": "skipped", "fetched": 0, "created": 0, "unchanged": 0, "updates_queued": 0, "duplicates": 0, "possible_duplicates": 0}
        if not provider.get("enabled"):
            row["reason"] = provider.get("disabled_reason", "disabled")
            summary["providers"].append(row)
            continue
        records = fetch_provider(provider, limit, transport, now)
        row["status"] = "ok"
        row["fetched"] = len(records)
        for record in records:
            if not record.get("upstream_id") or not record.get("title") or not record.get("source_url"):
                raise ValueError(f"{provider['id']}: registro incompleto")
            fingerprint = _fingerprint(record)
            provider_dir = Path("catalog/discoveries") / _safe_segment(provider["id"])
            snapshot_rel = provider_dir / f"{fingerprint}.json"
            snapshot_file = root / snapshot_rel
            snapshot = {
                "schema_version": 1,
                "provider_id": provider["id"],
                "retrieved_at": now.isoformat(),
                "metadata_sha256": fingerprint,
                "record": record,
            }
            if not dry_run and not snapshot_file.exists():
                write_json(snapshot_file, snapshot)
            candidate = _candidate_from_record(provider, record, fingerprint, snapshot_rel, now)
            candidate_id = candidate["candidate_id"]
            existing = by_id.get(candidate_id)
            duplicate_id = next((identity_index[key] for key in candidate["provenance"]["identity_keys"] if key in identity_index and identity_index[key] != candidate_id), None)
            if duplicate_id and not existing:
                row["duplicates"] += 1
                summary["duplicates"] += 1
                continue
            if not existing:
                work_key = candidate["provenance"]["work_key"]
                if work_key and work_index.get(work_key, candidate_id) != candidate_id:
                    candidate["provenance"]["possible_duplicate_of"] = work_index[work_key]
                    row["possible_duplicates"] += 1
                    summary["possible_duplicates"] += 1
                if work_key:
                    work_index.setdefault(work_key, candidate_id)
                if not dry_run:
                    stored, _ = add_candidate(candidate, root)
                else:
                    stored = candidate
                by_id[candidate_id] = stored
                for key in candidate["provenance"]["identity_keys"]:
                    identity_index[key] = candidate_id
                row["created"] += 1
                summary["created"] += 1
                continue
            previous_hash = existing.get("provenance", {}).get("metadata_sha256")
            if previous_hash == fingerprint:
                row["unchanged"] += 1
                summary["unchanged"] += 1
                continue
            if not dry_run:
                _queue_refresh(root, candidate_id, fingerprint, candidate_path(root, candidate_id), snapshot_file)
            row["updates_queued"] += 1
            summary["updates_queued"] += 1
        summary["providers"].append(row)
        transport.pause(float(provider.get("min_interval_seconds", 0)))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Extracción periódica de metadatos para el catálogo")
    parser.add_argument("--provider", action="append", dest="providers", help="ID de proveedor; repetible")
    parser.add_argument("--limit", type=int, default=20, help="máximo de registros por proveedor")
    parser.add_argument("--dry-run", action="store_true", help="consulta sin escribir candidatos, snapshots ni tareas")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 200:
        raise ValueError("--limit debe estar entre 1 y 200")
    result = sync_sources(provider_ids=args.providers, limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
