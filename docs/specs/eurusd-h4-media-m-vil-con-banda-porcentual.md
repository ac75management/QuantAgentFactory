# Spec: eurusd-h4-media-m-vil-con-banda-porcentual

**Estado: contrato registrado; listo para Gate 0 y corrida IS por `engine`. No es una estrategia validada.**

- Hipótesis: `008` de 9 registradas.
- Objetivo: EURUSD / H4, dentro del universo de investigación.
- Familia: `ma_band_breakout`, ruptura simétrica causal alrededor de una SMA.
- OOS permanece cerrado y no se consultó ningún resultado para fijar esta versión.

## Regla de entrada congelada

Se calcula `SMA(10)` con cierres hasta la barra `t`. La banda superior es `SMA × 1.03` y la inferior `SMA × 0.97`. Hay señal larga únicamente cuando el cierre cruza desde un valor menor o igual a la banda superior previa hacia un cierre estrictamente superior a la banda superior actual. La señal corta es simétrica: cruza desde un valor mayor o igual a la banda inferior previa hacia un cierre estrictamente inferior a la banda inferior actual. Permanecer fuera de una banda no repite señales.

La señal observada al cierre de `t` se llena al open de `t+1`. La serie es causal: ninguna media ni condición usa barras futuras. `direction=both`.

## Adaptación previa al IS

Kaufman sustenta el mecanismo cualitativo, pero la fuente primaria accesible no fija una única combinación numérica. Alexander autorizó implementar la familia para destrabar 008. Antes de observar IS se congelan `SMA(10)` y banda simétrica de 3%, valores mencionados únicamente por fuentes secundarias; son una adaptación sometida a falsación, no parámetros atribuidos como verificados a Kaufman.

La fuente tampoco fija una salida única. Se adopta la política conservadora común del proyecto: ATR(14), stop de `1.5 × ATR`, target de `3.0 × ATR`, riesgo de 0.5% del equity y salida temporal a 30 barras H4 (cinco días). `max_holding` cierra al open de `entrada + 30`; solo un gap de stop/target en ese open lo precede. Una ruptura opuesta no fuerza rotación mientras ya hay posición: la salida queda exclusivamente en stop, target o tiempo para que el contrato coincida exactamente con el motor.

Cambiar cualquiera de estos valores después de ver IS constituye una hipótesis nueva; la sensibilidad solo diagnostica la vecindad ±10/20% y nunca reemplaza esta spec.

## Datos, costos y puertas

El dataset es la partición EURUSD/H4 IS ya sellada; `engine` debe ejecutar Gate 0 antes de AED/backtest y no abrir OOS. La señal usa cierres del archivo y el fill usa el open siguiente. `price_basis=unknown`, `costs_verified=false`, calendario y procedencia no verificados permanecen como reservas explícitas que impiden una aprobación final.

Los costos se leen exclusivamente de `config/instruments.json`: spread, comisión por lado, slippage por lado, swap largo/corto, calendario triple y conversión de divisa. La estrategia debe tener al menos 30 operaciones, profit factor >1.3, drawdown ≤20%, ratio de fricción ≥3.0, superar el baseline EURUSD/H4 con el mismo capital 1× y pasar AED, estrés, bootstrap y sensibilidad según `config/runner.json`.

## Naturaleza de la prueba

Es una adaptación de una técnica diaria y multi-activo a EURUSD H4 CFD. La implementación habilita una prueba falsable; no corrige la debilidad de la evidencia numérica ni anticipa rentabilidad. Un fallo IS cierra esta versión y no autoriza rescatarla ajustando parámetros.
