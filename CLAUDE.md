# QuantAgentFactory — CLAUDE.md

## Propósito
Repositorio de investigación cuantitativa asistida por agentes. Objetivo: convertir una hipótesis de trading en una estrategia validada, siguiendo el método TIS (hipótesis → AED → reglas → backtest → optimización → robustez → sizing → deploy), documentado en [docs/philosophy.md](docs/philosophy.md).

Proyecto independiente de ZOO2. No comparte cuenta, capital ni conexión de bróker con ningún otro proyecto.

## Coordinación con otros agentes (obligatorio antes de editar)
Otras IA editan este mismo working tree en paralelo. El protocolo completo (preflight, reserva atómica, tablero, cierre) está en [AGENTS.md](AGENTS.md), importado aquí:

@AGENTS.md

## Alcance de mercado y frecuencia
- Mercados: CFDs (índices, forex, materias primas) y futuros, como foco principal. Ampliable a otros mercados más adelante, uno a la vez, no por defecto.
- Frecuencia: H1, H4 o diario como mínimo. Nunca por debajo de H1.
- Excluido explícitamente: M30/M15, alta frecuencia / scalping, estrategias de rebalanceo de cartera.
- Motivo: a esta frecuencia, spread/comisión/slippage del bróker quedan como margen operativo menor, no como la causa de pérdida de la cuenta (ver regla dura 11).
- Los autores citados en docs/philosophy.md (Kaufman, Raschke) son ejemplos ilustrativos de la fuente original del método, no el catálogo de dónde sacar hipótesis. `investigator` busca su propia literatura/patrones dentro de este alcance.

## Reglas duras (ningún agente las viola)
1. Nunca ejecutar operaciones reales ni conectar con una cuenta de bróker (demo o real) sin confirmación explícita y fresca de Alexander en el chat, sesión por sesión.
2. Nunca desplegar en VPS ni activar ejecución automatizada 24/7 sin esa misma confirmación explícita.
3. Toda estrategia pasa por las 8 fases del método TIS en orden. Ninguna estrategia queda "aprobada" sin pasar por robustez (Montecarlo + Out-of-Sample + permutación).
4. División de datos por defecto: 70% In-Sample / 30% Out-of-Sample. El OOS no se toca para optimizar parámetros, solo para validar al final.
5. Puertas numéricas mínimas: profit factor > 1.3 y p-valor de permutación < 0.05. Los umbrales vigentes del filtro IS viven en `config/runner.json` y los aplica `qaf/validation.py::screening_gates`. El drawdown máximo OOS se fija por estrategia en su spec.
6. Todo código de simulación/backtest en Python 3. Ninguna librería de ejecución de órdenes reales en este repo.
7. Cada fase deja un archivo (reporte, JSON o script) en la carpeta correspondiente — nunca solo un mensaje de chat que se pierde al cerrar la sesión.
8. Idioma: documentación y reportes en español. Nombres de variables/funciones en código, en inglés (convención estándar).
9. **Gate 0 — Calidad de datos**: ningún dataset entra a AED (fase 2 del método TIS) sin pasar el chequeo de `.claude/skills/data-quality-check/SKILL.md`. Datos sucios (huecos, duplicados, outliers no explicados, splits/dividendos o rollover de futuros sin ajustar) se documentan y el dataset se limpia o se descarta — nunca se ignora en silencio.
10. **Anti-minería de fuerza bruta**: prohibido correr búsquedas automatizadas masivas de combinaciones de parámetros sin una hipótesis de `investigator` que las respalde. Toda optimización se justifica por lógica de comportamiento, no solo por mejorar la curva de equidad.
11. **Costo de bróker como margen, no como causa de pérdida**: la expectativa neta (después de spread + comisión + slippage estimado) debe superar ese costo de fricción por un margen mínimo — fijado en la regla 17 (ratio ≥3.0). Ninguna estrategia queda "aprobada" solo por profit factor bruto, sin pasar este ratio.
12. **Alcance de mercado y frecuencia**: ver sección "Alcance" arriba. Cualquier hipótesis fuera de ese alcance se rechaza en `protocol`, antes de llegar a `engine`.
13. **Separación física de datos IS/OOS**: en la extracción, los datos se cortan 70/30 en archivos separados (`data/<símbolo>/IS.*` y `data/<símbolo>/OOS.*`). `engine` solo lee el archivo IS durante el desarrollo; el archivo OOS solo lo abre `validator`, una vez, al final.
14. **Análisis de sensibilidad de parámetros obligatorio**: ±10-20% sobre cada parámetro libre, mínimo 200 iteraciones tipo Montecarlo. La curva original debe quedar en el centro del abanico de curvas resultante, no ser la más ganadora.
15. **Fase de incubación obligatoria** antes de cualquier disponibilidad para live: 30-60 días en cuenta demo, seguidos de un tramo en cuenta real a lotaje mínimo (ej. 0.01) para medir fricción real que la demo esconde — cada paso requiere confirmación explícita de Alexander.
16. **Tope de parámetros libres optimizables**: 3-4 por estrategia. Distinto de "componentes estructurales" (señal de entrada, filtro, SL, TP, salida por tiempo) — ahí la zona más sana documentada es 4-8 componentes; menos de 2 o más de 12 componentes se trata con sospecha.
17. **Ratio de fricción mínimo**: expectancy neta / (spread+comisión+slippage+swap) ≥ 3.0, usando el contrato de `config/instruments.json` (fuente única de costos; `docs/cost_model.md` es documentación humana y no puede contradecirlo).
18. **Metodología de validación real**: walk-forward (rolling: entrenar en periodo 1, probar en periodo 2; entrenar en 1+2, probar en 3; y así sucesivamente) es el estándar, no un split estático de una sola vez. El split 70/30 fija el corte IS/OOS general; dentro de eso, la validación real avanza en ventanas.
19. **Puerta de baseline obligatoria**: ninguna estrategia se aprueba si no supera un "comprar y mantener" del mismo activo, con los mismos costos y el mismo capital (invertido 1x, `qaf/baseline.py`), en la misma ventana — IS como filtro, OOS en la validación final. Si el baseline es negativo, la estrategia además debe ser positiva.
20. **Tercer estado de veredicto**: `INVALID_POR_DATOS` (dato insuficiente o de mala calidad) es distinto de `RECHAZADA` (no cumple puertas de desempeño). `validator` lo usa cuando Gate 0 da `FAIL` (`quality.status` en `result.json`), o cuando las reservas de datos (`RESERVE`) bloquean el veredicto final y Alexander no las confirmó para esa estrategia.
21. **Modelo de fill explícito**: toda spec fija cómo se ejecuta la orden (por defecto: al open de la siguiente barra tras la señal) y qué precio de referencia usa (bid/ask/mid, según lo que declare Gate 0) — nunca se asume sin documentar.
22. **Registro de hipótesis obligatorio**: `investigator` consulta y actualiza la fuente estructurada `config/hypotheses.json`; `docs/hypotheses/_registry.md` se mantiene como espejo legible y `python -m qaf.consistency` debe quedar sin errores. Esto permite contar todas las ideas probadas contra el sobreajuste por múltiples pruebas.

