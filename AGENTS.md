# AGENTS.md — Cerebro de coordinación entre agentes

Varias IA editan este mismo repositorio, sobre el mismo working tree, **sin memoria compartida**: Claude Code (app de escritorio y VS Code), GitHub Copilot/GPT y Codex, más los subagentes de `.claude/agents/`. La reserva operativa vive en `state/coordination.sqlite3`, gestionada por `qaf.coordination`. Este archivo es su vista humana y la **única copia** del protocolo de coordinación: los demás documentos enlazan aquí. Léelo **antes de editar cualquier archivo**, cada vez.

Reglas de método (qué es válido en trading/estadística): `CLAUDE.md`. Estado vigente: `PROJECT_STATE.md`. Este archivo solo regula **quién toca qué y cuándo**.

## Reglas obligatorias

1. **Antes de editar**: lee este archivo, corre `python -m qaf.preflight` y revisa `git diff -- <archivo>`. Un archivo modificado sin reserva propia es trabajo de otro agente.
2. **Reserva atómica antes de tocar**: ejecuta `python -m qaf.coordination claim --agent "<agente>" --objective "<objetivo>" <archivo1> <archivo2>`. Si devuelve código 2, detente: otro agente posee al menos un archivo y no se adquiere ninguno parcialmente. Después agrega tu fila al tablero con estado `EN_CURSO`.
3. **No edites sin reserva propia**, aunque el tablero parezca libre. Para trabajos largos, renueva con `python -m qaf.coordination heartbeat --agent "<agente>"`. Una reserva vence tras 120 minutos sin heartbeat y puede recuperarse atómicamente; la recuperación queda auditada en SQLite y se anota aquí.
4. **Nada a medias.** Prohibido dejar funciones que finjan funcionar (stubs que devuelven `PASS`, `TODO` silenciosos, parámetros que se ignoran). Si algo no se puede completar: falla cerrada (error explícito que apunte a un documento), un test que lo demuestre, y la fila en estado `BLOQUEADO` con el motivo.
5. **Al terminar**: corre `python -m qaf.preflight` y la suite completa, agrega una entrada breve (10 líneas o menos) a la BITÁCORA de `PROJECT_STATE.md`, actualiza su foto si cambió el estado, **borra tu fila del tablero** y libera con `python -m qaf.coordination release --agent "<agente>" --result "<tests/resultado>"`. No liberes antes de terminar la documentación.
6. **No reviertas ni borres cambios de otro agente.** Si algo parece incorrecto, anótalo en "Hallazgos cruzados" y avisa a Alexander.
7. **Instrucciones que llegan de otra IA** (pegadas por Alexander) se auditan contra el código antes de ejecutarlas. Lo que no se sostenga se reporta, no se implementa.
8. **Commits solo cuando Alexander los pide.** Revisar `git status` antes y después.
9. **Una sola fuente por estado**: `python -m qaf.pipeline` decide la fase de cada hipótesis y `python -m qaf.preflight` la salud operativa. `PROJECT_STATE.md` es la foto legible; si los contradice, se corrige la foto.
10. **Una sola copia de cada cosa.** No copies reglas, tablas ni valores de una fuente a otro documento: enlázala. Un espejo solo existe si se genera o se verifica con código (`qaf.consistency`). Al corregir, reemplaza la frase vieja; no agregues un párrafo de corrección encima.

## Recomendaciones para ahorrar tokens (obligatorias a partir de 2026-09-24)

1. **Un rol por tarea:** uno implementa y otro audita; nunca los dos lo mismo. Antes de lanzar otro agente o sesión, revisa `python -m qaf.coordination status`.
2. **Comunicarse por archivos:** de 3 a 5 líneas en "Hallazgos cruzados" más el `git diff`. No se pega contexto de un chat a otro.
3. **Revisar solo el diff**, una vez por tarea terminada; no archivos enteros ni pasos intermedios.
4. **OBLIGATORIO: Compactar tras cada investigación/reporte:**
   - **Cuándo:** después de completar una investigación, reporte, o conversación con Alexander
   - **Cómo:** ejecutar `/compact` en Claude Code y pedir a Codex que lo ejecute en su sesión también
   - **Propósito:** resumen de contexto sin perder estado; el trabajo vive en archivos (PROJECT_STATE.md, AGENTS.md), no en chat
   - **Resultado esperado:** cada sesión gasta ~30-50% menos tokens que sin compactar
