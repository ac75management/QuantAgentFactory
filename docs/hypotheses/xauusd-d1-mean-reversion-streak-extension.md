# Hipótesis 001 — Reversión de corto plazo en XAUUSD (D1) tras extensión direccional de 3+ días consecutivos

## Estado
Pendiente — recién formalizada por `investigator`. Va a `protocol` para traducirla en reglas numéricas. No se ha corrido AED ni backtest. Ningún archivo de precio (IS ni OOS) fue tocado para escribir este documento.

## Fuente / inspiración
No proviene de un único autor/libro citado textualmente. Es una síntesis de dos cosas:

1. **Decisión de proyecto (2026-09-22)**: el dry-run de buy&hold en XAUUSD D1 (`reports/dryrun_costs_comparativa.md`) mostró que el holding largo es inviable en este bróker — bruto +103,902, swap acumulado -317,632.40, neto **-213,786.95** (el más caro de los tres símbolos probados). Alexander autorizó pivotar a hipótesis de holding corto (días, no años) para este símbolo. Documentado en `PROJECT_STATE.md`.
2. **Cuerpo de literatura cuantitativa real sobre "short-term return reversal" / overreaction**, verificado abajo con búsquedas independientes — no se acepta como intuición sin respaldo.

Dentro de `docs/author_library.md` (categoría A), Linda Raschke (reversión a la media, dinámicas de volatilidad) es el ejemplo ilustrativo más cercano en filosofía general, pero no tengo una fuente primaria verificada de una regla textual suya para este patrón específico — no se le atribuye directamente, se cita solo como anclaje de la línea metodológica del proyecto.

Nivel de taxonomía (`docs/taxonomy.md`): la lógica central (overreaction / reversión tras extensión) se apoya en fuentes de nivel 4-5 (papers académicos revisados por pares). Parte de la evidencia complementaria (comentario de mesa de commodities sobre flujo CTA, foros de trading sobre "días de tendencia" en oro) es de nivel 2-3 y se trata como color de contexto, nunca como prueba — señalado explícitamente en cada caso abajo.

## Mercado / activo / timeframe propuesto
- **XAUUSD** (CFD metal, Darwinex vía MT5), **D1**.
- Verificado en `docs/universe.md` fila 7: `alias=XAUUSD`, `symbol_mt5=XAUUSD`, `type=cfd_metal`, `tfs=D1,H4`, `status=active`. D1 es un timeframe válido para este símbolo.
- No se extiende automáticamente a H4 ni a otros símbolos (XAGUSD, por ejemplo, comparte `cost_key=metal` pero no se incluye aquí) — cualquier extensión se registraría como hipótesis separada.

## Lógica de comportamiento
XAUUSD vía CFD retail atrae un flujo dominado por momentum de corto plazo: CTAs sistemáticos, retail apalancado siguiendo tendencia, y algos de seguimiento de tendencia que construyen posición de forma incremental mientras la señal técnica se mantiene (medias móviles, breakouts de rango). Cuando el precio se mueve 3+ sesiones diarias seguidas en la misma dirección, ese flujo tiende a sobre-extender el movimiento más allá del ajuste "justo" a la información nueva disponible — no porque haya nueva información fundamental cada día, sino porque el propio flujo de persecución de tendencia empuja el precio de forma mecánica.

La reversión llegaría cuando:
- Las posiciones de corto plazo (retail, CTAs de reacción rápida) se cierran por toma de ganancias tras varios días de movimiento a favor.
- Se dispara ajuste de margen / reducción de tamaño en cuentas apalancadas que operaron en contra del extremo del movimiento.
- El flujo de nueva persecución de tendencia se agota (ya no queda "combustible" de compradores/vendedores tardíos) mientras el flujo contrario (fade) empieza a pesar más.

Esto generaría un retroceso mecánico de pocos días, no una reversión de tendencia de fondo. Holding esperado: 2-5 sesiones D1. Dirección: contraria al movimiento extendido (mean reversion).

## Clase de participante que genera el edge (y quién está del otro lado)
- **Genera la sobre-extensión (el lado "equivocado" del trade en el corto plazo)**: retail apalancado en CFD siguiendo tendencia, CTAs/algos de trend-following sistemático que no distinguen entre "tendencia con motivo fundamental nuevo" y "tendencia por inercia de flujo", y traders que persiguen el movimiento tarde (FOMO).
- **Se beneficiaría de la reversión (el lado hipotético del trade)**: participantes de reversión a la media de corto plazo — desde mesas de bancos que ejecutan fade sistemático de extensiones, hasta la propia estrategia que se probaría aquí. No se afirma que esto sea rentable, solo se identifica la estructura de flujo hipotética.

## Horizonte de holding esperado
2-5 sesiones D1. Esto no es arbitrario: es la razón de ser de esta hipótesis frente al buy&hold ya descartado. XAUUSD es, según `docs/cost_model.md` (sección LIVE, snapshot `docs/cost_snapshots/20260922_1122.json`), el símbolo con mayor swap absoluto del universo (`swap_long=-62.6`, `swap_short=35.4` por lote). Un holding de días, no meses/años, es la única forma de que el costo de mantenimiento no domine la expectativa bruta, como sí ocurrió en el dry-run de buy&hold.

