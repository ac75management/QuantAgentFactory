import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from .contracts import TIMEFRAMES
from .io import ROOT, digest, read_json, write_json, write_json_exclusive
from .registry import Registry


CATALOG_STATUSES = {"captured", "triage", "eligible", "needs_data", "rejected", "promoted"}
ACCESS_LEVELS = {"public", "subscription", "licensed_api", "unknown"}
CONTENT_TYPES = {"strategy", "methodology", "agent_system", "dataset", "survey"}
REVIEW_DECISIONS = {"eligible", "needs_data", "rejected"}
IMPLEMENTATION_TYPES = {"replication", "adaptation"}
ADAPTATION_DIMENSIONS = {"vehicle", "instrument", "session", "frequency", "portfolio", "costs"}
CATALOG_DIRECTORY = Path("catalog/candidates")


def candidate_path(root, candidate_id):
    """Canonical, Git-tracked path for a catalog candidate."""
    return Path(root) / CATALOG_DIRECTORY / f"{candidate_id}.json"


def _validate_candidate_id(candidate_id):
    if not isinstance(candidate_id, str) or not re.fullmatch(r"IDEA-[A-Z0-9-]{4,40}", candidate_id):
        raise ValueError("candidate_id inválido")
    return candidate_id


def _texts(value, name, required=True):
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"{name} debe ser una lista{' no vacía' if required else ''}")
    cleaned = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{name} contiene un valor inválido")
        cleaned.append(item.strip())
    return cleaned


def _url(value, name, required=True):
    if value in (None, "") and not required:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} inválida")
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} debe ser una URL http(s)")
    return value.strip()


def _target_pairs(candidate):
    explicit = candidate.get("proposed_targets", [])
    if explicit:
        return {(item["symbol"].upper(), item["timeframe"].upper()) for item in explicit}
    # Backward compatibility for catalog entries created before proposed_targets.
    return {
        (symbol.upper(), timeframe.upper())
        for symbol in candidate.get("instruments", [])
        for timeframe in candidate.get("original_timeframes", [])
    }


def validate_candidate(candidate):
    candidate = dict(candidate)
    for key in ("name", "source_name", "source_url", "rules_summary"):
        if not isinstance(candidate.get(key), str) or not candidate[key].strip():
            raise ValueError(f"Candidato incompleto: {key}")
        candidate[key] = candidate[key].strip()
    candidate["source_url"] = _url(candidate["source_url"], "source_url")
    candidate["primary_source_url"] = _url(candidate.get("primary_source_url"), "primary_source_url", False)
    candidate["original_asset_classes"] = _texts(candidate.get("original_asset_classes"), "original_asset_classes")
    candidate["original_timeframes"] = _texts(candidate.get("original_timeframes"), "original_timeframes")
    candidate["data_requirements"] = _texts(candidate.get("data_requirements", []), "data_requirements", False)
    candidate["instruments"] = _texts(candidate.get("instruments", []), "instruments", False)
    proposed_targets = candidate.get("proposed_targets", [])
    if not isinstance(proposed_targets, list):
        raise ValueError("proposed_targets debe ser una lista")
    cleaned_targets = []
    for target in proposed_targets:
        if not isinstance(target, dict):
            raise ValueError("proposed_targets contiene un valor inválido")
        symbol = target.get("symbol")
        timeframe = target.get("timeframe")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Cada proposed_target requiere symbol")
        if not isinstance(timeframe, str) or timeframe.upper() not in TIMEFRAMES:
            raise ValueError(f"Cada proposed_target requiere timeframe en {sorted(TIMEFRAMES)}")
        cleaned_targets.append({"symbol": symbol.strip().upper(), "timeframe": timeframe.upper()})
    pairs = {(item["symbol"], item["timeframe"]) for item in cleaned_targets}
    if len(pairs) != len(cleaned_targets):
        raise ValueError("proposed_targets contiene duplicados")
    candidate["proposed_targets"] = cleaned_targets
    access = candidate.get("access_level", "unknown")
    if access not in ACCESS_LEVELS:
        raise ValueError(f"access_level debe ser uno de {sorted(ACCESS_LEVELS)}")
    candidate["access_level"] = access
    content_type = candidate.get("content_type", "strategy")
    if content_type not in CONTENT_TYPES:
        raise ValueError(f"content_type debe ser uno de {sorted(CONTENT_TYPES)}")
    candidate["content_type"] = content_type
    if type(candidate.get("code_available", False)) is not bool:
        raise ValueError("code_available debe ser booleano")
    candidate["code_available"] = candidate.get("code_available", False)
    published = candidate.get("publication_date")
    if published:
        try:
            date.fromisoformat(published)
        except (TypeError, ValueError):
            raise ValueError("publication_date debe ser una fecha ISO YYYY-MM-DD")
    status = candidate.get("status", "captured")
    if status not in CATALOG_STATUSES:
        raise ValueError(f"status debe ser uno de {sorted(CATALOG_STATUSES)}")
    candidate["status"] = status
    return candidate


