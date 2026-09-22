# Hipótesis: ruptura de canal Donchian de corto plazo en US30 H1

## Estado

Pendiente de traducción por `protocol`. No es una afirmación de rentabilidad y
no se ha ejecutado ningún backtest ni se ha abierto OOS.

## Relación con la hipótesis #004

Esta es una hipótesis nueva y separada de
`us30-d1-time-series-momentum` (#004). La #004 propone momentum de series
temporales diario y una relación de medias rápida/lenta (`trend_cross`), sin
fijar un umbral de ruptura. No se puede transformar limpiamente en una ruptura
de canal H1: cambiar la frecuencia y sustituir el estimador de tendencia por
un máximo/mínimo móvil cambia el evento de entrada y el horizonte conductual.
La presente hipótesis prueba explícitamente la continuación tras romper el
rango reciente, no la misma señal diaria a otra frecuencia.

## Mercado y frecuencia

- Activo primario: US30, alias del universo y clave de
  `config/instruments.json`; símbolo MT5 `WS30`.
- Frecuencia: H1. Está dentro del alcance de `CLAUDE.md` y figura entre los
  timeframes permitidos para US30.
- Alternativas para una investigación posterior, no parte de esta prueba:
  NAS100 y SP500. No se hace un barrido multiíndice.

## Mecanismo

Una salida alcista del máximo del rango reciente puede indicar que la demanda
está absorbiendo la oferta disponible y que una tendencia intradía extendida
continúa durante varias barras. La salida bajista simétrica prueba el mismo
mecanismo del lado vendedor. El riesgo principal es el whipsaw en rangos
laterales; por eso la prueba exige costes realistas, stop, objetivo y tiempo
máximo de exposición.

## Regla propuesta

El contrato numérico de esta hipótesis está en
`docs/specs/us30-h1-channel-breakout.json`. El canal usa el máximo y mínimo de
las 24 barras H1 anteriores (sin incluir la barra de señal). Se genera señal
larga si el cierre de la barra t es mayor que ese máximo, y corta si es menor
que ese mínimo. La señal se calcula causalmente y se ejecuta en el open de
t+1. La posición se dimensiona al 1% de la equity arriesgada hasta el stop.
El motor aplica ATR(14), stop de 1.5 ATR, objetivo de 3 ATR y salida temporal
a las 24 barras.

## Refutación

La hipótesis queda refutada para esta prueba si, después de costes y en la
validación walk-forward/ OOS, no supera las puertas de la spec, no supera el
buy-and-hold neto del mismo US30 H1, o solo funciona en una zona estrecha de
parámetros.

