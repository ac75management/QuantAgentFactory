# QuantAgentFactory — Revisión exhaustiva (ronda 2)

Documento autocontenido, para pegar en cualquier IA con capacidad de razonamiento (Gemini, ChatGPT, etc.) junto con el prompt de instrucciones que acompaña este archivo. Segunda ronda de revisión externa (la primera ya cubrió arquitectura general y quedó en buen estado). Esta ronda pide profundidad en dos áreas concretas: extracción/purificación de datos, y la biblioteca de autores. Cierra con preguntas de fallas/recomendaciones generales.

## Contexto rápido (si no tienes la ronda anterior)
Sistema de agentes (Claude Code) para investigar, validar y aprobar estrategias de trading cuantitativo — método TIS (hipótesis → dato limpio → reglas → backtest → robustez → veredicto). 4 agentes (investigator, protocol, engine, validator) que se comunican solo por archivo, gobernados por reglas duras en un CLAUDE.md. Alcance: CFDs (índices, forex, materias primas) + futuros, diario o 4H mínimo, sin scalping/HFT/rebalanceo — para que el costo de bróker sea margen operativo y no causa de pérdida. Filosofía: la IA ejecuta código determinista ("obrero"), no inventa estrategias por intuición ("pensador"). Nada de esto ha corrido con una hipótesis real todavía — es diseño, no resultado.

Restricción real del operador: no hay acceso a proveedores de datos institucionales de pago (tipo Norgate). Los datos disponibles salen de un bróker de ejecución de baja/media frecuencia (probablemente MetaTrader 5 — sin confirmar todavía), no de un proveedor de datos dedicado.

## Área 1 — Extracción y purificación de datos (pedimos análisis exhaustivo aquí)

Por qué importa más de lo normal: sin proveedor de datos dedicado, la calidad de los datos depende enteramente de cómo se extraen y limpian los datos del propio bróker — no es un paso trivial de "descargar un CSV ya ajustado", hay que construirlo.

Proceso propuesto (a evaluar con lupa):
1. **Extracción**: exportar histórico directo del terminal del bróker (ej. MT5: historial de centro de datos, o vía API/paquete Python del bróker) a CSV/parquet, por activo y timeframe.
2. **Normalización**: unificar formato (timestamp, OHLC, volumen) y zona horaria entre activos y entre broker/fuente, antes de que cualquier agente los toque.
3. **Gate 0 — calidad de datos** (ya definido como skill del agente `engine`): huecos temporales, duplicados, outliers no explicados, ajustes de rollover en futuros, consistencia de zona horaria, cobertura de régimen de mercado (alta/baja volatilidad, tendencia/rango).
4. **Comparación cruzada**: cuando sea posible, contrastar una muestra corta contra una segunda fuente (ej. Yahoo Finance ajustado u otro bróker) para detectar sesgos sistemáticos propios de la fuente de origen (spread variable, feed distinto en fin de semana/rollover).
5. **Separación física IS/OOS**: el archivo se corta 70/30 en el momento de la extracción, no en tiempo de ejecución del backtest — el agente que desarrolla la estrategia nunca ve ni toca el archivo OOS; solo el agente validador lo usa, al final.
6. **Versionado**: cada dataset limpio queda fechado con su propio reporte de calidad asociado, para poder auditar después con qué datos se probó cada estrategia.

Preguntas específicas para esta área:
- ¿Es razonable depender de datos exportados de un bróker de ejecución minorista (no un proveedor de datos dedicado) para investigación cuantitativa seria? ¿Qué sesgos típicos introduce eso que el checklist de arriba no está capturando?
- ¿Qué validaciones adicionales son estándar en la industria para datos de bróker minorista (spread histórico no fiable, gaps de fin de semana, requotes, diferencias entre precio bid/ask reportado) que no estén ya cubiertas?
- El objetivo final es operar **múltiples estrategias en distintos activos** (no una sola). ¿El proceso descrito escala bien a eso, o falta un paso de normalización cruzada entre activos que no está contemplado?

## Área 2 — Biblioteca de autores / fuentes de hipótesis

El operador quiere ampliar la fuente de hipótesis más allá de los dos autores originales (Kaufman, Raschke) con cinco autores adicionales, pero sin que `investigator` termine con una lista plana sin criterio. Propuesta de clasificación en dos categorías — pedimos que la revisen y la corrijan si hace falta:

**Categoría A — dan hipótesis de mercado** (para `investigator`):
| Autor | Especialidad | Nuestra valoración |
|---|---|---|
| Perry Kaufman | Modelos adaptativos (KAMA) | Ejemplo original, sigue siendo válido para breakout adaptativo diario/4H |
| Linda Raschke | Reversión a la media, volatilidad | Válido para reversión de corto plazo dentro de nuestro filtro de frecuencia |
| Larry Williams | Volatility breakouts, estacionalidad, intermercado | Buen encaje; depende de datos COT que aún no confirmamos tener |
| Ernest P. Chan | Arbitraje estadístico, cointegración, Kalman | El más riguroso de los nuevos; encaja con pares de CFDs correlacionados; más esfuerzo de implementación |
| Thomas Bulkowski | Estadística empírica de patrones de precio | El más débil en rigor moderno — tasas de éxito de acciones de EE.UU., no necesariamente transferibles; no se trata como pre-validado |

**Categoría B — dan metodología de validación, no hipótesis** (para `validator`):
| Autor | Especialidad | Nuestra valoración |
|---|---|---|
| Marcos López de Prado | ML financiero, validación institucional | Deflated Sharpe Ratio y Purged Cross-Validation van directo al proceso de robustez, no a la biblioteca de hipótesis |
| Robert Pardo | Backtesting y robustez | Walk-Forward formal y degradación de estrategia, insumo directo para `validator` |

Preguntas específicas para esta área:
- ¿La separación en categoría A (hipótesis) vs. categoría B (validación) es correcta, o alguno de los cinco encaja mejor en la otra categoría?
- ¿Falta algún autor/enfoque relevante para CFDs/futuros en diario-4H, con foco en ineficiencias documentadas y no en indicadores genéricos?
- Danos tu propia clasificación/orden de estos siete autores (los 2 originales + los 5 nuevos) según utilidad para este sistema específico — no en abstracto.

## Preguntas generales de cierre (fallas y recomendaciones)
1. ¿Hay alguna falla de diseño en cómo está planteado el proceso completo (no solo estas dos áreas) que veas desde afuera?
2. Dado que el objetivo final es tener **varias estrategias colaborando en distintos activos** (no solo una), ¿el pipeline actual —una hipótesis a la vez, de principio a fin, por los 4 agentes— es la base correcta para eso, o hace falta pensar ya en algo a nivel de portafolio?
3. ¿Alguna recomendación que no hayamos pedido pero que consideres importante para este proyecto específico?