## Agentes disponibles (.claude/agents/)
- **investigator** — investiga ineficiencias documentadas y redacta hipótesis con lógica de comportamiento.
- **protocol** — aplica el método TIS: traduce hipótesis en reglas numéricas y puertas de aprobación.
- **engine** — limpia datos, corre AED y backtest en Python.
- **validator** — pruebas de robustez, veredicto final, genera el código de despliegue si aprueba.

Invocar con la herramienta Agent y el `subagent_type` correspondiente. No dupliques su trabajo en el hilo principal — si un agente ya está haciendo la tarea, no la repitas en paralelo.

**Orden de fases determinista**: el chat no decide a qué agente le toca. Antes de invocar cualquiera de los 4 sobre una hipótesis, correr `.venv/Scripts/python.exe -m qaf.pipeline --hypothesis <id> --as <agente>` e invocarlo solo si responde `PERMITIDO` (código 0). `python -m qaf.pipeline` sin argumentos muestra la fase de todas las hipótesis y las violaciones (artefactos contradictorios o fases saltadas). `READY_FOR_FROZEN_VALIDATION` significa "lista para entrar en validación congelada", nunca "estrategia validada". No se agregan agentes de optimización, sizing o deploy hasta que existan walk-forward real y la apertura OOS.

**Optimización**: no existe un agente optimizador ni una búsqueda automática de ganadores. `protocol` congela como máximo 3-4 parámetros justificables antes del backtest. `engine` puede medir sensibilidad alrededor de esa spec usando exclusivamente la política versionada de `config/runner.json`, pero ningún vecino reemplaza la spec. Un cambio posterior de regla, familia o parámetros constituye una hipótesis nueva y cuenta como otra prueba de campaña. OOS nunca retroalimenta IS.

## Estructura
- [docs/architecture.md](docs/architecture.md) — mapa del pipeline tal como corre hoy (grafo, puertas, agentes)
- [AGENTS.md](AGENTS.md) — coordinación entre agentes y tablero de reservas
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — proceso permitido de investigación y optimización
- [config/instruments.json](config/instruments.json) — contrato de instrumento y costos (fuente única); [docs/universe.md](docs/universe.md) es su espejo generado y [docs/cost_model.md](docs/cost_model.md) explica cómo se aplican los costos
- [config/hypotheses.json](config/hypotheses.json) — registro autoritativo de hipótesis; [docs/hypotheses/_registry.md](docs/hypotheses/_registry.md) es su espejo (`python -m qaf.consistency` detecta divergencias)
- [docs/VALIDATION_ROADMAP.md](docs/VALIDATION_ROADMAP.md) — qué falta para abrir OOS (hoy cerrado)
- [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) — extracción MT5 e importación IS/OOS
- `docs/hypotheses/`, `docs/specs/`, `docs/sources/` — hipótesis, contratos de protocol y evidencia de fuentes
- `docs/proposals/` — ideas aparcadas con diseño, sin aprobar; `docs/archive/` — informes, auditorías y specs históricos (no describen el estado vigente)
- `catalog/` — catálogo versionado de ideas externas (`candidates/`, `discoveries/`)
- `data/` y `reports/` — datos y resultados locales, no versionados (ver `.gitignore`)
- `strategies/` — código final validado (vacío: ninguna estrategia aprobada)
- `.claude/skills/data-quality-check` — checklist humano de Gate 0. AED, baseline, costos y puertas son código probado en `qaf/`, no skills.

## Estado del proyecto
[PROJECT_STATE.md](PROJECT_STATE.md): foto del estado vigente arriba y bitácora corta abajo. Léelo antes de asumir nada y actualízalo tras cada avance real. La fase de cada hipótesis la decide `python -m qaf.pipeline`, no la bitácora.
