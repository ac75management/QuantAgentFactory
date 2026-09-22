# QuantAgentFactory — Revisión exhaustiva (ronda 3): material nuevo y conflictos a resolver

Para pegar en Grok o Gemini (modo razonamiento/Pro), junto con el prompt de instrucciones ya usado en la ronda 2 (sé crítico, no elogies sin sustento, responde punto por punto). Pega también, a continuación de este documento, el material fuente completo que ya tienes: la taxonomía "Iceberg de Trading" + los 5 módulos de arquitectura, y el bloque de investigación empírica "Lisa Forex / Algo Lab". Aquí solo van las preguntas y los conflictos ya detectados — no hace falta repetir todo lo que ya se validó en rondas anteriores.

## Conflicto 1 — dirección del split IS/OOS (el más importante)
Diseño actual: 70% In-Sample (diseño) / 30% Out-of-Sample (validación), separación física.
Reclamo de la fuente nueva (63,499 estrategias, sin paper revisado por pares — tratar con escepticismo de fuente): diseñar en una muestra PEQUEÑA (1-2 años) y validar en una muestra GRANDE de datos no vistos (10-14 años) mejora el éxito en cuenta real +6.71%.
**Pregunta:** ¿es una técnica legítima (diseño en ventana corta reduce sobreajuste; validación en ventana larga da más poder estadístico) o es una cifra sin rigor detrás? Si es legítima, ¿reemplaza al 70/30, o se combinan (ej. diseño en 1-2 años, y dentro de lo restante aplicar igual una separación IS/OOS)?

## Conflicto 2 — contenido no codificable disfrazado de rigor (Módulo 4)
La fuente nueva incluye un "GTS Score" (función sin fórmula real: `f(sentimiento, tamaño, estructura)`), árboles de decisión bayesianos, teoría del caos/efecto mariposa, y una estrategia psicológica de "perdón estadístico del 30%" ante pérdidas (cita a Sigmund & Nowak, teoría de juegos evolutiva). Nuestra regla dice "si no se puede escribir en código, no existe".
**Pregunta:** ¿algo de esto es real y codificable, o es decoración conceptual que no debería entrar al sistema?

## Conflicto 3 — ejemplo de estrategia que viola nuestro propio alcance
La fuente nueva presenta "ELON Breakout" como caso de referencia: TSLA, velas de 5 minutos, duración promedio de operación 30 minutos, cierre forzoso el mismo día. Nuestro CLAUDE.md excluye explícitamente frecuencia por debajo de 4H y scalping/alta frecuencia.
**Pregunta:** confirma si coincides en que este ejemplo NO debería usarse como referencia (aunque sus métricas se vean bien: PF 2.3, 60% win rate) — un resultado así, en una sola acción, con métricas casi perfectas, es justo el perfil de sobreajuste que nuestras propias puertas deberían rechazar.

## Conflicto 4 — nuevos autores propuestos: ¿cuáles son reales?
La fuente nueva suma a la biblioteca: David Aronson (*Evidence-Based Technical Analysis*), Jim Simons, Robert Axelrod.
Valoración preliminar: Aronson encaja como categoría B (metodología anti-sobreajuste) junto a López de Prado/Pardo. Simons no tiene metodología pública (Renaissance Technologies es famoso por ser secreto) — citarlo no da nada operable. Axelrod es teórico de juegos académico (*La evolución de la cooperación*), no autor de trading — su presencia aquí viene de la metáfora "Tit-for-Tat" del Módulo 4, no de una fuente de hipótesis real.
**Pregunta:** ¿coincides, o ves algo aprovechable en Simons/Axelrod que se nos escape?

## Puntos que ya se dan por adoptados (no hace falta evaluarlos, solo tenerlos en cuenta al responder)
- Modo Caos / sensibilidad de parámetros ±10-20% — tercera fuente independiente lo confirma.
- Ratio de fricción ≥3.0 — esta fuente lo repite igual, ya adoptado.
- Exclusión de spread nocturno/viernes — fácil de sumar al Gate 0.
- "Punto dulce" de 4-8 componentes estructurales (distinto de "3-4 parámetros libres", no se contradicen).

## Pregunta de cierre
¿Hay algo más en este material nuevo (taxonomía del iceberg, módulos 1-5, bloque Lisa Forex) que debería entrar al sistema y que no cubran las preguntas de arriba?