def assess_candidate(candidate, instruments):
    """Cheap triage only. It never claims that a strategy is valid or profitable."""
    candidate = validate_candidate(candidate)
    enabled_symbols = {symbol for symbol, item in instruments.items() if item.get("status") == "research"}
    enabled_classes = {item.get("asset_class") for item in instruments.values() if item.get("status") == "research"}
    enabled_timeframes = {tf for item in instruments.values() for tf in item.get("timeframes", [])}
    enabled_pairs = {(symbol, tf) for symbol, item in instruments.items() if item.get("status") == "research" for tf in item.get("timeframes", [])}
    source_timeframes = {tf.upper() for tf in candidate["original_timeframes"]}
    source_instruments = {symbol.upper() for symbol in candidate["instruments"]}
    source_classes = {item.lower() for item in candidate["original_asset_classes"]}
    target_pairs = _target_pairs(candidate)
    target_timeframes = {timeframe for _, timeframe in target_pairs}

    score = 0
    reasons = []
    blockers = []
    if candidate.get("primary_source_url"):
        score += 25; reasons.append("Tiene enlace a la fuente primaria.")
    else:
        blockers.append("Falta localizar y revisar la fuente primaria.")
    if len(candidate["rules_summary"]) >= 80:
        score += 20; reasons.append("La descripción contiene reglas preliminares revisables.")
    else:
        blockers.append("Las reglas son demasiado breves para reproducirlas.")
    if target_pairs & enabled_pairs:
        score += 20; reasons.append("Existe un objetivo explícito habilitado en el universo de investigación.")
    elif source_instruments & enabled_symbols or source_classes & {str(x).lower() for x in enabled_classes}:
        score += 10; blockers.append("La clase coincide, pero falta fijar un objetivo símbolo/timeframe habilitado.")
    else:
        blockers.append("No coincide todavía con un instrumento o clase habilitada.")
    if target_timeframes and source_timeframes & target_timeframes:
        score += 15; reasons.append("El marco original está disponible.")
    elif target_timeframes <= set(TIMEFRAMES) and target_timeframes:
        score += 8; blockers.append("El objetivo cambia la frecuencia original; debe declararse como adaptación.")
    elif source_timeframes & set(TIMEFRAMES):
        score += 8; blockers.append("El marco existe en QAF, pero no está habilitado para un instrumento coincidente.")
    else:
        blockers.append("El marco original requiere datos o arquitectura adicional.")
    if not candidate["data_requirements"] or all(req.lower() in {"ohlc", "volume", "calendar"} for req in candidate["data_requirements"]):
        score += 10; reasons.append("Los requisitos declarados parecen reproducibles con datos simples.")
    else:
        blockers.append("Requiere datos externos que deben confirmarse antes de implementar.")
    if candidate["access_level"] == "public":
        score += 10; reasons.append("La referencia declarada es pública.")

    research_symbols = {symbol for symbol,item in instruments.items() if item.get("status") == "research"}
    pending_symbols = {symbol for symbol,item in instruments.items() if item.get("status") == "pending"}
    target_symbols = {symbol for symbol, _ in target_pairs}
    if candidate["content_type"] == "methodology":
        lane = "methodology"
    elif candidate["content_type"] in {"agent_system", "survey"}:
        lane = "agent_research"
    elif target_pairs & enabled_pairs:
        lane = "mt5_now"
    elif target_symbols & pending_symbols or target_symbols or source_instruments or source_classes:
        lane = "future_market"
    else:
        lane = "manual_review"
    verdict = "eligible_for_evidence_review" if score >= 60 else "needs_information"
    return {"score": score, "verdict": verdict, "research_lane": lane, "reasons": reasons, "blockers": blockers}