**Caveat relevante para `protocol`/`engine` (no es una regla, es una observación de costos)**: el swap de XAUUSD es asimétrico — negativo en largo, positivo en corto. Como esta hipótesis opera en ambas direcciones (short tras extensión alcista, long tras extensión bajista), el costo de mantenimiento neto no será simétrico entre los dos casos. Esto debe modelarse explícitamente, no promediarse.

## Evidencia de literatura

**A favor / contexto de apoyo:**

1. **Wang, C. & Yu, M. (2004), "Trading Activity and Price Reversals in Futures Markets," Journal of Banking & Finance.** Validado originalmente en: 24 futuros de EE.UU. (divisas, financieros, agrícolas, materias primas), horizonte semanal, 1983-2000 (según resumen de terceros). Encuentra evidencia fuerte de reversión semanal y sobre-reacción en mercados de futuros, con la ganancia de la estrategia contraria asociada positivamente a volumen y negativamente a interés abierto. Es la fuente más cercana en clase de activo (futuros multi-activo incluyendo materias primas) pero el horizonte es semanal, no un conteo de racha diaria de 3+ sesiones — no es una réplica directa.
2. **Quantpedia, resumen agregador de "Short-Term Reversal with Futures"** (basado en literatura académica de reversión semanal contraria, 24 futuros de EE.UU., 1983-2000). Fuente secundaria, no primaria — útil como verificación cruzada accesible del mismo efecto de Wang & Yu, no se trata como evidencia independiente adicional.
3. **Parikakis & Syriopoulos (2008), "Contrarian strategy and overreaction in foreign exchange markets," Review of International Business and Finance.** Validado en: pares EUR/USD, 1999-2007. Concluye que el USD tiende a sobre-reaccionar y que estrategias contrarias son rentables en FX. Relevante porque XAUUSD se cotiza y opera de forma muy similar a un cruce de USD en plataformas retail — más cercano en mecánica de mercado que en clase de activo estricta.
4. **Rentzler et al. (2006)** (citado en revisiones de literatura de overreaction en FX) — reversión intradía en cinco futuros de divisas, 1988-2003, tras retornos grandes de un día y gaps de apertura. Mecánica análoga (movimiento grande → reversión) pero horizonte intradía, por debajo de nuestro piso de 4H/D1 — se cita solo como analogía conceptual, no como soporte directo de la regla.
5. **Jegadeesh, N. (1990), "Evidence of Predictable Behavior of Security Returns," Journal of Finance; Lehmann, B. (1990), "Fads, Martingales, and Market Efficiency," Quarterly Journal of Economics.** Ambos son el origen académico clásico de la reversión de corto plazo (semanal) documentada — validados en **acciones individuales de EE.UU.**, no en futuros/CFD ni en materias primas. Clase de activo distinta a nuestro alcance — se citan como fundamento histórico del efecto "overreaction reversal", con extrapolación de riesgo declarada explícitamente.
6. **Bianchi, R.J., Drew, M.E., Fan, J.H. (2015), "Combining Momentum with Reversal in Commodity Futures," Journal of Banking & Finance.** Validado en futuros de materias primas (misma clase de activo que nos interesa), pero el patrón de reversión que documentan aparece **12-30 meses** después de la formación del momentum, no en 2-5 días. Mismo activo, horizonte completamente distinto — se cita solo como evidencia de que existen efectos de reversión en materias primas en general, no como soporte del mecanismo de racha corta.
7. **Larry Williams / Larry Connors & Cesar Alvarez, "Short Term Trading Strategies That Work" (2004)** — patrones de reversión tras rachas de precio (ej. RSI-2), mismo mecanismo estructural (racha → reversión) que se propone aquí. Validado mayormente en **acciones/ETFs de EE.UU.**, con holding originalmente de 1-3 días. Libro de práctica cuantitativa (nivel 3-4 de taxonomía), sin réplica académica independiente citada aquí — se trata como sugerente, no concluyente.

**Evidencia de contexto sobre el mecanismo específico de flujo (no académica, nivel 3-4 de taxonomía, tratar como color, no prueba):**

8. Cobertura de mesa de commodities (comentario de TD Securities/Bank of America sobre posicionamiento CTA en oro, 2026) describe explícitamente episodios de "selling exhaustion" en oro cuando la presión de venta de CTAs se agota tras una extensión — consistente con el mecanismo propuesto (flujo sistemático que se agota y revierte), pero es comentario de mercado, no investigación revisada por pares.

**En contra / caveat de riesgo (nivel 2-3, fuente retail, tratar con escepticismo):**

