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

## Recomendaciones para ahorrar tokens (no obligatorias)

1. **Un rol por tarea:** uno implementa y otro audita; nunca los dos lo mismo. Antes de lanzar otro agente o sesión, revisa `python -m qaf.coordination status`.
2. **Comunicarse por archivos:** de 3 a 5 líneas en "Hallazgos cruzados" más el `git diff`. No se pega contexto de un chat a otro.
3. **Revisar solo el diff**, una vez por tarea terminada; no archivos enteros ni pasos intermedios.
4. **Compactar al cerrar cada tarea:** primero deja el estado en `PROJECT_STATE.md` y `AGENTS.md`, luego compacta (`/compact` en Claude Code y en Codex) o abre una sesión nueva. El estado vive en los archivos, no en la conversación.
5. **Modelo según la tarea:** uno caro para diseño y auditoría, uno barato para lo mecánico (pruebas, mover archivos, formato).

## Fuente de verdad por tema (una sola)

| Tema | Fuente autoritativa | Espejos / notas |
|---|---|---|
| Contrato de instrumento y costos | `config/instruments.json` | `docs/universe.md` es un espejo generado (`python -m qaf.consistency --write-universe`, verificado en preflight); `docs/cost_model.md` explica, sin valores propios |
| Hipótesis y su estado | `config/hypotheses.json` | `docs/hypotheses/_registry.md` es espejo legible; `qaf/consistency.py` detecta divergencias |
| Ideas externas | `catalog/candidates/*.json` | `state/` solo guarda colas SQLite y reservas |
| Estrategias ejecutables | `config/strategies/*.json` (vía `qaf.cli register`) | `docs/specs/*.json` es la entrega de `protocol` |
| Partición IS/OOS | `data/clean/manifest.json` + sello (`python -m qaf.partition seal`) | OOS nunca se parsea en el flujo IS |
| Resultado de una corrida | `reports/factory/runs/<run_id>/result.json` | `report.html` es la vista |
| Qué falta para abrir OOS | `docs/VALIDATION_ROADMAP.md` | `qaf/holdout.py` falla cerrado apuntando ahí |
| Fase de cada hipótesis y a qué agente le toca | `python -m qaf.pipeline` (derivado, solo lectura) | Antes de invocar un agente: `--hypothesis <id> --as <agente>` |
| Reservas activas de archivos | `python -m qaf.coordination status` | El tablero inferior es el espejo humano |
| Salud operativa actual | `python -m qaf.preflight` | Coherencia, espejos, pipeline, reservas y cambios no consolidados |

## Comando estándar de tests (Windows)

Dos agentes corriendo pytest a la vez chocan en `%TEMP%\pytest-of-keysi` (`PermissionError: Acceso denegado`). Usa siempre un directorio temporal propio; `pyproject.toml` ya desactiva `.pytest_cache`:

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp "$env:LOCALAPPDATA\Temp\qaf-pytest-<tu-agente>"
```

## Tablero de trabajo (vivo)

Solo trabajos en curso o bloqueados. Al liberar, borra tu fila: el resultado va a la bitácora de `PROJECT_STATE.md` y al commit.

| Agente | Archivos reclamados | Objetivo | Inicio | Estado | Resultado |
|---|---|---|---|---|---|

## Hallazgos cruzados (para el dueño del archivo)

Solo hallazgos abiertos. Quien lo resuelve lo borra y lo anota en la bitácora.