def add_candidate(candidate, root=ROOT, before_write=None):
    root = Path(root)
    candidate = validate_candidate(candidate)
    assessment = assess_candidate(candidate, read_json(root / "config/instruments.json"))
    candidate_id = candidate.get("candidate_id")
    if candidate_id:
        _validate_candidate_id(candidate_id)
    else:
        candidate_id = "IDEA-" + uuid4().hex[:10].upper()
    if candidate["status"] != "captured":
        raise ValueError("Una idea nueva debe iniciar con status captured")
    now = datetime.now(timezone.utc).isoformat()
    record = {**candidate, "candidate_id": candidate_id, "created_at": now, "assessment": assessment}
    path = candidate_path(root, candidate_id)
    if before_write:
        before_write()
    try:
        write_json_exclusive(path, record)
    except FileExistsError as error:
        raise ValueError(f"El candidato {candidate_id} ya existe") from error
    if before_write:
        before_write()
    registry = Registry(root / "state/research.sqlite3")
    try:
        registry.queue_task(
            "catalog:" + candidate_id, candidate_id, "evidence_review", "investigator",
            json.dumps([str(path.relative_to(root))], ensure_ascii=False),
            "Idea catalogada; revisar fuente primaria y reglas antes de crear una hipótesis.",
        )
    finally:
        registry.close()
    return record, path


def acknowledge_refresh(candidate_id, fingerprint, root=ROOT):
    """Persist that investigator inspected one immutable metadata refresh."""
    root = Path(root)
    _validate_candidate_id(candidate_id)
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("metadata_sha256 debe tener 64 caracteres hexadecimales en minúscula")
    path = candidate_path(root, candidate_id)
    if not path.exists():
        raise ValueError(f"Candidato inexistente: {candidate_id}")
    candidate = read_json(path)
    provider_id = candidate.get("provenance", {}).get("provider_id")
    if not isinstance(provider_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,60}", provider_id):
        raise ValueError("El candidato no proviene de source-sync")
    snapshot_path = root / "catalog/discoveries" / provider_id / f"{fingerprint}.json"
    if not snapshot_path.exists():
        raise ValueError(f"Snapshot inexistente para {fingerprint}")
    from .source_sync import validate_snapshot_file
    validate_snapshot_file(snapshot_path, fingerprint, provider_id)
    acknowledged = candidate.setdefault("provenance", {}).setdefault("acknowledged_fingerprints", [])
    if fingerprint not in acknowledged:
        acknowledged.append(fingerprint)
        candidate["provenance"]["acknowledged_fingerprints"] = sorted(set(acknowledged))
        write_json(path, candidate)
    task_id = f"catalog-refresh:{candidate_id}:{fingerprint}"
    registry = Registry(root / "state/research.sqlite3")
    try:
        row = registry.db.execute("SELECT status FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row and row["status"] not in {"completed", "blocked", "failed", "cancelled"}:
            registry.finish_task(
                task_id,
                "completed",
                "METADATA_REFRESH_ACKNOWLEDGED",
                "Investigator revisó el snapshot y reconoció esta huella sin sobrescribir evidencia.",
                json.dumps([str(path.relative_to(root)), str(snapshot_path.relative_to(root))], ensure_ascii=False),
            )
    finally:
        registry.close()
    return candidate, path


def _required_text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"La revisión requiere {name}")
    return value.strip()


