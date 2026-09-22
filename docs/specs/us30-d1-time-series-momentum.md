# US30 D1 — momentum de series temporales

**ID:** `us30-d1-time-series-momentum`

**Familia:** `trend_cross`

**Hipótesis:** #004 (`us30-d1-time-series-momentum`)

**Versión:** 1 — especificación para investigación, no aprobación de desempeño

## Traducción y limitación de la familia

La hipótesis propone momentum de series temporales del propio activo a un
horizonte de semanas o meses. El contrato actual no implementa una señal de
retorno acumulado ni una salida explícita al cruce contrario: la traducción
codeable más cercana y no equivalente semánticamente a un breakout es
`trend_cross`, con dos medias simples del cierre. Por tanto, esta spec prueba
la hipótesis como **persistencia representada por cruce SMA rápido/lento**, no
como una réplica exacta de Moskowitz, Ooi y Pedersen (2012), cuya evidencia
original es principalmente de futuros/forwards multi-activo.

`qaf.signals.generate` emite señal únicamente cuando cambia el signo de
`SMA(fast) - SMA(slow)`: `+1` al cruce alcista y `-1` al bajista. No se añade
filtro, retorno previo, ni salida por cruce contrario porque no están
soportados por el contrato actual. Mientras haya una posición abierta, el
motor ignora nuevas señales; la salida queda limitada a stop, target y tiempo.

## Activo, timeframe y entrada

- **Activo:** alias `US30`, clave `US30` en `config/instruments.json`;
  símbolo MT5 `WS30`, CFD de índice.
- **Timeframe:** `D1`, permitido por `CLAUDE.md`, `docs/universe.md` y el
  instrumento.
- **Dirección:** larga y corta, simétricas (`direction: both`).
- **Parámetros fijados:** `fast=20`, `slow=60`, `atr_period=14`,
  `sl_atr=2.0`, `tp_atr=4.0`, `max_holding=20`.

Para cada barra `t`, usando solo cierres hasta esa barra, se calculan
`SMA20[t]` y `SMA60[t]`. Se genera señal larga si
`SMA20[t] - SMA60[t] > 0` y la diferencia en `t-1` era `<= 0`; se genera
señal corta si la diferencia es `< 0` y en `t-1` era `>= 0`. Sin cruce no hay
señal. El ATR es ATR de Wilder de periodo 14 y también se calcula de forma
causal.

Una señal en la barra `t` genera una orden de mercado al **open de la barra
`t+1`**, conforme a `qaf/engine.py::simulate`; no se entra en el cierre que
produce la señal. Si faltan valores válidos de ATR o no hay barra siguiente,
el motor no abre la operación.

Los cuatro parámetros libres de investigación son `fast`, `slow`, `sl_atr` y
`tp_atr`. `atr_period=14` y `max_holding=20` son convenciones estructurales
fijadas para esta traducción, no se optimizan. No se hará barrido de
combinaciones.

## Salida, stop y sizing

Sea `P` el open de entrada y `A = ATR14[t]`, disponible al cierre de la barra
de señal:

- larga: stop inicial `P - 2.0*A`, target `P + 4.0*A`;
- corta: stop inicial `P + 2.0*A`, target `P - 4.0*A`;
- time stop: cerrar al open de la barra en la que hayan transcurrido 20
  barras desde la entrada, salvo que en ese open exista un gap que active
  primero el stop;
- no hay trailing stop ni salida manual por cruce contrario; esa limitación
  es deliberada y pertenece al contrato `trend_cross`.

En cada barra el motor procesa el open y los gaps, y después comprueba stop
antes que target si ambos niveles se tocan. Si no hay salida antes del final
de la muestra, liquida conforme al comportamiento de `simulate`.

El sizing arriesga el **0.5% de la equity** (`risk_fraction=0.005`) al stop,
incluyendo el coste round-trip estimado en el cálculo de lotes. Respeta
`volume_min`, `volume_step`, `volume_max` y el límite de margen del
instrumento. Equity inicial: `100000` unidades de cuenta. Este riesgo hereda
`config/runner.json` y no es una aprobación de rentabilidad.

## Fill, referencia de precio y costos

El modelo nominal es señal en `t` y fill al open de `t+1`. El contrato declara
`price_basis: "unknown"`; por ello no se asume mid, bid ni ask. Esa es una
reserva de Gate 0 que debe conservarse en los reportes.

El motor debe leer directamente de `config/instruments.json` para `US30`:

- `spread_points=4`;
- `commission_type="cash"`, `commission_per_side=0.35`;
- `slippage_points_per_side=1`;
- `swap_long=-7.4`, `swap_short=3.08`;
- `swap_schedule="triple"`, `triple_weekday=4` (viernes);
- `point=1.0`, `tick_size=1.0`, `tick_value=1.0`,
  `currency_to_account=1.0`, `swap_unit="account_cash_per_lot"`.

El costo total de cada operación es spread + comisión + slippage más la
financiación que corresponda al lado y a los rollovers durante la tenencia.
No se recalculan costos desde `docs/cost_model.md`, que es histórico. La
expectancy neta debe cumplir `expectancy_neta / (spread + comisión +
slippage + swap) >= 3.0`. `costs_verified=false` no bloquea la escritura:
hereda `APTO_CON_RESERVAS` de Gate 0, pero sí impide una aprobación final de
`validator`; también quedan visibles `price_basis=unknown` y las reservas de
spread/slippage del instrumento.

## Datos, baseline y puertas

La partición la fija `qaf/ingest.py` y no se redefine: `engine` usa solo
`data/clean/US30/D1/IS.parquet`; `validator` abre una sola vez
`data/clean/US30/D1/OOS.parquet` al final. La validación debe mantener el
procedimiento walk-forward dentro de esa separación física. Esta entrega no
ejecuta backtest ni abre OOS.

La puerta de baseline es superar **comprar y mantener de US30 D1**, en el
mismo slice OOS y neto de los mismos campos de `config/instruments.json`.
Nunca se usará el índice cash, otro símbolo ni un baseline genérico. El valor
numérico del baseline no se inventa aquí: debe calcularlo `validator` con el
motor real. Si resulta negativo por financiación, perder menos no basta; la
estrategia debe demostrar edge neto por encima de financiación y costos.

Puertas heredadas sin relajación de `config/runner.json`:

- mínimo 30 operaciones;
- profit factor mínimo 1.3;
- máximo drawdown fraccional 0.20;
- ratio de fricción mínimo 3.0;
- superar el baseline US30 D1 neto del mismo periodo.

Además corresponden OOS, walk-forward, sensibilidad de ±10–20% de cada
parámetro libre, al menos 200 iteraciones Monte Carlo, permutación y los
controles de calidad de datos. Estas puertas no son un veredicto de
`protocol`.

El registro contiene cinco hipótesis; esta estrategia es la **hipótesis
#004**. La aplicación a `WS30` CFD es una extrapolación de evidencia en
futuros/forwards y debe juzgarse empíricamente.
