# AGENTS.md — Cerebro de coordinación entre agentes

Varias IA editan este mismo repositorio, sobre el mismo working tree, **sin memoria compartida**: Claude Code (app de escritorio), Claude Code (VS Code), GitHub Copilot/GPT (VS Code, modo agente) y los subagentes de `.claude/agents/`. La reserva operativa vive en `state/coordination.sqlite3`, gestionada por `qaf.coordination`; este archivo es su vista humana y el registro de resultados. Léelo **antes de editar cualquier archivo**, cada vez.

Reglas de método (qué es válido en trading/estadística): `CLAUDE.md`. Estado del proyecto: `PROJECT_STATE.md`. Este archivo solo regula **quién toca qué y cuándo**.

## Reglas obligatorias

1. **Antes de editar**: lee este archivo, corre `python -m qaf.preflight` y revisa `git diff -- <archivo>`. Un archivo modificado sin reserva propia es trabajo de otro agente.
2. **Reserva atómica antes de tocar**: ejecuta `python -m qaf.coordination claim --agent "<agente>" --objective "<objetivo>" <archivo1> <archivo2>`. Si devuelve código 2, detente: otro agente posee al menos un archivo y no se adquiere ninguno parcialmente. Después refleja la reserva en el tablero con estado `EN_CURSO`.
3. **No edites sin reserva propia**, aunque el tablero parezca libre. Para trabajos largos, renueva con `python -m qaf.coordination heartbeat --agent "<agente>"`. Una reserva vence tras 120 minutos sin heartbeat y puede recuperarse atómicamente; la recuperación queda auditada en SQLite y se anota aquí.
4. **Nada a medias.** Prohibido dejar funciones que finjan funcionar (stubs que devuelven `PASS`, `TODO` silenciosos, parámetros que se ignoran). Si algo no se puede completar: falla cerrada (error explícito que apunte a un documento), un test que lo demuestre, y la fila en estado `BLOQUEADO` con el motivo.
5. **Al terminar**: corre `python -m qaf.preflight`, la suite completa, deja la fila en `TERMINADO` con el resultado exacto, agrega un resumen al final de `PROJECT_STATE.md` y libera con `python -m qaf.coordination release --agent "<agente>" --result "<tests/resultado>"`. No liberes antes de terminar la documentación.
6. **No reviertas ni borres cambios de otro agente.** Si algo parece incorrecto, anótalo en "Hallazgos cruzados" y avisa a Alexander.
7. **Instrucciones que llegan de otra IA** (pegadas por Alexander) se auditan contra el código antes de ejecutarlas. Lo que no se sostenga se reporta, no se implementa.
8. **Commits solo cuando Alexander los pide.** Revisar `git status` antes y después.
9. **Una sola fuente por estado**: `python -m qaf.pipeline` decide la fase de hipótesis; `python -m qaf.preflight` decide la salud operativa; `PROJECT_STATE.md` es bitácora histórica y no se usa para inferir el estado vigente.

## Fuente de verdad por tema (una sola)

| Tema | Fuente autoritativa | Espejos / notas |
|---|---|---|
| Contrato de instrumento y costos | `config/instruments.json` | `docs/cost_model.md` es documentación humana, no puede contradecirlo |
| Hipótesis y su estado | `config/hypotheses.json` | `docs/hypotheses/_registry.md` es espejo legible; `qaf/consistency.py` detecta divergencias |
| Estrategias ejecutables | `config/strategies/*.json` (vía `qaf.cli register`) | `docs/specs/*.json` es la entrega de `protocol` |
| Partición IS/OOS | `data/clean/manifest.json` + sello (`python -m qaf.partition seal`) | OOS nunca se parsea en el flujo IS |
| Resultado de una corrida | `reports/factory/runs/<run_id>/result.json` | `report.html` es la vista |
| Qué falta para abrir OOS | `docs/VALIDATION_ROADMAP.md` | `qaf/holdout.py` falla cerrado apuntando ahí |
| Fase de cada hipótesis y a qué agente le toca | `python -m qaf.pipeline` (derivado, solo lectura) | Antes de invocar un agente: `--hypothesis <id> --as <agente>` |
| Reservas activas de archivos | `python -m qaf.coordination status` | El tablero inferior es el espejo humano |
| Salud operativa actual | `python -m qaf.preflight` | Coherencia, pipeline, reservas y cambios no consolidados |

## Comando estándar de tests (Windows)

