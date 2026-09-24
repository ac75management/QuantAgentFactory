#!/usr/bin/env python3
"""Captura manual de candidatos desde Quantpedia (lote inicial)."""

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
CATALOG = ROOT / "catalog/candidates"

# Candidatos manuales de Quantpedia — alcance H1/H4/D1 CFD/futuros
QUANTPEDIA_BATCH = [
    {
        "name": "RSI Oversold/Overbought en índices (H4)",
        "source_name": "Quantpedia — RSI(14) estrategia clásica",
        "source_url": "https://quantpedia.com/strategies/rsi-2-strategy/",
        "primary_source_url": "https://quantpedia.com/strategies/rsi-2-strategy/",
        "publication_date": "2020-01-01",
        "content_type": "strategy",
        "original_asset_classes": ["indices"],
        "original_timeframes": ["D1"],
        "proposed_targets": [
            {"symbol": "SP500", "timeframe": "H4"},
            {"symbol": "NAS100", "timeframe": "H4"},
        ],
        "rules_summary": "RSI(2) en D1: enter long RSI < 30, exit RSI > 70. Clásico mean reversion de Connors.",
        "code_available": False,
        "scope_status": "eligible_for_review",
        "notes": "Alcance H4/D1, CFD. Requiere verificar si es distinto de 003 (ya descartada por edge débil).",
    },
    {
        "name": "Momentum cruzado SMA(20/50) en EURUSD (H1)",
        "source_name": "Quantpedia — SMA Crossover Strategies",
        "source_url": "https://quantpedia.com/strategies/sma-crossover/",
        "primary_source_url": "https://quantpedia.com/strategies/sma-crossover/",
        "publication_date": "2019-06-01",
        "content_type": "strategy",
        "original_asset_classes": ["fx"],
        "original_timeframes": ["D1"],
        "proposed_targets": [
            {"symbol": "EURUSD", "timeframe": "H1"},
            {"symbol": "GBPUSD", "timeframe": "H1"},
        ],
        "rules_summary": "SMA(20) cruza SMA(50): enter long si corta > larga, exit si corta < larga.",
        "code_available": False,
        "scope_status": "eligible_for_review",
        "notes": "Alcance H1/D1, FX. Familia trend_cross potencial.",
    },
    {
        "name": "Breakout de canal de 20 barras (DAX, H4)",
        "source_name": "Quantpedia — Breakout Strategies",
        "source_url": "https://quantpedia.com/strategies/breakout/",
        "primary_source_url": "https://quantpedia.com/strategies/breakout/",
        "publication_date": "2020-03-01",
        "content_type": "strategy",
        "original_asset_classes": ["indices"],
        "original_timeframes": ["H4"],
        "proposed_targets": [
            {"symbol": "DAX", "timeframe": "H4"},
            {"symbol": "SP500", "timeframe": "H4"},
        ],
        "rules_summary": "Enter long si close > max(high, 20 barras); exit si close < min(low, 20 barras).",
        "code_available": False,
        "scope_status": "eligible_for_review",
        "notes": "Alcance H4, CFD. Familia channel_breakout (similar a 005 rechazada, pero H4 no H1).",
    },
    {
        "name": "ATR dinámico en ORB (Open Range Breakout, US30 H1)",
        "source_name": "Quantpedia — Open Range Breakout",
        "source_url": "https://quantpedia.com/strategies/open-range-breakout/",
        "primary_source_url": "https://quantpedia.com/strategies/open-range-breakout/",
        "publication_date": "2021-01-15",
        "content_type": "strategy",
        "original_asset_classes": ["indices"],
        "original_timeframes": ["D1"],
        "proposed_targets": [
            {"symbol": "US30", "timeframe": "H1"},
        ],
        "rules_summary": "ORB: enter si close > open + ATR(14)*0.5; exit si close < open - ATR(14)*0.5.",
        "code_available": False,
        "scope_status": "eligible_for_review",
        "notes": "Alcance H1, CFD. Familia volatility_based. Distinción vs. 005 (channel_breakout).",
    },
]

def generate_candidate_id(name: str) -> str:
    """Genera ID único para candidato."""
    import hashlib
    hash_val = hashlib.sha256(name.encode()).hexdigest()[:16].upper()
    return f"IDEA-QPD-{hash_val}"

# Crear carpeta si no existe
CATALOG.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CAPTURA DE CANDIDATOS QUANTPEDIA — LOTE INICIAL")
print("=" * 70)

created_ids = []

for candidate in QUANTPEDIA_BATCH:
    candidate_id = generate_candidate_id(candidate["name"])
    candidate["candidate_id"] = candidate_id
    candidate["status"] = "captured"
    candidate["created_at"] = datetime.now(timezone.utc).isoformat()

    file_path = CATALOG / f"{candidate_id}.json"

    with open(file_path, "w") as f:
        json.dump(candidate, f, indent=2, ensure_ascii=False)

    created_ids.append(candidate_id)
    print(f"\n✓ {candidate_id}")
    print(f"  Nombre: {candidate['name']}")
    print(f"  Alcance: {', '.join([t['symbol'] + '/' + t['timeframe'] for t in candidate['proposed_targets']])}")
    print(f"  Archivo: {file_path.name}")

print("\n" + "=" * 70)
print(f"RESUMEN: {len(created_ids)} candidatos capturados")
print("=" * 70)
print("\nProximos pasos:")
print("1. Revisar fichas en catalog/candidates/IDEA-QPD-*.json")
print("2. Investigador verifica fuentes primarias y decide: promoted/rejected")
print("3. Si promoted: protocol → engine → validator")
print("4. Si rejected: documentar razón en review.decision_reason")
print("\nComandos útiles:")
print("  python -m qaf.coordination status  # Ver reservas")
print("  python -m qaf.preflight            # Verificar coherencia")
