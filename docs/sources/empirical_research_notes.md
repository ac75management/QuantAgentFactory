# Notas empíricas externas — "Lisa Forex / Algo Lab"

Reclamos de una fuente externa (extracción de video/curso, no paper revisado por pares). Se tratan como hipótesis a verificar con nuestro propio AED, no como hecho establecido — misma regla que aplicamos a cualquier otra fuente.

## Reclamos con cifras
- **241,505 estrategias, 2018-2025, 28 pares/índices/metales**: rentabilidad mediana ~32% en M15, ~40%+ en H4. Pasar de M15 a H4 sube la probabilidad de rentabilidad ~+7% neto. → Refuerza (no prueba) la decisión ya tomada de excluir por debajo de 4H.
- **Personalidad de activos**: USD/JPY tendencial, AUD/CAD reversivo, EUR/USD sin sesgo claro. → Pista para `investigator`, no regla — se confirma o descarta con AED propio sobre nuestros datos.
- **"Punto dulce" de complejidad** (50,865 estrategias): 1-2 componentes = alta tasa de fallo; 4-8 componentes = zona más rentable; >12 = sobreajuste. → Complementa (no contradice) la regla de "máx. 3-4 parámetros libres": son cosas distintas. *Parámetro* = valor numérico ajustable (período, multiplicador). *Componente* = bloque estructural (señal de entrada, filtro de orden, stop-loss, take-profit, salida por tiempo). Un sistema de 5 componentes puede tener solo 3 parámetros libres.
- **"Modo Caos"** (Montecarlo de sensibilidad ±10-20%, 200 iteraciones): la curva original debe quedar en el centro de un abanico de curvas, no ser la más ganadora. → Coincide exactamente con lo ya propuesto en la ronda 1 de revisión (Gemini/otro revisor). Tercera fuente independiente confirmando lo mismo — alta confianza, ya adoptado.
- **Regla de data split "diseño en muestra PEQUEÑA (1-2 años), validar en muestra GRANDE OOS (10-14 años)"**, +6.71% de éxito reportado en cuenta real. → **Contradice nuestro 70/30 actual** (diseñamos en la porción grande, validamos en la chica). Es el conflicto más importante sin resolver — ver [docs/archive/reviews/review_round3.md](../archive/reviews/review_round3.md), no se resolvió por cuenta propia.
- **Exclusión de spread nocturno/viernes** (00:00-01:00 GMT, últimos 15 min del viernes) por ensanchamiento de spread. → Fácil de sumar al Gate 0 / modelo de costos ya planeado.
- **Prueba en cuenta real de 0.01 lotes** (no solo demo) para medir fricción real antes de escalar. → Refina la fase de incubación (30-60 días demo): sumar un tramo en cuenta real micro antes de escalar a tamaño completo.

## Reclamos de gestión de capital (no arquitectura de investigación — para después)
- "Cuentas lógicas": dividir mentalmente una cuenta física en subcuentas para diversificar riesgo con margen compartido.
- Matrices de correlación <0.34 para combinar estrategias aprobadas.

Ambos son de la fase de portafolio/despliegue, no de investigación — quedan aparcados hasta que haya al menos una estrategia aprobada (ver PARKED IDEAS en PROJECT_STATE.md).
