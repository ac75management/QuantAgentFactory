# Taxonomía del Iceberg de Trading — QuantAgentFactory

Filtro de madurez para lo que `investigator` acepta como fuente. Adaptado del material que trajo Alexander (2026-09-23).

## 6 niveles
1. **Superficie** — humo, promesas de riqueza rápida, grupos de señales. Nunca es fuente válida.
2. **Bases** — compra/venta, tipos de orden, gráficos simples. Demasiado genérico como fuente de hipótesis.
3. **Fundamentos** — análisis técnico, patrones de vela, soportes/resistencias, riesgo básico. Punto de partida aceptable, nunca pre-validado — pasa por AED igual que cualquier otro.
4. **Pilares avanzados** — volumen, order flow, market profile, correlaciones entre activos, riesgo de ruina. Nivel donde `investigator` debería operar la mayoría del tiempo.
5. **Expertise profesional / generación de alfa** — modelado matemático/estadístico, grafos de decisión, algoritmos. Nivel objetivo del sistema (Kaufman, Raschke, Chan, Pardo, López de Prado, Aronson caen aquí).
6. **Élite / creador de mercado** — sistemas dinámicos complejos, teoría del caos, aprendizaje por refuerzo multiagente. Aspiracional, no operable con nuestros recursos hoy — ver la nota de escepticismo en [docs/review_round3.md](review_round3.md).

## Regla de uso
`investigator` cita siempre de qué nivel viene una idea.
- Nivel 1-2: descartar sin escribir hipótesis.
- Nivel 3: aceptar solo si el AED confirma el patrón con más rigor del que trae la fuente.
- Nivel 4-5: fuente preferente.
- Nivel 6: tratar con escepticismo explícito — parte del material "nivel 6" que trajo Alexander no pasa nuestra propia regla de codificación ("si no se puede escribir en código, no existe").
