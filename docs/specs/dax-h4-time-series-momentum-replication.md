# DAX H4 — replicación de momentum de series temporales

**ID:** `dax-h4-time-series-momentum-replication`

**Familia:** `trend_cross`

**Hipótesis:** #006 (`dax-h4-time-series-momentum-replication`)

**Versión:** 1 — especificación para investigación, no aprobación de desempeño

## Admisibilidad y traducción

La hipótesis #006 es una replicación preespecificada en otro símbolo y
timeframe de #004: DAX (`GDAXI`) H4 frente a US30 (`WS30`) D1. No cambia la
familia ni rescata un resultado de #004, y pregunta explícitamente si el
mecanismo se transporta a otro índice y frecuencia. Por esa diferencia de
activo, región y frecuencia, se considera **semánticamente admisible** y no
una duplicación de la misma prueba. El registro de hipótesis contiene esta
idea como #006.

La literatura citada estudia principalmente futuros y forwards. Esta spec no
presenta el CFD como una réplica exacta de esos resultados: prueba una
representación ejecutable de persistencia mediante un cruce de medias del
propio DAX. El contrato actual no implementa una señal de retorno acumulado
ni permite añadir filtros macro, calendario, COT u order flow.

## Activo, alcance y parámetros

- **Activo:** alias `DAX`, clave `DAX` en `config/instruments.json`; símbolo
  MT5 `GDAXI`, CFD de índice.
- **Timeframe:** `H4`, permitido por `CLAUDE.md`, `docs/universe.md` y el
  instrumento.
- **Dirección:** ambas, larga y corta (`direction: both`).
- **Equity inicial:** 100000 unidades de cuenta.
- **Riesgo:** 0.5% de la equity por operación (`risk_fraction: 0.005`).
- **Parámetros del contrato:** `fast=20`, `slow=60`, `atr_period=14`,
  `sl_atr=2.0`, `tp_atr=4.0`, `max_holding=20`.

Los cuatro parámetros libres de investigación son `fast`, `slow`, `sl_atr` y
`tp_atr`. `atr_period=14` y `max_holding=20` quedan fijados como
componentes estructurales de esta traducción y no se optimizan. No se
autoriza un barrido de combinaciones ni la incorporación de parámetros no
presentes en el contrato JSON.

## Regla de entrada y modelo de señal

Para cada barra `t`, usando únicamente cierres disponibles hasta `t`, se
calculan:

- `SMA_fast[t] = media(close[t-19:t])`;
- `SMA_slow[t] = media(close[t-59:t])`.

Se genera señal larga (`+1`) cuando
`SMA_fast[t] - SMA_slow[t] > 0` y la diferencia en `t-1` es menor o igual a
cero. Se genera señal corta (`-1`) cuando
`SMA_fast[t] - SMA_slow[t] < 0` y la diferencia en `t-1` es mayor o igual a
cero. Sin cambio de signo no hay señal. La señal solo puede usar datos
causales; no se usa el cierre de una barra futura.

Una señal observada al cierre de la barra `t` se ejecuta como orden de
mercado al **open de la barra `t+1`**, conforme a
`qaf/engine.py::simulate`. No se entra en el cierre que produce el cruce.
Si no hay ATR válido en `t` o no existe `t+1`, se omite la entrada. Mientras
hay una posición abierta, el motor no abre otra.

## Regla de salida

Sea `P` el open de entrada y `A = ATR14[t]`, calculado causalmente al cierre
de la barra de señal:

- larga: stop inicial `P - 2.0*A` y take profit `P + 4.0*A`;
- corta: stop inicial `P + 2.0*A` y take profit `P - 4.0*A`;
- time stop: cerrar al open de la barra en que hayan transcurrido 20 barras
  desde la entrada, salvo que ese open active primero un stop por gap;
- no hay trailing stop ni salida manual por cruce contrario: el cruce
  contrario solo puede generar una señal futura después de que la posición
  haya quedado cerrada.

