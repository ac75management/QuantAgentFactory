# US30 H1 — ruptura de canal

**ID:** `us30-h1-channel-breakout`  
**Familia:** `channel_breakout`  
**Hipótesis:** #005 (`us30-h1-channel-breakout`)  
**Versión:** 1 — especificación para investigación, no aprobación de desempeño

## Distinción de la hipótesis de momentum diario

La hipótesis #004 (`us30-d1-time-series-momentum`) es una señal de momentum
diario que debía traducirse a `trend_cross`. No se la convierte artificialmente
en esta estrategia: una ruptura de máximos/mínimos es otro estimador, otro
evento de entrada y otro horizonte. Este documento formaliza la hipótesis H1
separada registrada como #005, solicitada para estudiar continuación tras
rupturas en un índice, sin barrer varios índices.

## Activo, timeframe y alcance

- **Activo primario:** alias `US30`, clave `US30` en
  `config/instruments.json`, símbolo MT5 `WS30`, CFD de índice.
- **Timeframe:** H1. `CLAUDE.md` permite H1, H4 y diario; además US30 declara
  `H1` en su lista `timeframes`.
- **Dirección:** larga y corta, simétricas.
- **Alternativas posteriores:** `NAS100` y `SP500` quedan explícitamente fuera
  de esta corrida; solo se estudiarían como hipótesis/corridas separadas.

La intuición procede de continuación tras una salida del rango, no de una
réplica de un resultado publicado. La evidencia de la hipótesis #004 en
futuros/forwards diarios no se trata como validación de esta versión H1 sobre
un CFD.

## Entrada numérica

Para cada barra H1 `t`, usando únicamente datos disponibles al cierre:

1. `upper[t] = max(high[t-24], ..., high[t-1])`.
2. `lower[t] = min(low[t-24], ..., low[t-1])`.
3. Emitir señal larga (`+1`) si `close[t] > upper[t]`.
4. Emitir señal corta (`-1`) si `close[t] < lower[t]`.
5. Si ninguna desigualdad se cumple, no emitir señal. Si ambas fueran
   imposibles por la definición de máximo/mínimo, no se abre nada.

El motor no entra en la misma barra de señal: una señal calculada en `t`
genera una orden de mercado al **open de `t+1`**, que es el modelo de
`qaf/engine.py::simulate`. No se permite look-ahead. Mientras haya una
posición abierta se ignoran nuevas señales.

El ATR causal usado para la gestión es ATR de Wilder de periodo 14, calculado
al cierre de `t`; se conserva el valor `ATR[t]` para la entrada en `t+1`.

## Salida y gestión de riesgo

Para una entrada en el precio de apertura `P` de `t+1`, con `A = ATR(14)[t]`:

- **Larga:** stop inicial `P - 1.5*A`; objetivo `P + 3.0*A`.
- **Corta:** stop inicial `P + 1.5*A`; objetivo `P - 3.0*A`.
- **Time stop:** cerrar al open de la barra en la que hayan transcurrido
  24 barras desde la entrada, salvo que en ese open exista un gap que active
  primero el stop. No hay trailing stop.
- En una misma barra, `qaf/engine.py` procesa primero el open (incluidos
  gaps), después stop antes que target si ambos niveles se tocan; esto evita
  inventar el orden intrabar.
- Si no ocurre stop, target ni time stop antes del final de la muestra, el
  motor liquida al cierre final conforme a su comportamiento de simulación.

El sizing arriesga el **1% de la equity** por operación al stop, ajustando el
volumen a `volume_min`, `volume_step` y `volume_max` del instrumento y al
límite de margen del motor. La estimación de lotes incluye el coste
round-trip; la estrategia no puede superar el límite de volumen o margen para
forzar el riesgo. Equity inicial de especificación: `100000` unidades de la
cuenta. Los parámetros libres de la hipótesis son cuatro: `lookback=24`,
`sl_atr=1.5`, `tp_atr=3.0` y `max_holding=24`; `atr_period=14` es el periodo
estructural de medición de volatilidad.

## Fill, precio de referencia y costes

El precio de referencia declarado por el contrato actual de
`config/instruments.json` es `price_basis: "unknown"`. Por ello esta spec no
asume mid, bid ni ask: queda como reserva de Gate 0 y debe conservarse
explícitamente en los reportes. El fill nominal es el open de la siguiente
barra, con la convención de costes del motor.

Para `US30`, el motor debe leer directamente estos campos de
`config/instruments.json` (no recalcularlos desde `docs/cost_model.md`, que es
histórico):

- `spread_points: 4`;
- `commission_type: "cash"` y `commission_per_side: 0.35`;
- `slippage_points_per_side: 1`;
- `swap_long: -7.4` y `swap_short: 3.08`;
- `swap_schedule: "triple"` y `triple_weekday: 4` (viernes);
- `swap_unit: "account_cash_per_lot"`, `point: 1.0`, `tick_size: 1.0`,
  `tick_value: 1.0`, `currency_to_account: 1.0`.

El coste total relevante es spread + comisión + slippage + swap/financiación
que corresponda al lado y al tiempo de permanencia. La expectancy neta debe
tener `expectancy_neta / (spread + comisión + slippage + swap) >= 3.0`.
La propiedad `costs_verified: false` no bloquea esta spec: hereda la reserva
de Gate 0 (`APTO_CON_RESERVAS`). Sí impide una aprobación final de
`validator`; el análisis debe mostrar el escenario de costes y conservar la
reserva de precio desconocido, spread y slippage.

## Datos, baseline y partición

La división IS/OOS no se redefine aquí. Debe usarse el corte inmutable creado
por `qaf/ingest.py` en
`data/clean/US30/H1/{IS,OOS}.parquet`: `engine` trabaja solo con IS y
`validator` abre OOS al final, dentro del procedimiento walk-forward. No se
ejecuta backtest ni se abre OOS como parte de esta entrega.

La puerta de baseline es superar **comprar y mantener de US30 H1**, con el
mismo slice OOS y exactamente los costes de `config/instruments.json`. No se
usará el índice cash, otro símbolo ni un baseline genérico. El valor de ese
baseline H1 no se inventa en la spec y debe calcularlo `validator` con el
motor real. La comparación debe considerar que la financiación puede hacer
negativo el buy-and-hold de varios años: perder menos que un baseline negativo
no basta; la estrategia debe justificar edge neto por encima de financiación y
costes.

## Puertas numéricas

Se heredan sin relajar los defaults de `config/runner.json`:

- mínimo **30 trades**;
- profit factor mínimo **1.3**;
- máximo drawdown fraccional **0.20**;
- ratio de fricción mínimo **3.0**;
- además, superar el baseline US30 H1 neto del mismo periodo y símbolo.

Las puertas no constituyen un veredicto. `validator` debe aplicar también
OOS, walk-forward, sensibilidad de ±10–20% de cada parámetro libre, al menos
200 iteraciones Monte Carlo, permutación y controles de calidad. El registro
contiene cinco hipótesis en total; esta estrategia es la **hipótesis #005**,
dato que debe considerar al interpretar evidencia y multiplicidad.

## Bloqueos y reservas declaradas

No hay bloqueo duro de datos para escribir el contrato: `US30` existe, tiene
`status: "research"` y declara H1. La spec queda condicionada a Gate 0 por
`price_basis: "unknown"`, `costs_verified: false` y las reservas de spread,
slippage, calendario/proveniencia y conversiones del instrumento. No se ha
solicitado evidencia externa adicional para fijar una regla: la entrada es
la definición numérica ya ejecutable de `channel_breakout`; cualquier variante
de canal o proxy distinto requeriría otra hipótesis registrada.
