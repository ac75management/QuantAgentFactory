# Hipótesis: momentum de series temporales en US30 diario

## Estado

Pendiente de traducción por `protocol`. No es una afirmación de rentabilidad y todavía no
se ha ejecutado ningún backtest.

## Fuente e inspiración

La fuente principal es **Moskowitz, Ooi y Pedersen (2012), “Time Series
Momentum”, Journal of Financial Economics**. El estudio documenta persistencia
direccional en una muestra amplia de futuros líquidos de renta variable, bonos,
divisas y materias primas, con señales construidas a partir del retorno pasado
del propio activo y horizontes de varios meses. Es una fuente de evidencia
cuantitativa, no un vídeo o curso.

Como evidencia de largo plazo y contrapeso, **Hurst, Ooi y Pedersen (2017),
“A Century of Evidence on Trend-Following Investing”, Journal of Portfolio
Management**, estudia la persistencia de trend-following en futuros y forwards
desde finales del siglo XIX. El resultado no garantiza que una implementación
concreta sobreviva en el universo de Darwinex, pero hace plausible estudiar el
mecanismo en vez de descartarlo como una regla técnica aislada.

La hipótesis también es consistente con la literatura de underreaction y
momentum, por ejemplo **Hong y Stein (1999), “A Unified Theory of
Underreaction, Momentum Trading, and Overreaction in Asset Markets”, Journal of
Finance**. Ese trabajo ofrece un mecanismo conductual para la difusión gradual
de información, aunque no valida por sí solo esta aplicación a un CFD.

## Mercado y frecuencia

- **Activo propuesto:** US30, símbolo MT5 `WS30`, CFD de índice activo en
  `docs/universe.md`.
- **Frecuencia:** D1.
- **Familia ejecutable prevista:** `trend_cross`, siempre que `protocol`
  traduzca la idea a una especificación sin añadir una segunda fuente de
  señal no justificada.

El contexto original de la evidencia principal son **futuros líquidos
multi-activo**, no CFDs minoristas. Por tanto, la prueba en `WS30` es una
extrapolación: el CFD debería seguir razonablemente al futuro/índice
subyacente, pero tiene cotización, horario, financiación y costes propios del
bróker. La extrapolación debe tratarse como una pregunta empírica, no como una
transferencia directa del resultado publicado.

## Lógica de comportamiento

La hipótesis es que un movimiento direccional suficientemente persistente no
se incorpora de una sola vez al precio. La información macroeconómica y los
cambios en expectativas de tipos, crecimiento o beneficios llegan por
episodios; los participantes actualizan sus posiciones con retraso y muchos
vehículos institucionales escalonan entradas, límites de riesgo y coberturas.
Ese proceso puede producir autocorrelación direccional a horizontes diarios,
en lugar de una reversión inmediata.

La señal propuesta debe medir únicamente la dirección y persistencia del
precio del propio US30 mediante una estructura de tendencia lenta/rápida. No
se propone un umbral numérico en este documento. La intuición es mantener la
exposición mientras la evidencia de tendencia siga presente y reducirla o
invertirla cuando la relación direccional se deteriore. Esto no equivale a
afirmar que toda tendencia continúe ni a ignorar los episodios de reversión
violenta.

## Quién genera el edge y quién está al otro lado

Los posibles generadores de la oportunidad son:

1. inversores discrecionales que reaccionan gradualmente a noticias y régimen
   macroeconómico;
2. instituciones que deben ejecutar coberturas o asignaciones por tramos y no
   pueden cambiar toda la exposición al precio óptimo;
3. participantes con límites de riesgo, mandatos long-only o restricciones de
   liquidez que venden una tendencia alcista demasiado pronto o compran una
   caída antes de que termine.

El otro lado lo proporcionan esos operadores de cobertura, market makers,
arbitrajistas y gestores discrecionales que aceptan inventario y riesgo de
reversión a cambio del spread, de la prima por liquidez o de cumplir un
mandato. La estrategia no supone que exista un único “perdedor” identificable:
el edge, si existe, sería una compensación agregada por asumir cambios de
exposición y riesgo de whipsaw.

## Horizonte de holding esperado

La literatura original estudia horizontes de semanas a meses. En esta
investigación la frecuencia de observación y decisión será diaria, pero el
holding esperado sigue siendo de varios días a varias semanas, potencialmente
más largo en tendencias persistentes. No es una hipótesis de scalping,
intradiaria ni de alta frecuencia.

## Por qué no se ha arbitrado por completo

El efecto puede no comprimirse del todo por varias razones:

- las tendencias y los shocks macroeconómicos son intermitentes y difíciles de
  calendarizar;
- seguir la señal implica soportar muchas falsas rupturas, giros bruscos y
  periodos sin recompensa;
- el apalancamiento, los límites de drawdown y los mandatos institucionales
  impiden a algunos participantes mantener una posición hasta que la tendencia
  madura;
- la financiación overnight, el spread, el slippage y el horario específico
  del CFD reducen la capacidad de explotar movimientos pequeños;
- las estrategias trend-following conocidas compiten por la misma exposición,
  pero su ejecución, velocidad, gestión de riesgo y universo no son idénticos.

Estas razones son una explicación de persistencia potencial, no evidencia de
que la ventaja neta sobreviva en `WS30`.

## Riesgos y condiciones de refutación

La hipótesis debe considerarse refutada para este activo si, después de costes
realistas y de una validación walk-forward, no muestra una relación
direccional estable o si el resultado depende de una zona estrecha de
parámetros. También debe vigilarse que el resultado sea solo una prima de
riesgo de tendencia común al índice, que desaparezca al cambiar el periodo de
la muestra, o que el CFD tenga financiación y horarios que anulen la señal.

La comparación deberá incluir el baseline exigido por el repositorio y separar
físicamente IS/OOS. El análisis de robustez, los costes y el fill pertenecen a
las fases posteriores; este documento no fija reglas numéricas ni afirma
rentabilidad.

## Referencias

- Moskowitz, T. J., Ooi, Y. H. y Pedersen, L. H. (2012), “Time Series
  Momentum”, *Journal of Financial Economics*, 104(2), 228–250.
- Hurst, B., Ooi, Y. H. y Pedersen, L. H. (2017), “A Century of Evidence on
  Trend-Following Investing”, *Journal of Portfolio Management*, 44(1),
  15–29.
- Hong, H. y Stein, J. C. (1999), “A Unified Theory of Underreaction, Momentum
  Trading, and Overreaction in Asset Markets”, *Journal of Finance*, 54(6),
  2143–2184.
