# Hipótesis: momentum de series temporales en DAX H4

## Estado

Pendiente de AED y de traducción por `protocol`. No es una afirmación de
rentabilidad y no se ha ejecutado ningún backtest.

## Fuente e inspiración

La fuente principal es **Moskowitz, Ooi y Pedersen (2012), “Time Series
Momentum”, Journal of Financial Economics, 104(2), 228–250**. El trabajo
estudia la persistencia de los retornos propios del activo en 58 futuros
líquidos de renta variable, bonos, divisas y materias primas, con señales de
dirección basadas en retornos pasados y tenencias que duran semanas o meses.
Como evidencia de persistencia histórica y contrapeso, **Hurst, Ooi y
Pedersen (2017), “A Century of Evidence on Trend-Following Investing”,
Journal of Portfolio Management, 44(1), 15–29**, examina trend-following en
futuros y forwards a lo largo de un periodo muy extenso. **Hong y Stein
(1999), “A Unified Theory of Underreaction, Momentum Trading, and Overreaction
in Asset Markets”, Journal of Finance, 54(6), 2143–2184**, aporta el mecanismo
conductual de difusión gradual de información.

Esta hipótesis está vinculada a la #004 (`us30-d1-time-series-momentum`), pero
no es un ajuste de sus parámetros ni un intento de rescatar un resultado
fallido: es una replicación preespecificada en otro índice, otra región, otra
frecuencia y con una ventana de negociación parcialmente distinta. La razón
para hacerla por separado es comprobar si el mecanismo documentado en futuros
multi-activo se transporta al índice europeo y a H4, en vez de asumir que el
resultado del US30 representa a todo el universo. Si el protocolo considera
que esa replicación cuenta como duplicación semántica, debe rechazarla antes de
AED y no tratarla como una nueva familia de pruebas.

## Mercado y frecuencia

- **Activo:** DAX, símbolo MT5 `GDAXI`, CFD de índice activo según
  `docs/universe.md`.
- **Frecuencia:** H4.
- **Familia ejecutable prevista:** `trend_cross`.

La validación original de las fuentes se hizo principalmente en **futuros y
forwards líquidos multi-activo**, no en el CFD minorista `GDAXI` ni
específicamente en H4. Por tanto, esto es una extrapolación de riesgo. El CFD
puede diferir por horario de cotización, spread, financiación, slippage y
formación de precios alrededor de la apertura europea. La fuente no demuestra
por sí sola que la prima exista después de esos costes.

## Lógica de comportamiento

La información sobre crecimiento, inflación, tipos, energía y riesgo europeo
se incorpora en episodios, no necesariamente en una sola transacción. Los
gestores institucionales escalonan asignaciones y coberturas, mientras que
los participantes sujetos a límites de riesgo esperan confirmación antes de
ampliar exposición. Esa actualización gradual puede generar persistencia
direccional durante varias velas H4. El efecto esperado no es que cada
movimiento continúe, sino que, en ciertos regímenes, la probabilidad de que
persista la dirección reciente sea mayor que la implícita en un paseo
aleatorio.

La señal que `protocol` traduzca deberá usar únicamente una relación de
tendencia rápida/lenta sobre el propio DAX. Este documento no fija periodos,
umbrales, stops, objetivos ni reglas de salida numéricas.

## Participantes y lado contrario

Los posibles generadores del desequilibrio son:

1. gestores que incorporan gradualmente nueva información macro europea;
2. instituciones que ejecutan coberturas o cambios de asignación por tramos;
3. operadores discrecionales y mandatos con límites de pérdida que reducen
   una posición antes de que el régimen direccional termine.

El lado contrario lo forman market makers, hedgers y gestores que aceptan
inventario o riesgo de reversión para proporcionar liquidez, junto con
operadores que cierran demasiado pronto por restricciones de mandato. La
hipótesis no identifica a un perdedor único: la compensación potencial sería
por asumir whipsaws, gaps y riesgo de régimen.

## Horizonte de holding esperado

El holding esperado es de varios días a varias semanas, sujeto a que la
tendencia permanezca activa. La frecuencia H4 solo determina cuándo se
actualiza la señal; no convierte la idea en scalping ni en trading de alta
frecuencia. El protocolo deberá comprobar que el holding real sea compatible
con spread, financiación y costes del CFD.

## Por qué no se ha arbitrado por completo

- Las tendencias son intermitentes y no se conocen de antemano sus fechas de
  inicio y final.
- Seguirlas exige soportar falsas señales, gaps y reversiones rápidas, por lo
  que muchos participantes reducen tamaño o abandonan durante drawdowns.
- Los mandatos, límites de tracking error y necesidades de liquidez impiden a
  algunas instituciones mantener una exposición hasta que se materializa el
  movimiento.
- La financiación, el spread y el slippage del CFD eliminan oportunidades
  pequeñas y hacen que la ejecución y el control de riesgo importen tanto
  como la dirección.
- La existencia pública del trend-following atrae capital competidor, pero
  sus universos, velocidades, costes y restricciones no son idénticos; la
  competencia puede comprimir una parte del efecto sin eliminar toda la
  heterogeneidad entre activos y horarios.

Estas razones hacen plausible investigar la hipótesis, pero no prueban que
sea explotable.

## Criterios de refutación y bloqueos

La hipótesis deberá considerarse refutada para `GDAXI` si la persistencia no
es estable entre subperiodos y ventanas walk-forward, si depende de una zona
estrecha de parámetros, o si los costes y la financiación consumen el efecto.
También debe rechazarse si no supera el baseline exigido por el repositorio o
si la evidencia queda confinada a un único episodio macro.

Bloqueos explícitos:

1. `docs/research_external/` no contiene actualmente un informe entregado
   sobre momentum en DAX/CFD H4; las referencias anteriores son literatura
   pública conocida, no evidencia específica de `GDAXI`.
2. La extrapolación futuro/forward → CFD y diario/semanal → H4 debe
   demostrarse con AED y costes del universo real; no debe presentarse como
   replicación directa de los resultados publicados.
3. El fill, la calidad de datos, la separación IS/OOS, walk-forward y la
   robustez pertenecen a fases posteriores. Este documento no autoriza
   backtest ni define una spec.
4. No se deben añadir filtros macro, calendario, COT u order flow: no están
   disponibles en `docs/universe.md` y además no son necesarios para la
   familia prevista.

## Referencias

- Moskowitz, T. J., Ooi, Y. H. y Pedersen, L. H. (2012), “Time Series
  Momentum”, *Journal of Financial Economics*, 104(2), 228–250.
- Hurst, B., Ooi, Y. H. y Pedersen, L. H. (2017), “A Century of Evidence on
  Trend-Following Investing”, *Journal of Portfolio Management*, 44(1),
  15–29.
- Hong, H. y Stein, J. C. (1999), “A Unified Theory of Underreaction,
  Momentum Trading, and Overreaction in Asset Markets”, *Journal of Finance*,
  54(6), 2143–2184.