def validate_review(review, candidate, instruments):
    """Validate an evidence review. This is not a strategy-performance verdict."""
    if not isinstance(review, dict):
        raise ValueError("La revisión debe ser un objeto JSON")
    review = dict(review)
    candidate_id = candidate.get("candidate_id")
    if review.get("candidate_id") not in (None, candidate_id):
        raise ValueError("candidate_id de la revisión no coincide con el candidato")
    review["candidate_id"] = candidate_id
    decision = review.get("decision")
    if decision not in REVIEW_DECISIONS:
        raise ValueError(f"decision debe ser uno de {sorted(REVIEW_DECISIONS)}")
    review["reviewer"] = _required_text(review.get("reviewer"), "reviewer")
    review["reason_code"] = _required_text(review.get("reason_code"), "reason_code")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,60}", review["reason_code"]):
        raise ValueError("reason_code debe usar MAYÚSCULAS_Y_GUIONES_BAJOS")
    review["decision_reason"] = _required_text(review.get("decision_reason"), "decision_reason")
    review["decision"] = decision

    if decision != "eligible":
        return review
    if candidate.get("content_type") != "strategy":
        raise ValueError("Solo una estrategia puede declararse eligible para hipótesis")
    if candidate.get("assessment", {}).get("research_lane") != "mt5_now":
        raise ValueError("Solo el carril mt5_now puede promocionarse en la campaña actual")

    review["primary_source_url"] = _url(
        review.get("primary_source_url") or candidate.get("primary_source_url"),
        "primary_source_url",
    )
    for key in (
        "primary_source_title", "evidence_summary", "mechanism", "original_market",
        "original_vehicle", "source_rule_id", "target_symbol", "target_timeframe",
    ):
        review[key] = _required_text(review.get(key), key)
    source_rule_id = review["source_rule_id"].lower().replace("_", "-")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", source_rule_id):
        raise ValueError("source_rule_id debe ser un identificador estable de 3 a 80 caracteres")
    review["source_rule_id"] = source_rule_id
    review["primary_source_authors"] = _texts(review.get("primary_source_authors"), "primary_source_authors")
    for key in (
        "original_instruments", "original_timeframes", "original_rules",
        "data_requirements", "cost_assumptions", "limitations",
    ):
        review[key] = _texts(review.get(key), key)
    review["ambiguities"] = _texts(review.get("ambiguities", []), "ambiguities", False)

    implementation_type = review.get("implementation_type")
    if implementation_type not in IMPLEMENTATION_TYPES:
        raise ValueError(f"implementation_type debe ser uno de {sorted(IMPLEMENTATION_TYPES)}")
    review["implementation_type"] = implementation_type
    notes = review.get("adaptation_notes")
    if implementation_type == "adaptation":
        review["adaptation_notes"] = _required_text(notes, "adaptation_notes")
        dimensions = _texts(review.get("adaptation_dimensions"), "adaptation_dimensions")
        normalized_dimensions = {item.lower() for item in dimensions}
        if not normalized_dimensions <= ADAPTATION_DIMENSIONS:
            raise ValueError(f"adaptation_dimensions solo admite {sorted(ADAPTATION_DIMENSIONS)}")
        review["adaptation_dimensions"] = sorted(normalized_dimensions)
    elif notes not in (None, ""):
        raise ValueError("Una replication no debe declarar adaptation_notes")
    else:
        review["adaptation_notes"] = None
        review["adaptation_dimensions"] = []

    symbol = review["target_symbol"].upper()
    timeframe = review["target_timeframe"].upper()
    if symbol not in instruments or instruments[symbol].get("status") != "research":
        raise ValueError("target_symbol no está habilitado para investigación")
    if timeframe not in instruments[symbol].get("timeframes", []):
        raise ValueError("target_timeframe no está habilitado para target_symbol")
    allowed_targets = _target_pairs(candidate)
    if allowed_targets and (symbol, timeframe) not in allowed_targets:
        raise ValueError("El objetivo de la revisión no fue declarado en proposed_targets")
    original_symbols = {item.upper() for item in review["original_instruments"]}
    original_timeframes = {item.upper() for item in review["original_timeframes"]}
    dimensions = set(review["adaptation_dimensions"])
    if implementation_type == "replication" and (symbol not in original_symbols or timeframe not in original_timeframes):
        raise ValueError("Una replication debe conservar instrumento y timeframe originales")
    if implementation_type == "adaptation":
        if symbol not in original_symbols and "instrument" not in dimensions:
            raise ValueError("La adaptación cambia el instrumento pero no declara esa dimensión")
        if timeframe not in original_timeframes and "frequency" not in dimensions:
            raise ValueError("La adaptación cambia la frecuencia pero no declara esa dimensión")
    review["target_symbol"] = symbol
    review["target_timeframe"] = timeframe
    return review


