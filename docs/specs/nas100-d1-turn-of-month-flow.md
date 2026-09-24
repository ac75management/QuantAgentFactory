# Spec congelada — NAS100 D1 turn-of-month

Hipótesis #002. Estado: contrato congelado antes de IS; no aprobado y sin acceso OOS.

## Alcance y evidencia

- Activo: NAS100 CFD, D1, solo largo.
- Familia: `calendar_window`.
- Fuente: Ariel; Lakonishok y Smidt; McConnell y Xu. `IDEA-98890471BE` aporta la misma regla y linaje académico.
- Tipo: **adaptación**. La evidencia estudia índices bursátiles amplios/estadounidenses, no NAS100 ni su CFD específicamente.
- La variante de cuatro días antes de fin de mes no pertenece a esta hipótesis.

## Regla ejecutable y causal

1. El día de señal es el día hábil (lunes-viernes) inmediatamente anterior al último día hábil del mes. Se calcula desde la fecha de la barra, sin consultar barras futuras ni precios.
2. La fuente expresa entrada al cierre de ese día. El motor causal observa ese cierre y ejecuta al open de la barra siguiente, que corresponde al último día hábil del mes; esta diferencia de fill es una adaptación explícita.
3. La posición se mantiene durante el último día hábil del mes y los tres primeros días hábiles del siguiente. `max_holding=4` liquida al open de la cuarta barra posterior a la entrada, aproximando la salida al cierre del tercer día hábil con el fill causal del motor.
4. Festivos y cierres extraordinarios no se infieren de barras futuras. Hasta contar con calendario bursátil verificado, cualquier divergencia frente al calendario lunes-viernes es una reserva de Gate 0.
5. No hay filtros de precio ni rama corta. Una variante de ventana o instrumento exige otra hipótesis.

## Riesgo y salida

- ATR de Wilder: 14 barras.
- Stop: 1.5 ATR; objetivo: 2.5 ATR; ambos son válvulas de seguridad y no alteran la ventana de entrada.
- Salida temporal: `max_holding=4`; solo un gap de stop/target en ese open la precede.
- Riesgo: 0.5% del equity por operación; equity inicial: 100,000 USD.
- Sin piramidación; el motor descarta una nueva señal si ya existe posición.

## Fill, costos y datos

- Señal al cierre de `t`; fill al open de `t+1`, conforme a `qaf.engine.simulate`.
- `price_basis=unknown`: reserva, no se asume mid.
- Spread, comisión, slippage y swap se toman únicamente de `config/instruments.json`; `costs_verified=false`, calendario y procedencia sin verificar impiden aprobación final.
- IS/OOS usa la partición sellada del manifest. Engine solo puede leer IS; OOS permanece cerrado.

## Puertas y sensibilidad

Se heredan sin relajar las puertas de `config/runner.json`: operaciones mínimas, PF > 1.3, drawdown máximo, AED p<0.05, baseline 1x del mismo NAS100 D1, fricción >=3.0, estrés y bootstrap. La sensibilidad usa la política versionada; ningún vecino sustituye este contrato.

La spec JSON compañera es la fuente ejecutable. Cualquier cambio posterior a observar IS crea una hipótesis nueva.
