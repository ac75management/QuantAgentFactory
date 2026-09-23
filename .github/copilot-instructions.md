# Instrucciones para GitHub Copilot / GPT en QuantAgentFactory

Antes de editar cualquier archivo, lee `AGENTS.md`: es el único protocolo de coordinación (preflight, reserva atómica, tablero y cierre) entre las IA que trabajan en paralelo sobre este working tree, sin memoria compartida. Las reglas de método están en `CLAUDE.md`, y el estado vigente en `PROJECT_STATE.md`.

Datos propios de este agente:

- Nombre en las reservas: `--agent "GPT-Copilot"` (o `"Codex"` desde la app de Codex).
- Tests con directorio temporal propio: `.venv\Scripts\python.exe -m pytest -q --basetemp "$env:LOCALAPPDATA\Temp\qaf-pytest-copilot"`.
- Sin commits salvo pedido explícito de Alexander. Nunca conectar un bróker ni abrir OOS fuera de `qaf/holdout.py`.