def _finish_evidence_task(registry, candidate_id, decision, relative_path):
    task_id = "catalog:" + candidate_id
    row = registry.db.execute("SELECT status FROM tasks WHERE task_id=?", (task_id,)).fetchone()
    if not row or row["status"] in {"completed", "blocked", "failed", "cancelled"}:
        return
    status = "blocked" if decision == "needs_data" else "completed"
    registry.finish_task(
        task_id,
        status,
        "EVIDENCE_" + decision.upper(),
        f"Revisión de evidencia terminada con decisión {decision}.",
        json.dumps([relative_path], ensure_ascii=False),
    )


def review_candidate(candidate_id, review, root=ROOT):
    root = Path(root)
    _validate_candidate_id(candidate_id)
    path = candidate_path(root, candidate_id)
    if not path.exists():
        raise ValueError(f"Candidato inexistente: {candidate_id}")
    registry = Registry(root / "state/research.sqlite3")
    try:
        registry.db.execute("BEGIN IMMEDIATE")
        candidate = read_json(path)
        if candidate.get("status") == "promoted":
            raise ValueError("Una idea promovida no puede volver a revisarse")
        instruments = read_json(root / "config/instruments.json")
        validated = validate_review(review, candidate, instruments)
        existing = candidate.get("review")
        if existing:
            comparable_existing = {k: v for k, v in existing.items() if k != "reviewed_at"}
            if comparable_existing != validated:
                raise ValueError("El candidato ya tiene una revisión; no se sobrescribe evidencia")
            canonical_path = candidate_path(root, candidate_id)
            if path != canonical_path:
                write_json(canonical_path, candidate)
            _finish_evidence_task(registry, candidate_id, existing["decision"], str(canonical_path.relative_to(root)))
            registry.db.execute("COMMIT")
            return candidate, canonical_path
        validated["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        candidate["review"] = validated
        candidate["status"] = validated["decision"]
        if validated.get("primary_source_url"):
            candidate["primary_source_url"] = validated["primary_source_url"]
        candidate["assessment"] = assess_candidate(candidate, instruments)
        canonical_path = candidate_path(root, candidate_id)
        write_json(canonical_path, candidate)
        _finish_evidence_task(registry, candidate_id, validated["decision"], str(canonical_path.relative_to(root)))
        registry.db.execute("COMMIT")
        return candidate, canonical_path
    except BaseException:
        if registry.db.in_transaction:
            registry.db.execute("ROLLBACK")
        raise
    finally:
        registry.close()


def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:90].rstrip("-")


def _evidence_fingerprint(review):
    url = review["primary_source_url"].rstrip("/").lower()
    return digest({
        "primary_source_url": url,
        "source_rule_id": review["source_rule_id"],
        "symbol": review["target_symbol"],
        "timeframe": review["target_timeframe"],
        "implementation_type": review["implementation_type"],
    })


