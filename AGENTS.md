# AGENTS.md — see docs/archive/reviews/AUDIT_GROK_2026-09-24.md for full coordination order.

**TEMPORARY NOTE FROM GROK:** A prior commit accidentally replaced this file with PLACEHOLDER. Claude must restore AGENTS.md from git history (commit before c13419c) and re-apply only the section below under Hallazgos cruzados.

### 2026-09-24 — ORDEN ALEXANDER + AUDITORÍA GROK (acción inmediata)

**Documento completo:** `docs/archive/reviews/AUDIT_GROK_2026-09-24.md`

**Prioridad:** no producir más estrategias; Experiment Registry primero.

1. **Claude** — Diseñar Experiment Registry mínimo (schema + enganche pipeline + DoD). ≤40 líneas en Hallazgos cruzados. No reescribir motor. No cambiar umbrales.
2. **Codex** — Implementar registry append-only + tests + N total/por familia. No OOS. No features extra.
3. **Ambos** — preflight + suite + bitácora.

**Prohibido:** abrir OOS; rescatar 001–011; nuevos agentes LLM; cambiar puertas; ASSUMED sin etiqueta.

**DoD:** §6 de AUDIT_GROK.

**Restore:** `git show 8c5937e7adf50096360978a81645bd2e810381e1:AGENTS.md` then insert the order above at the top of Hallazgos cruzados.
