# Intraday Reversal Currency Markets Alpha

Estado: **pendiente de protocolo**. Esta ficha registra una hipótesis investigable; no afirma rentabilidad y no contiene resultados de backtest.

## Trazabilidad

- Hipótesis: `009`
- Candidato: `IDEA-SRC-051A7EA057B3`
- Fuente primaria: [IntradayReversalCurrencyMarketsAlpha.py — QuantConnect LEAN, Algorithm.Python/Alphas, implementando la estrategia de LeBaron & Zhao, 'Foreign Exchange Reversals in New York Time' (también circulada como 'Intraday Foreign Exchange Reversals')](https://github.com/QuantConnect/Lean/blob/88bce0fc6fe282378ee73c54cef1090d0d7a73ee/Algorithm.Python/Alphas/IntradayReversalCurrencyMarketsAlpha.py)
- Autores: QuantConnect Corporation (implementación), Blake LeBaron, Yan Zhao (paper académico citado en el código fuente)
- Mercado y vehículo originales: FX interbancario/institucional, par EUR/USD, sesión de Nueva York (10:00-15:00 hora NY) / Forex spot/interbancario (implementación LEAN usa Symbol.create EURUSD, SecurityType.FOREX, Market.OANDA)
- Objetivo QAF: EURUSD / H1
- Tratamiento: adaptation
- Regla fuente: `lean-intraday-fx-reversal-sma-band-ny-session`
- Dimensiones adaptadas: costs, vehicle

## Evidencia revisada

Código completo leído línea por línea (commit fijado 88bce0fc6f). `resolution = Resolution.HOUR`. Universo: un solo símbolo, EURUSD (OANDA FOREX). SMA de 5 períodos (`period_sma=5`) calculada a resolución horaria. Regla: `is_uptrend(price) = price < round(sma*1.001, 6)`; en `update()`: `direction = UP if is_uptrend else DOWN`. Es decir, precio por debajo de SMA(5)+0.1% -> dirección UP (largo, apostando a reversión al alza); precio por encima de ese umbral -> DOWN (corto, apostando a reversión a la baja). Solo emite un insight nuevo cuando la dirección cambia respecto de la anterior (`if direction == previous_direction: continue`). Filtro de sesión: solo evalúa señales entre las 10:00 y las 15:00 hora de Nueva York (`time_of_day >= time(10) and time_of_day <= time(15)`); el insight expira a las 15:01 NY (`time_to_close`). El comentario del archivo cita explícitamente el paper de LeBaron & Zhao y su hipótesis: el patrón de reversión en esa franja horaria se debe a cobertura institucional de operaciones vinculadas al dólar durante el horario de mercado de EEUU. Búsqueda independiente (WebSearch) confirma que el paper existe y es real: 'Foreign Exchange Reversals in New York Time', Blake LeBaron y Yan Zhao, con copias en CiteSeerX, la página de Brandeis (people.brandeis.edu/~heidifox/fx.pdf) y ResearchGate. Según los resúmenes disponibles, el estudio usa datos horarios de la plataforma EBS, diciembre 2003 - marzo 2006, documenta una estrategia de reversión de un parámetro (m, en horas, típicamente 4-12h) y efectos de hora del día ligados a cuál mercado del par está abierto.

## Mecanismo propuesto

Hipótesis (según LeBaron & Zhao, sin verificar el texto completo del paper más allá de los resúmenes disponibles): durante la sesión de Nueva York, flujos de cobertura institucional en USD (corporaciones/instituciones ajustando exposición en dólares durante el horario de mercado de EEUU) generan presión de precio direccional de corto plazo que se revierte una vez que ese flujo se agota, produciendo el patrón de reversión horaria alrededor de una media móvil corta. El otro lado del trade serían esos mismos flujos institucionales de cobertura (no discrecionales, ligados a necesidades operativas, no a una visión de mercado) y traders de momentum de muy corto plazo que persiguen el movimiento inicial antes de la reversión.

## Reglas publicadas que deben conservarse

- Universo: EURUSD únicamente (Market.OANDA, FOREX).
- SMA de 5 períodos calculada a resolución horaria (Resolution.HOUR).
- Señal: precio < SMA(5) * 1.001 -> dirección UP (largo); en caso contrario -> DOWN (corto).
- Solo se emite una nueva señal cuando la dirección calculada difiere de la señal previa (evita repetir la misma dirección barra a barra).
- Filtro de sesión: solo se evalúan/emiten señales entre las 10:00 y las 15:00 hora de Nueva York.
- Cierre forzado de la posición a las 15:01 hora de Nueva York (expiración del insight).

## Réplica o adaptación

Se conserva EURUSD/H1 y la sesión original, pero se adapta de spot institucional/OANDA a CFD retail con costos, rollover y ejecución propios del contrato del proyecto.

## Ambigüedades todavía abiertas

- El código no publica un stop-loss ni una salida por precio: la única salida explícita es temporal (15:01 NY) o un cambio de dirección de la señal; no hay evidencia de gestión de riesgo por stop en la fuente.
- El comentario del código no da número de página ni cita textual del paper (solo enlaces), y el acceso completo al texto de LeBaron & Zhao no fue verificado línea por línea, solo su existencia y resumen vía búsqueda independiente.
- El período exacto de datos de LeBaron & Zhao (dic. 2003 - mar. 2006, EBS interbancario) es anterior y de un vehículo distinto (interbancario) al CFD Darwinex/MT5 que usaría este proyecto; la ventana horaria 10:00-15:00 NY y el mecanismo de flujos de cobertura institucional podrían haberse diluido o desplazado en la estructura de mercado FX actual (post-2006), lo cual no está verificado aquí.

## Datos requeridos

- OHLC horario de EURUSD con marca de tiempo en zona horaria de Nueva York verificable (para aplicar el filtro de sesión 10:00-15:00 NY).

## Costos y fricciones que el contrato debe modelar

- Spread/comisión/swap del CFD EURUSD en Darwinex/MT5, ausentes en el ejemplo LEAN original (usa ConstantFeeModel(0)).

## Límites de la evidencia

- La familia de señal necesaria (precio vs. SMA corta + banda porcentual, con filtro de sesión horaria) no existe en `qaf/contracts.py` (`FAMILIES = {streak_reversal, trend_cross, channel_breakout, oscillator_reversion}`); ninguna de las 4 familias implementadas expresa 'precio cruza SMA(n) ± banda %' con ventana horaria de sesión. Requeriría una familia nueva en `qaf/signals.py` (protocol/engine deben evaluarlo) antes de poder traducirse a spec ejecutable.
- Extrapolación de vehículo: el paper original es FX interbancario/institucional 2003-2006; adaptarlo a CFD retail vía Darwinex/MT5 dos décadas después es una extrapolación de riesgo, no una aplicación directa, y debe declararse así explícitamente en la hipótesis si/cuando se promueva.

## Decisión de la revisión

La implementación fijada y la evidencia académica identifican una regla horaria reproducible para EURUSD; su rentabilidad no se presume y debe probarse con costos y datos del proyecto.

Siguiente paso: `protocol` debe convertir esta hipótesis en reglas numéricas congeladas o bloquearla si las ambigüedades impiden una implementación fiel. OOS permanece cerrado.
