# Borrador metodológico: VWAP en NAS100/NDX H1

> **Estado: BLOQUEADO — no aprobado y no ejecutable.**
>
> Este documento es una propuesta de prueba. No es una hipótesis oficial, no
> tiene número en el registro, no es una spec ejecutable y no autoriza ningún
> backtest, apertura de OOS o conexión con un broker.

## 1. Pregunta falsable

En NAS100/NDX, durante la sesión regular estadounidense, ¿una desviación
extrema del precio respecto al VWAP de la sesión es seguida por una reversión
estadísticamente significativa hacia el VWAP antes de alcanzar un stop de
volatilidad, después de descontar spread, comisión, slippage y swap?

La hipótesis se consideraría fallida si no supera, en la validación final:

- profit factor OOS mayor que 1.30;
- p-valor de permutación menor que 0.05;
- ratio de expectancy neta frente a fricción de al menos 3.0;
- baseline de comprar y mantener del mismo NDX/H1, con los mismos costes.

## 2. Mecanismo conductual

La desviación intradía podría representar ejecución urgente, desequilibrio
temporal o sobreextensión. Parte de ese flujo podría agotarse antes del cierre
de la sesión, mientras participantes que usan VWAP como referencia favorecen
la convergencia hacia ese nivel.

Esta explicación no supone que toda desviación revierta. Un movimiento que
represente información nueva debe poder continuar y producir una pérdida.

## 3. Variante propuesta

La variante preferida es un VWAP reiniciado al comienzo de la sesión regular
estadounidense:

- sesión provisional: `09:30–16:00 America/New_York`;
- precio por barra provisional: `(high + low + close) / 3`;
- volumen: preferiblemente volumen real; si solo existe tick volume, debe
  declararse como proxy y aprobarse explícitamente;
- fórmula:

  `VWAP = sum(precio_típico * volumen) / sum(volumen)`.

La sesión y la fuente de volumen no están confirmadas. No pueden utilizarse en
un backtest hasta resolver Gate 0.

## 4. Reglas provisionales

Estas reglas solo demuestran que la idea puede hacerse concreta. No autorizan
una ejecución.

Parámetros libres provisionales, máximo cuatro:

1. `z_entry = 2.0`;
2. `k_SL = 1.5`;
3. `k_TP = 1.0`;
4. `max_bars = 8`.

Se calcularía:

`z_t = (Close_t - VWAP_t) / ATR14_t`

usando únicamente barras H1 cerradas.

### Entrada larga

Al cierre de una barra de sesión regular:

- `z_t <= -2.0`;
- cierre por debajo del VWAP;
- al menos 30 barras válidas acumuladas en la sesión;
- no existe posición abierta;
- no se entra durante los últimos 30 minutos de la sesión.

La orden se ejecutaría en el open de la barra siguiente.

### Entrada corta

Condiciones simétricas:

- `z_t >= +2.0`;
- cierre por encima del VWAP;
- VWAP válido y suficiente historial de sesión;
- sin posición abierta;
- fuera de los últimos 30 minutos.

### Salidas

Para una posición larga:

- `SL = precio_entrada - 1.5 * ATR14`;
- `TP = precio_entrada + 1.0 * ATR14`;
- salida si el precio alcanza el VWAP;
- salida temporal después de ocho barras H1;
- cierre al finalizar la sesión si no se autoriza riesgo overnight.

Para una posición corta se invierten las fórmulas.

Si stop y objetivo se alcanzan en la misma barra y no hay datos de ticks para
resolver el orden, se aplica el desempate conservador: primero el stop.

## 5. Riesgo y ejecución

- riesgo máximo provisional: 0.50 % del equity al inicio de la señal;
- volumen redondeado hacia abajo al `volume_step`;
- se descarta la señal si el volumen queda por debajo de `volume_min`;
- el cálculo debe incluir costes estimados de ida y vuelta.

Modelo de fill:

- señal con barra cerrada;
- ejecución en el open siguiente;
- compra con ask y venta con bid cuando existan;
- si solo existe mid, debe declararse la aproximación y añadirse spread;
- stops y objetivos deben aplicar bid/ask según el sentido de la posición.

## 6. Baseline y validación futura

El baseline obligatorio será comprar y mantener el mismo `NDX` en H1, durante
la misma ventana y neto de los mismos costes. No se permite sustituirlo por
QQQ, Nasdaq cash u otro timeframe.

Si los bloqueos se resuelven, el flujo futuro será:

1. 70 % IS y 30 % OOS en archivos separados;
2. `engine` solo lee IS;
3. `validator` abre OOS una única vez;
4. walk-forward, permutación, Monte Carlo y sensibilidad;
5. veredicto `APROBADA`, `RECHAZADA` o `INVALID_POR_DATOS`.

## 7. Bloqueos actuales

1. La serie local H1 todavía no existe. Debe obtenerse mediante el extractor
   de Darwinex/MT5 antes de ejecutar la prueba.
2. [`docs/universe.md`](./universe.md) y
   [`config/instruments.json`](../config/instruments.json) ya declaran
   NAS100/NDX en H1, H4 y D1.
3. El histórico existente contiene `tick_volume`, mientras `real_volume` es
   cero en todas las filas; no hay volumen centralizado del futuro Nasdaq.
4. No está validada la reconstrucción de la sesión regular en las barras H1.
5. `price_basis` aparece como `unknown`.
6. Spread y slippage de NDX no tienen un modelo histórico confirmado.
7. Deben reconciliarse contrato, tick value, swaps, conversiones y ajustes
   del CFD.
8. No existe todavía una hipótesis correspondiente en
   [`docs/hypotheses/_registry.md`](./hypotheses/_registry.md).

## 8. Próximo paso

Mañana, el flujo multi-IA debe investigar por separado la literatura VWAP, la
viabilidad de los datos, la sesión NDX y las variantes de implementación.
Después, un sintetizador decidirá si la idea es:

- `TESTABLE`;
- `TESTABLE_CON_RESERVAS`;
- `INVALID_POR_DATOS`; o
- `RECHAZADA_POR_EVIDENCIA`.

Solo con una decisión testeable, una hipótesis registrada y un Gate 0
resuelto, `protocol` podrá convertir este borrador en una spec ejecutable.
