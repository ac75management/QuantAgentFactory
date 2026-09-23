# Biblioteca de autores / fuentes de hipótesis — QuantAgentFactory

Catálogo vivo de dónde `investigator` puede buscar lógica de comportamiento documentada. Organizado por categoría, no por orden de llegada — se actualiza según lo que vayamos validando o descartando.

Distinción clave: no todos los autores dan lo mismo. Unos proponen **hipótesis de mercado** (categoría A); otros proponen **método de validación** (categoría B) y no deberían tratarse como fuente de ideas de entrada/salida.

## Categoría A — Fuente de hipótesis (patrones/ineficiencias a probar)

| Autor | Especialidad | Aporta a investigator | Valoración |
|---|---|---|---|
| Perry Kaufman | Modelos adaptativos (KAMA), diseño de sistemas | Punto de partida del video fuente original | Ejemplo ilustrativo, no agotado. Buen anclaje para breakout adaptativo en diario/4H. |
| Linda Raschke | Reversión a la media, dinámicas de volatilidad | Ejemplo ilustrativo original | Útil para hipótesis de reversión de corto plazo dentro de nuestro filtro de frecuencia. |
| Larry Williams | Volatility breakouts, estacionalidad, intermercado | Expansión de rango, sesgos por día/fecha del mes | Encaja bien: patrones mecánicos y verificables en diario/4H. **Riesgo**: parte de su material depende de datos COT (Commitment of Traders) — confirmar acceso antes de tratar una hipótesis suya como lista para AED. |
| Ernest P. Chan | Arbitraje estadístico, cointegración, reversión a la media cuantitativa | Pares de activos, filtros de Kalman | El más riguroso matemáticamente de los cinco nuevos. Encaja con CFDs correlacionados (oro vs. mineras, índice vs. sector). Más esfuerzo de implementación en `engine` (cointegración, no solo indicadores), pero mayor calidad de hipótesis resultante. |
| Thomas Bulkowski | Estadística de patrones de precio (figuras técnicas) | Tasas de éxito/fallo documentadas de patrones | El más débil de los cinco en rigor estadístico moderno — sus tasas vienen de datos históricos de acciones de EE.UU., no necesariamente transferibles a CFDs/futuros actuales. Ninguna hipótesis suya se trata como "ya validada" solo por venir de su libro — pasa por el mismo Gate de AED que cualquier otra. |
| Kevin Davey | Desarrollo algorítmico en futuros, walk-forward + Montecarlo + incubación | Verificado real (libro "Building Winning Algorithmic Trading Systems", Wiley) — su propio método ya coincide con el nuestro (walk-forward, Montecarlo, incubación antes de vivo) |
| Toby Crabel | Opening Range Breakout, patrones de precio de corto plazo | Verificado real (libro "Day Trading with Short Term Price Patterns and Opening Range Breakout", 1990) — clásico de culto sobre ORB, encaja con futuros/CFD diario-4H |
| Andrea Unger | Tendencia y reversión en futuros, 4x campeón mundial de trading | No verificado individualmente todavía (mencionado por una fuente externa, no confirmado con búsqueda propia) — tratar con la misma cautela que cualquier fuente no verificada hasta que se confirme |
| Momentum de series temporales (Moskowitz, Ooi, Pedersen) | Momentum documentado en 58 futuros líquidos multi-activo | Verificado real: paper "Time Series Momentum", Journal of Financial Economics 2012 — muy relevante para el objetivo de varias estrategias en distintos activos |
| Larry Connors (con Cesar Alvarez) | Reversión a la media de corto plazo vía osciladores (RSI(2), ConnorsRSI, IBS-adyacente), filtro de tendencia SMA200 | Verificado real: *Short Term Trading Strategies That Work* (2008), *High Probability ETF Trading* (2009), *An Introduction to ConnorsRSI* (2012) — ya citado como fuente de la hipótesis 001, formalizado aquí. Base de la familia `oscillator_reversion` en `qaf/signals.py`. **Reserva**: su validación original usa salida por SMA5 sin stop fijo; este proyecto siempre aplica SL/TP por ATR (regla de motor, no específica de familia) — la implementación es un híbrido, no una réplica exacta. |

## Categoría B — Metodología de validación (no dan hipótesis, dan rigor)

| Autor | Especialidad | Aporta a validator | Valoración |
|---|---|---|---|
| Marcos López de Prado | ML financiero, validación institucional | Deflated Sharpe Ratio, Purged Cross-Validation | No es fuente de hipótesis — es insumo directo para `validator`. Su Purged CV es especialmente relevante ahora que separamos físicamente IS/OOS: evita fuga de información en validaciones con múltiples cortes. |
| Robert Pardo | Backtesting, robustez, arquitectura de pruebas | Criterios formales de Walk-Forward y degradación de estrategia | Igual que López de Prado: insumo para `validator`, no para `investigator`. Encaja directo con la fase 7 (robustez) ya definida en el pipeline. |
| David Aronson | Anti-sobreajuste, sesgo de minería de datos, validación con método científico | Verificado real (libro "Evidence-Based Technical Analysis", Wiley) — recomienda reglas simples y robustas, walk-forward, y corrección por comparaciones múltiples (conecta directo con el registro de hipótesis, regla 22 de CLAUDE.md) |
| Robert Carver | "Systematic Trading" — framework práctico de sizing y combinación multi-activo | No verificado individualmente todavía (mencionado por una fuente externa) — muy relevante en teoría para el objetivo de portafolio multi-estrategia, pendiente de confirmar con búsqueda propia |

## Por qué separar A y B
Mezclar los cinco autores nuevos en una sola lista sin esta distinción haría que `investigator` intentara "sacar una hipótesis" de un libro que en realidad es un manual de validación. López de Prado y Pardo no proponen qué comprar o vender — proponen cómo comprobar que cualquier estrategia (de cualquier autor) no está sobreajustada.

## Pendiente
- Confirmar si hay acceso a datos COT (necesarios para algunas ideas de Larry Williams).
- Ya preguntado y resuelto en docs/archive/reviews/review_round2.md, docs/archive/reviews/review_round3.md y esta misma tabla: separación A/B confirmada correcta, autores nuevos ya incorporados arriba.
