# Auditoría completa del pipeline QAF

Fecha: 2026-09-22

Alcance: `qaf/`, contratos, datos IS/OOS, costos, validación, agentes, tests y resultados generados durante esta sesión.

## Dictamen ejecutivo

El motor actual es útil como **filtro exploratorio IS**, pero todavía no es una fábrica capaz de entregar una estrategia rentable validada. Las tres estrategias ejecutadas en esta sesión fueron descartadas correctamente en IS; no hay evidencia de rentabilidad que justifique abrir OOS.

La falta de resultados no se explica únicamente por las hipótesis. También hay puertas metodológicas declaradas en `CLAUDE.md` que no están implementadas en el camino que ejecuta `qaf.cli run`.

Estado real:

- estrategias aprobadas: **0**;
- estrategias con OOS abierto: **0**;
- Gate 0: funciona como chequeo estructural, pero normalmente devuelve `RESERVE`;
- AED formal: **no implementado en `qaf`**;
- baseline buy-and-hold: **no es una puerta del runner**;
- test de permutación: **no implementado**;
- walk-forward real: **no implementado**;
- `freeze`/`validate`: bloqueados deliberadamente;
- costos: escenario actual constante, no histórico;
- tests: la ejecución completa falló por `PermissionError` del directorio temporal de pytest, no por una aserción funcional.

## Hallazgos críticos

### C1 — El runner afirma un flujo TIS completo, pero no ejecuta AED

`qaf.cli run` llama a `load_is`, `inspect_frame`, `simulate`, `diagnose` y `screening_gates`. No existe un módulo AED ni una prueba de hipótesis sobre el patrón antes del backtest.

`diagnose` solo calcula folds con parámetros fijos, estrés de costos, dos vecinos conjuntos de stop/objetivo y bootstrap de operaciones. El propio resultado marca el bootstrap como diagnóstico, no como prueba causal.

**Impacto:** una hipótesis puede llegar al backtest aunque el patrón conductual no haya sido confirmado estadísticamente. Esto viola la fase AED obligatoria y hace que el proceso pruebe reglas, no hipótesis.

**Corrección necesaria:** implementar un artefacto AED reproducible por hipótesis, con estadísticas preespecificadas, comparación contra ventanas/control apropiado y decisión `AED_CONFIRMED`/`AED_NOT_CONFIRMED`. El runner debe bloquear el backtest si no existe confirmación.

### C2 — La puerta de baseline obligatoria no existe en código

El proyecto exige superar comprar-y-mantener del mismo símbolo, timeframe, ventana y costos. `screening_gates` no recibe ni calcula baseline y no genera ninguna puerta `baseline`.

Los reportes de las estrategias ejecutadas no contienen resultado comparable de buy-and-hold. La existencia de scripts históricos de baseline no sustituye una puerta integrada y reproducible.

**Impacto:** una estrategia podría pasar todas las puertas actuales sin demostrar superioridad frente al baseline exigido.

**Corrección necesaria:** implementar un simulador baseline dentro de `qaf`, usar exactamente el mismo ledger de costos y añadir una puerta explícita. Para un baseline neto negativo, la regla debe exigir rentabilidad neta positiva y edge económico adicional; “perder menos” no debe bastar.

### C3 — No existe ruta de validación final

`qaf/holdout.py` lanza `NotImplementedError` tanto en `freeze` como en `validate_final`. Por diseño, ninguna estrategia puede abrir OOS, ejecutar permutación final, walk-forward real o producir un veredicto `APROBADA`.

**Impacto:** el repositorio no puede entregar una estrategia validada aunque alguna futura corrida supere IS.

**Corrección necesaria:** implementar un contrato congelado con hash de spec, código, costos, política, datos IS y OOS; permitir una única apertura OOS; registrar walk-forward, permutación, baseline y veredicto inmutable. Mantener el cierre actual hasta que los costos y calendario estén verificados.

### C4 — Las conclusiones económicas usan costos constantes, no costos históricos

