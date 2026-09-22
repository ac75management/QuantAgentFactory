# Instrucciones para GitHub Copilot / GPT en QuantAgentFactory

Antes de editar cualquier archivo, lee `AGENTS.md` en la raíz: otras IA (Claude Code) trabajan en paralelo sobre este mismo working tree, sin memoria compartida.

Resumen obligatorio (el detalle está en `AGENTS.md`):

1. Corre `.venv\Scripts\python.exe -m qaf.preflight` y lee `AGENTS.md`.
2. Antes de editar, adquiere todos los archivos con `.venv\Scripts\python.exe -m qaf.coordination claim --agent "GPT-Copilot" --objective "..." <archivos>`. Código 2 significa detenerse; no hagas una reclamación parcial. Refleja después la reserva en el tablero.
3. Nada a medias: si algo no se puede completar, falla cerrado con un error explícito y un test, nunca con un stub que finja funcionar.
4. No reviertas ni borres cambios de otro agente; anota el problema en "Hallazgos cruzados".
5. Reglas de método (IS/OOS, costos, puertas, alcance H1/H4/D1): `CLAUDE.md`. Estado del proyecto: `PROJECT_STATE.md`.
6. Tests en Windows con directorio temporal propio: `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\qaf-pytest-copilot"`.
7. Al terminar: preflight, suite completa, bitácora/tablero y `.venv\Scripts\python.exe -m qaf.coordination release --agent "GPT-Copilot" --result "..."`.
8. Sin commits salvo pedido explícito de Alexander. Nunca conectar un bróker ni abrir OOS fuera de `qaf/holdout.py`.
