# Media móvil con banda porcentual

Estado: **pendiente de protocolo**. Esta ficha registra una hipótesis investigable; no afirma rentabilidad y no contiene resultados de backtest.

## Trazabilidad

- Hipótesis: `008`
- Candidato: `IDEA-PILOT-MABAND-EUR-H4`
- Fuente primaria: [Trading Systems and Methods, 5th Edition](https://onlinelibrary.wiley.com/doi/book/10.1002/9781119202561)
- Autores: Perry J. Kaufman
- Mercado y vehículo originales: Sistemas de trading probados originalmente sobre futuros de materias primas y forex, de forma genérica y multi-activo (el libro no ata esta técnica específica a un símbolo único) / Futuros y forex, contratos continuos / spot institucional — no CFD retail
- Objetivo QAF: EURUSD / H4
- Tratamiento: adaptation
- Regla fuente: `kaufman-ma-percentage-band-breakout`
- Dimensiones adaptadas: costs, frequency, instrument

## Evidencia revisada

Kaufman describe una envolvente de banda porcentual: dos líneas equidistantes (en %) por encima y por debajo de una media móvil suavizada. La entrada clásica que documenta es de RUPTURA/CONTINUACIÓN: cuando el precio penetra la banda superior se abre/rota a largo; cuando penetra la banda inferior se abre/rota a corto (cierre de la posición contraria si existía). El propio Kaufman documenta explícitamente varias variantes de ejecución tras la señal (no una sola regla fija): entrar al cierre de la barra de señal, entrar en la apertura siguiente, retrasar la entrada 1-3 días, esperar un retroceso del 50% tras la señal, o condicionar la entrada a un riesgo máximo relativo a un stop. Esto confirma que el libro no define una única regla canónica de ejecución/salida, sino un menú de variantes — motivo por el que esta revisión no fija ninguna. Fuentes secundarias independientes que describen la misma técnica (sin ser la fuente primaria, usadas solo para corroborar que el mecanismo es real y no una invención): Medium (David Borst, sobre KAMA/ATR de Kaufman), Oxford Capital Strategies (estrategias derivadas de Kaufman), QuantifiedStrategies.com (adaptive moving average / bandas), stockcharts.com/chartschool (KAMA). Ninguna de estas es una cita textual con número de página del libro de 2012.

## Mecanismo propuesto

Hipótesis de comportamiento (no verificada en el texto primario más allá del mecanismo general): una media móvil sola cruza el precio constantemente por ruido de corto plazo, generando señales falsas; exigir que el precio supere la media por un margen porcentual mínimo filtra ese ruido y solo actúa cuando hay suficiente convicción direccional para vencer la volatilidad reciente. El lado contrario del trade lo proveen operadores de reversión a la media / rango que venden fuerza y compran debilidad exactamente en el punto donde el sistema de banda confirma ruptura, y liquidez de contrapartes institucionales (creadores de mercado, coberturas) que absorben el impulso inicial. El edge, si existe, sería la prima de riesgo por asumir el lado de la tendencia confirmada en el momento en que el consenso de corto plazo (reversión) se equivoca.

## Reglas publicadas que deben conservarse

- Construir una media móvil suavizada de período N (no verificado cuál valor exacto usa Kaufman para esta técnica en la edición 2012; fuentes secundarias mencionan 10 como ejemplo pero sin cita primaria, se declara ambiguo).
- Definir una banda porcentual P% por encima y por debajo de esa media (no verificado el valor exacto; fuentes secundarias mencionan 3% como ejemplo sin cita primaria, se declara ambiguo).
- Precio penetra banda superior -> señal larga (cierre de corto si existía, apertura de largo).
- Precio penetra banda inferior -> señal corta (cierre de largo si existía, apertura de corto).
- Kaufman documenta múltiples variantes de ejecución tras la señal (cierre de la barra, apertura siguiente, retraso de 1-3 barras, retroceso del 50%, o condicionado a un stop de riesgo) sin fijar una única regla; ninguna se adopta aquí como definitiva.

## Réplica o adaptación

El candidato ya declaraba el objetivo EURUSD/H4. Se mantiene esa adaptación y se documentan sus tres dimensiones: (1) instrument — el libro describe un sistema genérico multi-activo (futuros y forex en general), no específico a EURUSD; aquí se fija a un solo símbolo. (2) frequency — la fuente se referencia a sistemas diarios (D1); se adapta a H4, un cambio de frecuencia no validado por la fuente. (3) costs — el libro asume costos de futuros/forex institucional; el vehículo real es un CFD retail vía Darwinex/MT5 con spread, comisión, slippage y swap propios, que deben modelarse aparte según config/instruments.json. No se declara adaptación de 'vehicle' como dimensión separada de 'instrument' porque el libro ya cubre forex de forma genérica (no es un salto de clase de activo, sino de generalidad multi-activo a un símbolo puntual).

## Ambigüedades todavía abiertas

- Período exacto de la media móvil: no verificado contra el texto primario (fuentes secundarias sugieren 10, sin cita de página).
- Ancho exacto de la banda porcentual: no verificado contra el texto primario (fuentes secundarias sugieren 3%, sin cita de página).
- Regla de salida/ejecución: Kaufman documenta explícitamente varias variantes (cierre, apertura siguiente, retraso, retroceso del 50%, stop de riesgo) sin fijar una sola; cuál usar queda abierto para `protocol`, dentro de lo que la familia de señal disponible permita expresar.
- No se verificó si esta técnica específica de banda porcentual aparece exactamente igual en la 5ª edición (2012, DOI citado) o si es una descripción heredada de ediciones anteriores del libro bajo el título 'Commodity Trading Systems and Methods'; se asume continuidad editorial pero no se confirmó línea por línea.

## Datos requeridos

- OHLC H4 de EURUSD

## Costos y fricciones que el contrato debe modelar

- Spread, comisión, swap y slippage del CFD EURUSD según config/instruments.json (fuente única de costos); el ejemplo original de Kaufman no modela fricción de CFD retail.

## Límites de la evidencia

- Ningún valor numérico de esta revisión (período de media, % de banda) debe tratarse como dato verificado de la fuente primaria; son referencias de fuentes secundarias sin cita de página, declaradas explícitamente como ambiguas.
- La familia de señal necesaria ('precio cruza una media móvil ± una banda porcentual') no existe hoy en `qaf/contracts.py` (`FAMILIES = {streak_reversal, trend_cross, channel_breakout, oscillator_reversion}`). `trend_cross` exige DOS medias (rápida/lenta) y no expresa una banda porcentual sobre una sola media; ninguna familia actual lo cubre. Esta hipótesis requiere una familia nueva en `qaf/signals.py`, todavía no implementada, antes de que `protocol` pueda traducirla a spec ejecutable.
- Extrapolación de riesgo: la técnica se documenta para sistemas diarios multi-activo institucionales (futuros/forex), no específicamente para EURUSD H4 vía CFD retail; es una adaptación, no una aplicación directa.

## Decisión de la revisión

La fuente primaria (Perry J. Kaufman, 'Trading Systems and Methods', 5ª edición, Wiley, 2012, DOI 10.1002/9781119202561) es real y verificada (confirmado autor, título, editorial, año 2012 y edición 5ª vía WebSearch independiente del registro DOI de Wiley). El texto completo está detrás de suscripción (access_level='subscription' ya declarado en el candidato) y no pude leer el capítulo exacto línea por línea, pero encontré confirmación independiente y consistente, en múltiples fuentes secundarias no afiliadas entre sí, de que Kaufman documenta en sus libros ('Commodity Trading Systems and Methods' y ediciones posteriores bajo el título actual) una técnica de 'moving average with percentage band'/'trading band': dos líneas a una distancia porcentual igual de una media móvil suavizada; el precio penetrando la banda superior dispara entrada larga (o cierre de corto + entrada larga), y penetrando la banda inferior dispara entrada corta (o cierre de largo + entrada corto) — es decir, es una técnica de RUPTURA/CONTINUACIÓN DE TENDENCIA con filtro de ruido (comprar fuerza confirmada, no comprar barato), no de reversión a la media. El mecanismo general (MA + banda porcentual como filtro de ruido para romper solo en dirección confirmada) está bien corroborado como técnica real y documentada de Kaufman por varias fuentes independientes; los valores numéricos exactos (período de la media, ancho de la banda, y cuál de las variantes de salida usa) NO están verificados contra el texto primario y se declaran como ambigüedad explícita — protocol no debe tomar ningún valor numérico de esta revisión como dato de la fuente, solo el mecanismo cualitativo.

Siguiente paso: `protocol` debe convertir esta hipótesis en reglas numéricas congeladas o bloquearla si las ambigüedades impiden una implementación fiel. OOS permanece cerrado.
