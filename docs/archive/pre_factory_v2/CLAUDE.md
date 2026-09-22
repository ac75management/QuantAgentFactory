# QuantAgentFactory — CLAUDE.md

## Propósito
Repositorio de investigación cuantitativa asistida por agentes. Objetivo: convertir una hipótesis de trading en una estrategia validada, siguiendo el método TIS (hipótesis → AED → reglas → backtest → optimización → robustez → sizing → deploy), documentado en [docs/philosophy.md](docs/philosophy.md).

Proyecto independiente de ZOO2. No comparte cuenta, capital ni conexión de bróker con ningún otro proyecto.

## Alcance de mercado y frecuencia
- Mercados: CFDs (índices, forex, materias primas) y futuros, como foco principal. Ampliable a otros mercados más adelante, uno a la vez, no por defecto.
- Frecuencia: diario o 4H como mínimo. Nunca por debajo de 4H.
- Excluido explícitamente: alta frecuencia / scalping, estrategias de rebalanceo de cartera.
- Motivo: a esta frecuencia, spread/comisión/slippage del bróker quedan como margen operativo menor, no como la causa de pérdida de la cuenta (ver regla dura 11).
- Los autores citados en docs/philosophy.md (Kaufman, Raschke) son ejemplos ilustrativos de la fuente original del método, no el catálogo de dónde sacar hipótesis. `investigator` busca su propia literatura/patrones dentro de este alcance.

## Reglas duras (ningún agente las viola)
1. Nunca ejecutar operaciones reales ni conectar con una cuenta de bróker (demo o real) sin confirmación explícita y fresca de Alexander en el chat, sesión por sesión.
2. Nunca desplegar en VPS ni activar ejecución automatizada 24/7 sin esa misma confirmación explícita.
3. Toda estrategia pasa por las 8 fases del método TIS en orden. Ninguna estrategia queda "aprobada" sin pasar por robustez (Montecarlo + Out-of-Sample + permutación).
4. División de datos por defecto: 70% In-Sample / 30% Out-of-Sample. El OOS no se toca para optimizar parámetros, solo para validar al final.
5. Puertas numéricas mínimas por defecto (placeholders — confirmar/ajustar en PROJECT_STATE.md antes de la primera validación real):
   - Profit factor OOS > 1.3
   - p-valor de test de permutación < 0.05
   - Máximo drawdown OOS: se fija por estrategia en su spec, no hay default global todavía