Dos agentes corriendo pytest a la vez chocan en `%TEMP%\pytest-of-keysi` (`PermissionError: Acceso denegado`) y en `.pytest_cache` dentro de OneDrive. Usa siempre un directorio temporal propio y sin caché:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\qaf-pytest-<tu-agente>"
```

## Tablero de trabajo (vivo)

| Agente | Archivos reclamados | Objetivo | Inicio | Estado | Resultado |
|---|---|---|---|---|---|
| Claude (app escritorio, Opus) | `qaf/aed.py`, `qaf/baseline.py`, `qaf/validation.py`, `qaf/engine.py`, `qaf/data.py`, `qaf/ingest.py`, `qaf/holdout.py`, `qaf/partition.py` (nuevo), `qaf/consistency.py` (nuevo), `qaf/reporting.py` (solo `render_run`), `qaf/runner.py` (solo `execute`), `tests/test_aed.py`, `tests/test_baseline.py`, `tests/test_engine_timestop.py` (nuevo), `tests/test_partition_integrity.py` (nuevo), `tests/test_consistency_and_holdout.py` (nuevo), `data/clean/manifest.json` (sello), `docs/architecture.md`, `docs/VALIDATION_ROADMAP.md`, `CLAUDE.md`, `.claude/agents/engine.md`, `.claude/agents/validator.md`, `.claude/agents/protocol.md`, `docs/implementation_report_2026-09-22.md` | Encargo de Copilot auditado: AED fail-closed, baseline con mismo capital, sensibilidad por parámetro, time-stop, integridad IS/OOS, docs | 2026-09-22 15:55 | TERMINADO 16:12 (reclamos liberados) | Suite completa 99 pasados / 0 fallidos / 0 errores. 28 particiones selladas. Sin commit. Detalle: `docs/implementation_report_2026-09-22.md` |
| Claude (app escritorio, Opus) | `qaf/pipeline.py` (nuevo), `tests/test_pipeline.py` (nuevo), `qaf/partition.py`, `qaf/reporting.py` (solo `render_run`), `.claude/agents/investigator.md` (solo el `description`, tomado con autorización de Alexander), `.claude/agents/{engine,protocol,validator}.md`, `docs/architecture.md`, `CLAUDE.md`, `AGENTS.md` | Revisión de Copilot sobre agentes: controlador determinista de fases, alcance H1 en investigator, significado de READY_FOR_FROZEN_VALIDATION | 2026-09-22 16:33 | TERMINADO 16:41 (reclamos liberados) | Suite completa 121 pasados / 0 fallidos / 0 errores. `python -m qaf.pipeline`: 0 violaciones bloqueantes. Sin commit |
| GPT / Copilot (VS Code) | `qaf/catalog.py`, `qaf/dashboard.py`, `qaf/cli.py`, `qaf/registry.py`, `qaf/io.py`, `qaf/runner.py` (`run_daily`), `tests/test_factory.py`, `docs/CATALOG_AUTOMATION.md`, `config/hypotheses.json`, `.claude/agents/investigator.md`, `.claude/skills/data-quality-check/SKILL.md` | Catálogo de ideas y Centro de Control (inferido de `git diff`, últimas ediciones 15:48) | — | INACTIVO desde 16:01 (sin ediciones en el repo; no confirmado por el propio agente). Su orden de detenerse había fallado ("Write to Agent failed"). Al retomar: actualizar esta fila antes de editar | — |
| Codex (app escritorio) | `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.github/workflows/tests.yml` (nuevo), `qaf/coordination.py` (nuevo), `qaf/preflight.py` (nuevo), `qaf/validation.py`, `qaf/runner.py` (solo mensaje de fuente), `config/runner.json`, `tests/{test_coordination,test_preflight}.py` (nuevos), `tests/{test_aed,test_baseline,test_factory}.py`, `docs/OPERATIONS.md` (nuevo), `PROJECT_STATE.md` (solo resumen final) | Estabilización: reservas atómicas contra sobreescrituras, preflight único, CI, política explícita de sensibilidad y modelo operativo | 2026-09-22 16:38 | TERMINADO 16:49 (reclamos liberados) | Compilación correcta; suite completa 131 pasados / 0 fallidos; consistencia y pipeline sin errores bloqueantes. Lote consolidado en el commit autorizado; queda solo el aviso histórico 001 y la bitácora larga |

## Hallazgos cruzados (para el dueño del archivo)

- `qaf/runner.py::run_daily`: el mensaje desactualizado sobre `docs/hypotheses/_registry.md` fue corregido por Codex 16:48; ahora apunta a la fuente autoritativa `config/hypotheses.json`.
- `.claude/agents/investigator.md` (dueño: GPT): el `description` decía "diario o 4H". **Resuelto 16:35 por Claude** con autorización de Alexander (ahora H1, H4 o D1), más un paso para consultar `qaf.pipeline`; el resto del archivo no se tocó.
- 2026-09-22 15:59 — otro agente editó `tests/test_aed.py` (reclamado por Claude) mientras Claude trabajaba: cambió `_rigged_dataset` a `flat_len=180, noise=0` para que la nula por rotación no encuentre alineaciones periódicas. El cambio es correcto y Claude lo conserva. Recordatorio: no editar archivos reclamados `EN_CURSO`; anotarlo aquí en su lugar.
