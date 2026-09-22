# QuantAgentFactory — Resumen para revisión externa

Documento autocontenido para pasar a otra IA/revisor sin más contexto. No es un resultado — es el diseño del proceso, todavía sin ninguna hipótesis corrida.

## Qué es
Sistema de agentes (Claude Code) para investigar, validar y aprobar estrategias de trading cuantitativo, siguiendo el método TIS (hipótesis → dato limpio → reglas → backtest → robustez → veredicto). Proyecto nuevo, independiente de otros sistemas de trading del usuario. Nivel de madurez: sistema agéntico — 4 agentes especializados gobernados por reglas duras en CLAUDE.md.

## Alcance
- Mercados: CFDs (índices, forex, materias primas) + futuros.
- Frecuencia: diario o 4H, nunca menos.
- Excluido explícitamente: scalping, alta frecuencia, rebalanceo de cartera.
- Por qué: a esa frecuencia, el costo de bróker (spread/comisión/slippage) queda como margen operativo menor, no como causa de pérdida de la cuenta.

## Filosofía
La IA es "obrero, no pensador": ejecuta código determinista (Python) dentro de límites estrictos; no se le pide que invente una estrategia rentable de la nada. Toda regla debe ser codificable — "si no se puede escribir en código, no existe".

## Proceso (gate de datos + 8 fases del método TIS)
0. **Gate de calidad de datos** (añadido en esta versión) — antes de tocar nada estadísticamente.
1. Hipótesis con lógica de comportamiento.
2. AED — confirmar que el patrón existe en los datos antes de programar reglas.
3. Definición de reglas numéricas (entrada, salida, riesgo).
4. Backtest In-Sample.
5. Optimización delimitada — sin minería de fuerza bruta.
6. Backtest Out-of-Sample (30% nunca tocado antes de este paso).
7. Pruebas de robustez: Montecarlo, permutación, walk-forward.
8. Sizing y veredicto final. Deploy en vivo/VPS queda fuera de este repo — requiere confirmación explícita del usuario cada vez, nunca automática.

## Los 4 agentes y cómo se conectan
Se comunican solo por archivo — nunca por un mensaje de chat que se pierde al cerrar la sesión:

| Agente | Lee | Escribe |
|---|---|---|
| investigator | literatura externa (busca por su cuenta, no limitado a autores de ejemplo) | docs/hypotheses/\<slug\>.md |
| protocol | la hipótesis | docs/specs/\<slug\>.md — reglas numéricas, puertas, chequeo de que el activo/timeframe esté dentro del alcance |
| engine | la spec + datos | Gate 0 de calidad, AED y backtest → reports/\<slug\>/ |
| validator | los resultados de engine | veredicto (aprobada/rechazada) → reports/\<slug\>/verdict.md; si aprueba, código final en strategies/\<slug\>/ |

Si algo falla en cualquier punto (datos sucios, patrón no confirmado, puerta numérica no superada), el proceso vuelve a investigator con la razón documentada — nunca se descarta en silencio ni se fuerza el avance.

## Reglas duras (gobernanza)
- Nunca ejecución en vivo ni conexión a bróker sin confirmación explícita del usuario, cada vez.
- Nunca deploy en VPS sin esa misma confirmación.
- 70/30 In-Sample/Out-of-Sample fijo; el OOS nunca se toca para optimizar.
- Prohibida la minería de fuerza bruta de parámetros sin una hipótesis previa que la respalde.
- Todo el código de simulación en Python 3; ninguna librería de ejecución de órdenes reales en el repo.
- Cada fase deja un archivo — nunca solo un mensaje de chat.

## Puertas numéricas — estado actual
| Puerta | Valor | Estado |
|---|---|---|
| Profit factor OOS | > 1.3 | Placeholder, sin confirmar |
| p-valor test de permutación | < 0.05 | Placeholder, sin confirmar |
| Máximo drawdown OOS | por estrategia | Sin default global |
| Ratio expectancy / costo de bróker | sin definir | **Bloqueante** |
| Límite de parámetros libres | sin definir | Pendiente |
| Split In-Sample/Out-of-Sample | 70/30 | Confirmado |

## Lo que ya existe (construido)
- CLAUDE.md con reglas duras + alcance de mercado/frecuencia
- 4 subagentes reales, invocables ya (.claude/agents/investigator, protocol, engine, validator)
- Skill de calidad de datos con checklist concreto (.claude/skills/data-quality-check/)
- docs/philosophy.md — método TIS y glosario
- docs/architecture.md — mismo mapa con diagrama de flujo
- Repo git local inicializado (sin commit todavía)

## Lo que falta / sigue abierto
- Fuente de datos históricos y bróker de referencia — sin decidir, bloquea correr cualquier hipótesis real de punta a punta.
- Número exacto del ratio expectancy/costo de bróker.
- Tope de parámetros libres por estrategia, o evaluación caso por caso.
- Skills de AED y backtest todavía no son código — solo el proceso está descrito.
- Ninguna hipótesis se ha procesado todavía.
- ¿GitHub remoto ahora o más adelante?

## Preguntas para quien revise esto
1. ¿El orden de las 8 fases + el gate de datos tiene sentido, o falta un paso?
2. ¿Las reglas duras alcanzan para evitar sobreajuste y ejecución accidental en vivo, o falta alguna?
3. ¿Falta algún tipo de prueba de robustez o de chequeo de calidad de datos que sea estándar en la industria?
4. ¿La división de responsabilidades entre los 4 agentes es clara, o se solapa en algún punto?
5. ¿El alcance (CFD + futuros, diario/4H, sin scalping/HFT/rebalanceo) es razonable para el objetivo, o es demasiado restrictivo/laxo?