`qaf.costs.financing` aplica la foto vigente de spreads, slippage, swaps y comisiones a todo el histórico. Los reportes lo reconocen como reserva, pero las métricas se presentan como P&L numérico.

**Impacto:** el signo o magnitud de una estrategia puede cambiar por régimen de financiación, spread o ejecución. No es válido llamarla rentable ni comparar su resultado histórico como si fuera una simulación de costos reales.

**Corrección necesaria:** conservar escenarios de costos separados de resultados históricos; incorporar series históricas o rangos conservadores documentados por símbolo y fecha, y bloquear aprobación si no existe cobertura temporal.

## Hallazgos altos

### H1 — Sensibilidad incompleta

La política exige sensibilidad de ±10–20% sobre cada parámetro libre. `diagnose` solo modifica simultáneamente `sl_atr` y `tp_atr` y no prueba por separado `lookback`, `fast`, `slow`, `max_holding`, RSI u otros parámetros libres.

**Impacto:** no demuestra estabilidad del contrato completo y puede ocultar sensibilidad extrema.

**Corrección:** generar vecinos preespecificados por parámetro individual y registrar el abanico completo, sin convertirlo en una búsqueda masiva.

### H2 — No hay test de permutación ni walk-forward real

El resultado declara:

- `permutation_test: NOT_EXECUTED`;
- `walk_forward_optimization: NOT_APPLICABLE`.

Los tres folds temporales son diagnósticos fijos, no entrenamiento en ventana 1 y prueba en ventana 2, seguido de expansión/rolling.

**Impacto:** faltan dos pruebas centrales de robustez y significación contra una explicación de azar.

**Corrección:** implementar permutación causal bajo una hipótesis nula definida y walk-forward rolling/expanding sin tocar OOS antes del momento autorizado.

### H3 — La corrección por multiplicidad es informativa, no una puerta

El bootstrap reporta `p_campaign_bonferroni_upper_bound`, pero `screening_gates` decide usando únicamente el intervalo bootstrap no ajustado. Además, el valor se basa en un bootstrap de operaciones, no en un test de permutación de la hipótesis.

**Impacto:** la campaña puede seleccionar una señal entre muchos ensayos sin que la decisión aplique la penalización declarada por pruebas múltiples.

**Corrección:** definir el universo de ensayos, incluir campañas anteriores y aplicar una regla estadística formal al veredicto.

### H4 — El time-stop sobrescribe toques intrabar

En la barra que alcanza `max_holding`, el motor reemplaza una salida `STOP`, `STOP_TIE`, `TARGET` o `TARGET_GAP_CONSERVATIVE` por salida `TIME`, excepto `STOP_GAP`.

**Impacto:** el resultado depende de una prioridad no documentada de forma suficiente y puede alterar P&L, win rate y distribución de trades.

**Corrección:** fijar una política explícita (evento intrabar primero o time-stop primero), documentarla y añadir tests para stop, target y empate en la barra límite.

### H5 — El contrato de hipótesis no se valida completamente en `register`

El runner sí comprueba que el `hypothesis_id` aparece en el registro Markdown, pero `qaf.cli register` solo valida que sea un string no vacío y que el símbolo exista. Es posible crear un JSON registrado con un identificador que no corresponda a una fila real; solo fallará cuando llegue al runner.

**Impacto:** la cola de estrategias puede contener contratos inválidos y el error aparece tarde.

**Corrección:** hacer la comprobación del registro parte de `check-spec`/`register`, con el mismo parser usado por el runner.

### H6 — Integridad de partición OOS incompleta

`load_is` comprueba que `OOS.parquet` existe y que IS coincide con `rows_is`, pero no verifica hash, filas reales OOS, timestamps OOS posteriores al corte ni que IS termine estrictamente antes del corte.

**Impacto:** una partición alterada o mal cortada puede pasar el control previo sin que el runner la lea.