def _write_text_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _render_hypothesis_document(hypothesis, candidate, review):
    bullets = lambda rows: "\n".join(f"- {row}" for row in rows) or "- Ninguna declarada."
    adaptation = review.get("adaptation_notes") or "La revisión la clasifica como réplica; no declara cambios de implementación."
    return f"""# {candidate['name']}

Estado: **pendiente de protocolo**. Esta ficha registra una hipótesis investigable; no afirma rentabilidad y no contiene resultados de backtest.

## Trazabilidad

- Hipótesis: `{hypothesis['id']}`
- Candidato: `{candidate['candidate_id']}`
- Fuente primaria: [{review['primary_source_title']}]({review['primary_source_url']})
- Autores: {', '.join(review['primary_source_authors'])}
- Mercado y vehículo originales: {review['original_market']} / {review['original_vehicle']}
- Objetivo QAF: {review['target_symbol']} / {review['target_timeframe']}
- Tratamiento: {review['implementation_type']}
- Regla fuente: `{review['source_rule_id']}`
- Dimensiones adaptadas: {', '.join(review['adaptation_dimensions']) or 'ninguna'}

## Evidencia revisada

{review['evidence_summary']}

## Mecanismo propuesto

{review['mechanism']}

## Reglas publicadas que deben conservarse

{bullets(review['original_rules'])}

## Réplica o adaptación

{adaptation}

## Ambigüedades todavía abiertas

{bullets(review['ambiguities'])}

## Datos requeridos

{bullets(review['data_requirements'])}

## Costos y fricciones que el contrato debe modelar

{bullets(review['cost_assumptions'])}

## Límites de la evidencia

{bullets(review['limitations'])}

## Decisión de la revisión

{review['decision_reason']}

Siguiente paso: `protocol` debe convertir esta hipótesis en reglas numéricas congeladas o bloquearla si las ambigüedades impiden una implementación fiel. OOS permanece cerrado.
"""


def _ensure_registry_row(root, hypothesis, candidate, review):
    path = root / "docs/hypotheses/_registry.md"
    line_prefix = f"| {hypothesis['id']} |"
    text = path.read_text(encoding="utf-8-sig") if path.exists() else (
        "# Registro de hipótesis — QuantAgentFactory\n\n"
        "| # | slug | fecha | fuente/autor | activo/timeframe | estado |\n"
        "|---|---|---|---|---|---|\n"
    )
    if any(line.startswith(line_prefix) for line in text.splitlines()):
        return path
    safe = lambda value: str(value).replace("|", "/").replace("\n", " ")
    source = safe(", ".join(review["primary_source_authors"]) + " — " + review["primary_source_title"])
    row = f"| {hypothesis['id']} | {safe(hypothesis['slug'])} | {hypothesis['created_at']} | {source} | {review['target_symbol']} / {review['target_timeframe']} | **pendiente de protocolo** |"
    _write_text_atomic(path, text.rstrip() + "\n" + row + "\n")
    return path