9. Fuentes retail sobre trading de oro (ej. "Pro-Scalper", material educativo no verificado independientemente) afirman que aproximadamente 20-25% de las sesiones en XAUUSD son "días de tendencia fuerte" donde los intentos de reversión a la media fallan repetidamente. No es una fuente rigurosa, pero señala un riesgo operativo real que el AED debe verificar: la hipótesis puede tener un régimen de fallo sistemático (tendencias fuertes prolongadas, ej. 2020, 2024-2025) que una racha de solo 3 días no captura bien.

## Por qué el edge no se ha comprimido del todo
- **Restricción institucional, no arbitraje puro**: los CTAs de seguimiento de tendencia no "arbitran" su propia sobre-extensión — es estructural a su mandato (siguen la señal, no operan en contra de ella). No hay un mecanismo natural por el cual el mismo flujo que genera el patrón lo elimine.
- **El flujo que genera la ineficiencia se renueva constantemente**: nuevo capital retail apalancado y nuevas señales sistemáticas de trend-following entran cada día — no es una anomalía que se "gaste" una vez explotada, si existe, se regenera con cada racha nueva.
- **Desajuste de horizonte con los arbitrajistas más agresivos**: la reversión intradía (Rentzler et al.) es terreno de HFT y market makers, ya muy competido. La reversión de 12-30 meses en materias primas (Bianchi et al.) es terreno de fondos sistemáticos institucionales grandes. El hueco de 2-5 días en un CFD retail de oro es menos atractivo en capacidad para fondos grandes (demasiado pequeño, demasiado ruidoso frente a la curva de futuros de COMEX) y demasiado lento para HFT — posible "tierra de nadie" de horizonte, sin que esto se afirme como hecho probado.
- **Costos de bróker como fricción real, no eliminados**: `docs/cost_model.md` marca swap y comisión de `metal` como `SIN_CONFIRMAR` en varias filas — el ratio de fricción (regla 17 de CLAUDE.md) no se puede evaluar todavía con precisión. Esto no invalida la hipótesis, pero significa que `protocol`/`engine` no pueden aprobar una spec sobre este símbolo hasta que esos campos se confirmen.

## Por qué sigue siendo explotable (especulación declarada, no hecho establecido)
Esto es una hipótesis a probar, no una afirmación de rentabilidad. La combinación de (a) evidencia académica real de reversión de corto plazo en futuros multi-activo (Wang & Yu 2004) y en FX (Parikakis & Syriopoulos 2008), (b) mecánica de flujo CTA descrita en comentario de mesa de commodities, y (c) el mismo patrón estructural (racha → reversión) documentado en acciones (Jegadeesh 1990, Lehmann 1990, Connors) sugiere que el efecto general "overreaction reversal" es real en múltiples clases de activo y horizontes cercanos al propuesto. Ninguna fuente encontrada estudia exactamente "racha de 3+ días en XAUUSD CFD D1, reversión de 2-5 días" — es una síntesis, no una réplica directa, y así se declara.

## Caveats y riesgos (explícitos)
- **Riesgo de extrapolación de clase de activo/horizonte**: ninguna fuente citada valida exactamente esta combinación (oro, CFD retail, D1, racha de 3+ días, holding 2-5 días). Las fuentes más cercanas difieren en clase de activo (acciones: Jegadeesh, Lehmann, Connors), horizonte (semanal: Wang & Yu; intradía: Rentzler; 12-30 meses: Bianchi et al.), o tipo de instrumento (FX spot: Parikakis & Syriopoulos, vs. CFD sobre metal). Tratar como hipótesis de síntesis, no como réplica de un estudio existente.
- **Riesgo de régimen de tendencia fuerte**: fuente retail (caveat, no probada) sugiere que una fracción no trivial de sesiones en XAUUSD son días de tendencia donde la reversión de corto plazo falla repetidamente. El AED (fase 2) debe medir esto explícitamente, no asumir que el patrón es estable en todos los regímenes.
- **Asimetría de swap**: ver sección "Horizonte de holding esperado" — el costo de mantenimiento no es simétrico entre la rama larga y la corta de esta hipótesis.
- **Costos sin confirmar**: `cost_key=metal` en `docs/cost_model.md` tiene varios campos en `SIN_CONFIRMAR` (spread, swap materiales, commission). No bloquea escribir la hipótesis (no depende de datos no disponibles como COT u order flow — solo necesita OHLC D1, que sí está disponible), pero sí bloqueará el paso a `protocol`/`engine` hasta confirmarse, por la regla 17 de CLAUDE.md.
- **Primera hipótesis del proyecto**: `docs/hypotheses/_registry.md` estaba vacío antes de esta entrada (N=0 → N=1). No hay hipótesis previa semánticamente equivalente que declarar como vínculo/re-test.

## Qué no es esta hipótesis
- No es una regla de trading. No hay umbral numérico de qué cuenta como "3+ días" (¿close a close? ¿qué mínimo de rango?), ni definición de stop-loss, take-profit, ni tamaño de posición. Eso lo define `protocol`.
- No es una afirmación de que el patrón sea rentable. Es una hipótesis a validar mediante AED (fase 2 del método TIS) antes de escribir cualquier regla.
- No se ha tocado ningún dato de precio (IS ni OOS) para escribir este documento.