6. Todo código de simulación/backtest en Python 3. Ninguna librería de ejecución de órdenes reales en este repo.
7. Cada fase deja un archivo (reporte, JSON o script) en la carpeta correspondiente — nunca solo un mensaje de chat que se pierde al cerrar la sesión.
8. Idioma: documentación y reportes en español. Nombres de variables/funciones en código, en inglés (convención estándar).
9. **Gate 0 — Calidad de datos**: ningún dataset entra a AED (fase 2 del método TIS) sin pasar el chequeo de `.claude/skills/data-quality-check/SKILL.md`. Datos sucios (huecos, duplicados, outliers no explicados, splits/dividendos o rollover de futuros sin ajustar) se documentan y el dataset se limpia o se descarta — nunca se ignora en silencio.
10. **Anti-minería de fuerza bruta**: prohibido correr búsquedas automatizadas masivas de combinaciones de parámetros sin una hipótesis de `investigator` que las respalde. Toda optimización se justifica por lógica de comportamiento, no solo por mejorar la curva de equidad.
11. **Costo de bróker como margen, no como causa de pérdida**: la expectativa neta (después de spread + comisión + slippage estimado) debe superar ese costo de fricción por un margen mínimo — fijado en la regla 17 (ratio ≥3.0). Ninguna estrategia queda "aprobada" solo por profit factor bruto, sin pasar este ratio.
12. **Alcance de mercado y frecuencia**: ver sección "Alcance" arriba. Cualquier hipótesis fuera de ese alcance se rechaza en `protocol`, antes de llegar a `engine`.
13. **Separación física de datos IS/OOS**: en la extracción, los datos se cortan 70/30 en archivos separados (`data/<símbolo>/IS.*` y `data/<símbolo>/OOS.*`). `engine` solo lee el archivo IS durante el desarrollo; el archivo OOS solo lo abre `validator`, una vez, al final.
14. **Análisis de sensibilidad de parámetros obligatorio**: ±10-20% sobre cada parámetro libre, mínimo 200 iteraciones tipo Montecarlo. La curva original debe quedar en el centro del abanico de curvas resultante, no ser la más ganadora.
15. **Fase de incubación obligatoria** antes de cualquier disponibilidad para live: 30-60 días en cuenta demo, seguidos de un tramo en cuenta real a lotaje mínimo (ej. 0.01) para medir fricción real que la demo esconde — cada paso requiere confirmación explícita de Alexander.
16. **Tope de parámetros libres optimizables**: 3-4 por estrategia. Distinto de "componentes estructurales" (señal de entrada, filtro, SL, TP, salida por tiempo) — ahí la zona más sana documentada es 4-8 componentes; menos de 2 o más de 12 componentes se trata con sospecha.
17. **Ratio de fricción mínimo**: expectancy neta / (spread+comisión+slippage+swap) ≥ 3.0, usando `docs/cost_model.md`.
18. **Metodología de validación real**: walk-forward (rolling: entrenar en periodo 1, probar en periodo 2; entrenar en 1+2, probar en 3; y así sucesivamente) es el estándar, no un split estático de una sola vez. El split 70/30 fija el corte IS/OOS general; dentro de eso, la validación real avanza en ventanas.
19. **Puerta de baseline obligatoria**: ninguna estrategia se aprueba si no supera un "comprar y mantener" del mismo activo, con los mismos costos, en la misma ventana OOS.
20. **Tercer estado de veredicto**: `INVALID_POR_DATOS` (dato insuficiente o de mala calidad) es distinto de `RECHAZADA` (no cumple puertas de desempeño). `validator` lo usa cuando `data_quality.md` no es APTO sin confirmación explícita de Alexander.
21. **Modelo de fill explícito**: toda spec fija cómo se ejecuta la orden (por defecto: al open de la siguiente barra tras la señal) y qué precio de referencia usa (bid/ask/mid, según lo que declare Gate 0) — nunca se asume sin documentar.
22. **Registro de hipótesis obligatorio**: `investigator` consulta y actualiza `docs/hypotheses/_registry.md` antes de escribir cualquier hipótesis nueva, para poder controlar cuántas ideas se han probado en total (contra sobreajuste por múltiples pruebas).

## Agentes disponibles (.claude/agents/)
- **investigator** — investiga ineficiencias documentadas y redacta hipótesis con lógica de comportamiento.
- **protocol** — aplica el método TIS: traduce hipótesis en reglas numéricas y puertas de aprobación.
- **engine** — limpia datos, corre AED y backtest en Python.
- **validator** — pruebas de robustez, veredicto final, genera el código de despliegue si aprueba.

Invocar con la herramienta Agent y el `subagent_type` correspondiente. No dupliques su trabajo en el hilo principal — si un agente ya está haciendo la tarea, no la repitas en paralelo.

## Estructura
- [docs/architecture.md](docs/architecture.md) — mapa del pipeline completo (grafo de decisión, gates, agentes conectados)
- [docs/cost_model.md](docs/cost_model.md) — costos de bróker por símbolo (borrador, sin confirmar)
- [docs/universe.md](docs/universe.md) — catálogo de símbolos disponibles
- [docs/hypotheses/_registry.md](docs/hypotheses/_registry.md) — registro de todas las hipótesis probadas
- `docs/` — filosofía, hipótesis (`docs/hypotheses/`), specs (`docs/specs/`), fuentes, incidentes
- `data/` — series históricas (no se versionan archivos grandes, ver `.gitignore`)
- `reports/` — resultados de backtest, AED, chequeos de calidad de datos, veredictos de robustez
- `strategies/` — código final validado (Python primero; MQL5/PineScript solo si se pide)
- `.claude/skills/` — scripts y protocolos reutilizables (`data-quality-check` ya definido; backtest/AED pendientes)

## Estado del proyecto
Ver [PROJECT_STATE.md](PROJECT_STATE.md) antes de asumir nada. Actualizarlo tras cada avance real, no al final de cada mensaje.