def promote_candidate(candidate_id, root=ROOT):
    """Create one registered hypothesis from one reviewed candidate, at most once."""
    root = Path(root)
    _validate_candidate_id(candidate_id)
    candidate_path_value = candidate_path(root, candidate_id)
    if not candidate_path_value.exists():
        raise ValueError(f"Candidato inexistente: {candidate_id}")
    registry = Registry(root / "state/research.sqlite3")
    try:
        registry.db.execute("BEGIN IMMEDIATE")
        candidate = read_json(candidate_path_value)
        hypotheses_path = root / "config/hypotheses.json"
        payload = read_json(hypotheses_path) if hypotheses_path.exists() else {"version": 1, "hypotheses": []}
        rows = payload.get("hypotheses")
        if not isinstance(rows, list):
            raise ValueError("config/hypotheses.json requiere una lista hypotheses")
        existing = next((row for row in rows if row.get("candidate_id") == candidate_id), None)
        if existing:
            if not candidate.get("review"):
                raise ValueError("La hipótesis referencia un candidato sin revisión de evidencia")
            review = validate_review(candidate["review"], candidate, read_json(root / "config/instruments.json"))
            existing_slug = existing.get("slug")
            if not isinstance(existing_slug, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,89}", existing_slug):
                raise ValueError("La hipótesis existente tiene un slug inválido")
            hypothesis_doc = root / "docs/hypotheses" / f"{existing_slug}.md"
            if not hypothesis_doc.exists():
                _write_text_atomic(hypothesis_doc, _render_hypothesis_document(existing, candidate, review))
            registry_doc = _ensure_registry_row(root, existing, candidate, review)
            candidate["status"] = "promoted"
            candidate["hypothesis_id"] = existing["id"]
            canonical_path = candidate_path(root, candidate_id)
            write_json(canonical_path, candidate)
            registry.queue_task(
                "protocol:" + existing["id"], existing["id"], "contract", "protocol",
                json.dumps([str(canonical_path.relative_to(root)), str(hypothesis_doc.relative_to(root)), str(registry_doc.relative_to(root))], ensure_ascii=False),
                "Hipótesis registrada; falta contrato numérico antes de ejecutar.",
            )
            registry.db.execute("COMMIT")
            return existing, canonical_path

        if candidate.get("status") != "eligible" or not candidate.get("review"):
            raise ValueError("Solo una idea revisada con estado eligible puede promocionarse")
        review = validate_review(candidate["review"], candidate, read_json(root / "config/instruments.json"))
        fingerprint = _evidence_fingerprint(review)
        duplicate = next((row for row in rows if row.get("evidence_fingerprint") == fingerprint), None)
        if duplicate:
            raise ValueError(f"La evidencia ya originó la hipótesis {duplicate['id']}")
        numeric_ids = [int(row["id"]) for row in rows if isinstance(row.get("id"), str) and row["id"].isdigit()]
        hypothesis_id = str(max(numeric_ids, default=0) + 1).zfill(3)
        slug = _slug(f"{review['target_symbol']}-{review['target_timeframe']}-{candidate['name']}")
        if not slug:
            raise ValueError("No se pudo construir un slug para la hipótesis")
        if any(row.get("slug") == slug for row in rows):
            raise ValueError(f"Ya existe una hipótesis con slug {slug}")
        hypothesis_doc = root / "docs/hypotheses" / f"{slug}.md"
        if hypothesis_doc.exists():
            raise ValueError(f"El documento de hipótesis ya existe: {hypothesis_doc}")
        source = ", ".join(review["primary_source_authors"]) + " — " + review["primary_source_title"]
        hypothesis = {
            "id": hypothesis_id,
            "slug": slug,
            "created_at": date.today().isoformat(),
            "candidate_id": candidate_id,
            "source": source,
            "primary_source_url": review["primary_source_url"],
            "source_rule_id": review["source_rule_id"],
            "symbol": review["target_symbol"],
            "timeframe": review["target_timeframe"],
            "implementation_type": review["implementation_type"],
            "adaptation_dimensions": review["adaptation_dimensions"],
            "evidence_fingerprint": fingerprint,
            "status": "pending",
            "reason_code": "AWAITING_PROTOCOL",
            "reason": "La evidencia fue revisada; todavía no existe contrato ni backtest.",
            "next_action": "Protocol debe congelar reglas numéricas o bloquear la hipótesis.",
        }
        rows.append(hypothesis)
        payload["version"] = payload.get("version", 1)
        write_json(hypotheses_path, payload)
        _write_text_atomic(hypothesis_doc, _render_hypothesis_document(hypothesis, candidate, review))
        registry_doc = _ensure_registry_row(root, hypothesis, candidate, review)
        candidate["status"] = "promoted"
        candidate["hypothesis_id"] = hypothesis_id
        candidate["promoted_at"] = datetime.now(timezone.utc).isoformat()
        canonical_path = candidate_path(root, candidate_id)
        write_json(canonical_path, candidate)
        registry.queue_task(
            "protocol:" + hypothesis_id, hypothesis_id, "contract", "protocol",
            json.dumps([str(canonical_path.relative_to(root)), str(hypothesis_doc.relative_to(root)), str(registry_doc.relative_to(root))], ensure_ascii=False),
            "Hipótesis registrada; falta contrato numérico antes de ejecutar.",
        )
        registry.db.execute("COMMIT")
        return hypothesis, canonical_path
    except BaseException:
        if registry.db.in_transaction:
            registry.db.execute("ROLLBACK")
        raise
    finally:
        registry.close()


def list_candidates(root=ROOT):
    """Every candidate of the versioned catalog. An unreadable file fails loudly:
    skipping it would hide evidence and let source-sync create a duplicate."""
    rows = []
    for path in sorted((Path(root) / CATALOG_DIRECTORY).glob("*.json")):
        try:
            row = read_json(path)
        except (OSError, ValueError) as error:
            raise ValueError(f"Candidato ilegible en el catálogo: {path.name} ({error})") from error
        if not isinstance(row, dict) or row.get("candidate_id") != path.stem:
            raise ValueError(f"Candidato inconsistente en el catálogo: {path.name} no declara candidate_id={path.stem}")
        rows.append(row)
    return rows