**Corrección:** registrar hashes de IS/OOS y validar límites temporales, filas y esquema en la ingesta y en la carga.

## Hallazgos medios

### M1 — Gate 0 mezcla calidad de datos y contrato de ejecución

`inspect_frame` marca `price_basis`, procedencia y calendario como `RESERVE`, pero permite continuar a simulación. Esto es aceptable para exploración, pero el reporte debe separar claramente:

1. calidad estructural del OHLC;
2. validez del modelo de ejecución;
3. validez de costos históricos.

Actualmente los tres conceptos aparecen juntos como `quality=RESERVE`.

### M2 — El skill de calidad de datos y `qaf` usan fuentes distintas

El skill describe `docs/cost_model.md` y estados de confirmación propios; el runner usa `config/instruments.json` y `costs_verified`. Debe existir una única fuente contractual para no producir decisiones divergentes entre agentes y código.

### M3 — Las specs de `trend_cross` no son una implementación completa de time-series momentum

La señal solo genera entrada cuando cambia el signo de SMA rápida menos SMA lenta. La salida no ocurre explícitamente por cruce contrario; depende de stop, target o time-stop. Las specs documentan esta aproximación, pero el nombre de la hipótesis y la implementación no son equivalentes.

Esto no invalida el backtest como contrato definido, pero sí impide afirmar que se replicó directamente la literatura de time-series momentum.

### M4 — Cobertura de tests insuficiente en rutas de dinero

La suite cubre unidades, causalidad, ledger básico, gaps y protección IS/OOS, pero no tiene pruebas dedicadas para:

- `INSOLVENT_OPEN`;
- `END_OF_SAMPLE`;
- límite de margen;
- volumen mínimo que impide operar;
- rollover exactamente en el límite de intervalo;
- time-stop con toque intrabar;
- baseline;
- permutación;
- hashes de partición.

La ejecución completa actual tampoco llegó a completar por un `PermissionError` de pytest al crear `C:\Users\keysi\AppData\Local\Temp\pytest-of-keysi`; esto es un problema del entorno de tests, pero debe resolverse en CI para que una suite roja no quede sin diagnóstico.

## Lo que sí funciona

- El runner ejecuta únicamente JSON registrado.
- La carga IS no abre ni lee OOS.
- Existe una prueba que envenena OOS y verifica que el pipeline no lo toca.
- El ledger básico reconcilia balance y operaciones.
- Los fills de la barra siguiente y la prioridad conservadora de gaps están explícitos.
- Los costos se separan en spread, slippage, comisión y financiación.
- El motor no conecta ni ejecuta órdenes reales.
- Las tres estrategias recientes fueron descartadas en IS por métricas objetivamente negativas, no ocultadas como aprobadas.

## Prioridad de corrección

1. Implementar AED y bloquear backtest sin AED confirmado.
2. Implementar baseline dentro del runner.
3. Resolver costos históricos, precio de referencia y calendario por símbolo.
4. Implementar partición congelada y validación OOS de un solo uso.
5. Implementar permutación y walk-forward reales.
6. Completar sensibilidad por parámetro y corrección por multiplicidad.
7. Corregir/decidir prioridad del time-stop y añadir tests.
8. Unificar documentación de agentes, skill Gate 0 y `PROJECT_STATE.md`.
9. Resolver el entorno pytest/CI y ampliar cobertura de rutas financieras.

## Veredicto final

El sistema actual puede responder:

> “Esta especificación perdió en este escenario de costos sobre IS.”

Todavía no puede responder de forma válida:

> “Esta estrategia es rentable y robusta.”

La ausencia de estrategias rentables es, por tanto, una combinación de dos hechos:

1. las hipótesis probadas hasta ahora fallaron realmente en IS;
2. el pipeline aún carece de varias fases necesarias para descubrir y certificar una estrategia válida.

No debe abrirse OOS ni declararse ninguna estrategia rentable hasta resolver como mínimo C1, C2, C3 y C4.