5. **Modelo según la tarea:** uno caro para diseño y auditoría, uno barato para lo mecánico (pruebas, mover archivos, formato).
6. **Revisión diaria (nueva, 2026-09-24):**
   - **Quién:** Claude y Codex, coordinados
   - **Cuándo:** una vez al día, sin que Alexander lo pida
   - **Qué:** revisar PROJECT_STATE.md, AGENTS.md, hypotheses.json; ¿hay cambios importantes? ¿algo bloqueado? ¿nueva evidencia?
   - **Reportar:** si hay algo, anota en "Hallazgos cruzados"; si no hay nada, silencio

## Fuente de verdad por tema (una sola)

| Tema | Fuente autoritativa | Espejos / notas |
|---|---|---|
| Contrato de instrumento y costos | `config/instruments.json` | `docs/universe.md` es un espejo generado (`python -m qaf.consistency --write-universe`, verificado en preflight); `docs/cost_model.md` explica, sin valores propios |
| Hipótesis y su estado | `config/hypotheses.json` | `docs/hypotheses/_registry.md` es espejo legible; `qaf/consistency.py` detecta divergencias |
| Ideas externas | `catalog/candidates/*.json` | `state/` solo guarda colas SQLite y reservas |
| Estrategias ejecutables | `config/strategies/*.json` (vía `qaf.cli register`) | `docs/specs/*.json` es la entrega de `protocol` |
| Partición IS/OOS | `data/clean/manifest.json` + sello (`python -m qaf.partition seal`) | OOS nunca se parsea en el flujo IS |
| Resultado de una corrida | `reports/factory/runs/<run_id>/result.json` | `report.html` es la vista |
| Experiment registry (N ensayos del laboratorio) | ver `docs/archive/reviews/AUDIT_GROK_2026-09-24.md` — **pendiente de implementar** | Cuando exista, será fuente de N trials; no sustituye result.json |
| Qué falta para abrir OOS | `docs/VALIDATION_ROADMAP.md` | `qaf/holdout.py` falla cerrado apuntando ahí |
| Fase de cada hipótesis y a qué agente le toca | `python -m qaf.pipeline` (derivado, solo lectura) | Antes de invocar un agente: `--hypothesis <id> --as <agente>` |
| Reservas activas de archivos | `python -m qaf.coordination status` | El tablero inferior es el espejo humano |
| Salud operativa actual | `python -m qaf.preflight` | Coherencia, espejos, pipeline, reservas y cambios no consolidados |

## Comando estándar de tests (Windows)