En cada barra, el motor procesa primero el open y los gaps. Si dentro de la
barra se tocan ambos niveles, el stop tiene prioridad (`STOP_TIE`); si solo
se toca uno, se ejecuta ese nivel. El time stop se aplica al open según la
lógica de `simulate`. Una posición que siga abierta al final de la muestra
se liquida según el comportamiento del motor, no mediante una regla
alternativa de esta spec.

El sizing calcula lotes para que la pérdida al stop sea aproximadamente el
0.5% de la equity, incluyendo la estimación de round-trip del motor, y
respeta `volume_min`, `volume_step`, `volume_max` y el límite de margen del
instrumento. El tamaño efectivo queda sujeto a redondeo y a esos límites.

## Fill, precio de referencia y costos

El precio de referencia declarado por `config/instruments.json` para `DAX`
es `price_basis: "unknown"`. Por tanto, esta spec **no asume mid, bid ni
ask**; la incertidumbre queda como reserva de Gate 0.

El motor debe leer directamente de `config/instruments.json` la siguiente
configuración de `DAX` y no recalcularla desde `docs/cost_model.md`, que es
histórico:

- `spread_points=50`;
- `commission_type="cash"` y `commission_per_side=2.75`;
- `slippage_points_per_side=12.5`;
- `swap_long=-31.7637528` y `swap_short=5.4717624`;
- `swap_schedule="triple"` y `triple_weekday=4` (viernes);
- `point=0.1`, `tick_size=0.1`, `tick_value=1.14712`,
  `contract_size=10.0`, `currency_to_account=1.14712`;
- `swap_unit="account_cash_per_lot"`, `rollover_timezone="America/New_York"`
  y `rollover_time="17:00"`.

El costo neto por operación debe incluir spread, comisión de entrada y
salida, slippage de cada lado y el swap correspondiente a dirección,
tenencia, calendario y triple rollover. La expectancy neta debe cumplir

`expectancy_neta / (spread + comisión + slippage + swap) >= 3.0`.

Ese ratio se calcula con los costos del instrumento real y no se puede
aprobar usando solo P&L bruto. `costs_verified=false` no bloquea esta
escritura: hereda la reserva de Gate 0 (`APTO_CON_RESERVAS`), pero bloquea
una aprobación final de `validator`. También permanecen explícitas las
reservas de `price_basis`, spread/slippage, calendario y dividendos que
figuran en `config/instruments.json`.

## Datos, IS/OOS y baseline

La división In-Sample/Out-of-Sample la fija `qaf/ingest.py` y es inmutable
una vez creada. `engine` debe usar únicamente
`data/clean/DAX/H4/IS.parquet`; `validator` abrirá
`data/clean/DAX/H4/OOS.parquet` una sola vez al final. Esta spec no redefine
el corte 70/30 ni mueve datos. La validación debe conservar además el
walk-forward dentro de esa separación física.

La puerta de baseline es superar **comprar y mantener de DAX H4**, en el mismo
slice OOS y neto de exactamente los mismos campos de
`config/instruments.json`. No se permite usar el índice cash, otro símbolo ni
un baseline genérico. El valor del baseline no se inventa en esta fase:
`validator` debe recalcularlo con el motor real. Si el baseline neto es
negativo por financiación, perder menos no basta; la estrategia debe
demostrar edge neto por encima de la financiación y de los costos.

## Puertas numéricas de aprobación

Se heredan sin relajación los defaults de `config/runner.json`:

- mínimo de 30 operaciones;
- profit factor mínimo de 1.3;
- máximo drawdown fraccional de 0.20;
- ratio de fricción mínimo de 3.0;
- superar el baseline neto de comprar y mantener del mismo `DAX` H4.

También son obligatorios OOS, walk-forward, controles de Gate 0, sensibilidad
de ±10–20% de cada parámetro libre, al menos 200 iteraciones de Monte Carlo
y prueba de permutación. Esta entrega no ejecuta backtest, optimización,
AED ni OOS, y no emite un veredicto de aprobación o rechazo.