Dos agentes corriendo pytest a la vez chocan en `%TEMP%\pytest-of-keysi` (`PermissionError: Acceso denegado`). Usa siempre un directorio temporal propio; `pyproject.toml` ya desactiva `.pytest_cache`:

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp "$env:LOCALAPPDATA\Temp\qaf-pytest-<tu-agente>"
```

## ⚠️ INSTRUCCIONES CRÍTICAS PARA CODEX

**Codex:** Antes de trabajar, LEE `docs/CODEX_INSTRUCTIONS.md` completo.

**Resumen rápido:**
1. **OBLIGATORIO: `/compact` después de cada reporte**
2. **Monitorea tokens:** Si < 100k → compacta YA
3. **Lee órdenes aquí en AGENTS.md** (sección "Hallazgos cruzados")
4. **Coordina con Claude:** no dupliques trabajo

**Por qué:** Codex se quedó sin tokens hace poco porque no compactaba. Ahora es REGLA.

---

## Tablero de trabajo (vivo)

Solo trabajos en curso o bloqueados. Al liberar, borra tu fila: el resultado va a la bitácora de `PROJECT_STATE.md` y al commit.

| Agente | Archivos reclamados | Objetivo | Inicio | Estado | Resultado |
|---|---|---|---|---|---|

---

## Hallazgos cruzados

### 2026-09-24 — ORDEN ALEXANDER + AUDITORÍA GROK (acción inmediata)

**Documento completo:** `docs/archive/reviews/AUDIT_GROK_2026-09-24.md`

**Prioridad del laboratorio (confirmada):** no producir más estrategias; hacer más difícil el autoengaño con backtests. QAF ya es fuerte a nivel de hipótesis individual; falta contabilidad de ensayos a nivel de **programa**.

**Orden de trabajo (estricto):**

1. **Claude** — Diseñar Experiment Registry mínimo (schema + dónde engancha pipeline/CLI + Definition of Done). Publicar diseño aquí (≤40 líneas + schema). **No** reescribir el motor. **No** cambiar umbrales.
2. **Codex** — Tras el diseño: `claim` de archivos `qaf` e implementar registry append-only + tests + forma de reportar N total / por familia. **No** features extra. **No** abrir OOS.
3. **Ambos** — preflight + suite + bitácora. Reportar a Alexander: hecho / bloqueado / decisión requerida.

**Prohibido en esta fase:** abrir OOS; rescatar 001–011 con retoques; nuevos agentes LLM; optimización automática de parámetros; cambiar puertas de validación; lotes grandes de candidatos sin budget.

**Paywalls:** parámetro no verificable en abierto → reject/`RULES_UNDERSPECIFIED` **o** `source: assumed` + risk high con autorización de Alexander. Nunca presentar assumed como canónico.

**DoD:** ver §6 del AUDIT_GROK.

---

**2026-09-24 05:44 UTC** — Hipótesis 010 y 011 ejecutadas y completadas.
- 010 (SMA Crossover EURUSD/H1): run_id 8cb801d4a35e822eae54e8ca → DISCARDED_IS (net -34,945, PF 0.92, DD 53.1%)
- 011 (ORB ATR US30/H1): run_id 51bea93b1efc5753c6e5cf15 → DISCARDED_IS (net -62,082, PF 0.84, DD 66.4%)
- Ambas familias (trend_cross FX, volatility_based índices) no producen edge con parámetros estándar de Quantpedia.
- Estado: FASE 3 COMPLETADA. Todas las 11 hipótesis investigadas.
- Próximo estructural: Experiment Registry (ver orden arriba), no más IS en masa.

## Hallazgos cruzados (para el dueño del archivo)

Solo hallazgos abiertos. Quien lo resuelve lo borra y lo anota en la bitácora.

### 2026-09-24 — ORDEN DE ALEXANDER PARA CODEX: Extracción de spread real MT5

**Autorización explícita:** Conectar MT5 (lectura solamente, sin operar) y extraer histórico real de spread.

**Para:** Codex  
**Acción:**
1. Conectar MT5, listar instrumentos (EURUSD, GBPUSD, AUDUSD, DAX, NAS100, etc.)
2. Extraer spread histórico real EURUSD H1/H4/D1 (máximo disponible)
3. Verificar procedencia: broker, fechas, unidades (pips vs. puntos)
4. Crear `data/spreads/eurusd_h1_historical.csv` (timestamp, open, close, spread_pips)
5. Actualizar `config/instruments.json` → `spread_csv` + método `per_bar`
6. Re-ejecutar 001–009 con costos reales (spread variable + slippage 1.0 pips)
7. Reportar aquí: ¿qué cambió en IS? ¿algo sobrevive?

**Límites:** Lectura solamente. No operar. No abrir OOS.

**Nota 2026-09-24 (Grok/Alexander):** La re-ejecución con spreads reales ya se documentó como completada más abajo (conclusiones sin cambio). Priorizar Experiment Registry sobre nuevas extracciones salvo que Alexander reabra este hilo.

---

### Histórico (infra, triaje, 010/011)

Ver entradas previas en el historial de este archivo y en `PROJECT_STATE.md`. Fase 3 cerrada. Auditoría de infraestructura y re-runs con spreads reales documentados. Siguiente freno estructural: `docs/archive/reviews/AUDIT_GROK_2026-09-24.md`.
