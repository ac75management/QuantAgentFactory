---
name: data-quality-check
description: Gate 0 obligatorio. Evalúa calidad de datos históricos de broker minorista (CFD/futuros) antes de cualquier AED o backtest. Úsalo solo desde el agente engine, sobre archivos en data/. Produce reports/<slug>/data_quality.md con veredicto APTO | APTO_CON_RESERVAS | RECHAZADO.
---

# Gate 0 — Calidad de datos (broker minorista)

## Cuándo correr
Antes de cualquier cálculo estadístico, indicador o backtest, sobre el archivo IS ya separado. `qaf.data.inspect_frame` produce `PASS`, `RESERVE` o `FAIL`. `FAIL` bloquea siempre. `RESERVE` permite investigación IS con las reservas visibles, pero nunca habilita aprobación final ni apertura de OOS.

**Implementación vigente.** `qaf/data.py::inspect_frame` ejecuta los controles automatizados como parte de `qaf.cli run`. El resultado por check dentro de `result.json` y `report.html` es la evidencia autoritativa. `config/instruments.json` es la única fuente contractual de instrumento y costos; `docs/cost_model.md` es documentación humana y no puede contradecirla. Las secciones B (clasificación causal de gaps), E (costos históricos), G, H y J no están automatizadas: deben quedar como reservas, nunca como `PASS` narrativo.

## Entrada
- Ruta(s) a serie(s) OHLC (CSV/parquet) del activo y timeframe de la spec.
- Contrato exacto del símbolo en `config/instruments.json`.
- Entrada exacta `symbol+timeframe` del `data/clean/manifest.json` y presencia física de IS/OOS.
- Spec registrada en `config/strategies/`.

## Checklist obligatorio (todos los puntos)

### A. Integridad estructural
1. Columnas mínimas: timestamp, open, high, low, close. Volumen/tick_volume si existe.
2. Tipos correctos; sin NaN en OHLC.
3. Timestamp único, ordenado ascendente, sin duplicados.
4. Timezone explícita (ideal UTC). Si el broker usa server time (p.ej. GMT+2/+3 con DST), documentarlo y convertir a UTC de forma reproducible.
5. Frecuencia real de barras coincide con la declarada (diario o 4H). Medir mediana y percentil de gaps entre barras.

Un resultado `PASS` solo puede usarse cuando el check fue ejecutado sobre el
archivo inspeccionado. Si el control requiere revisión manual, debe figurar
como `MANUAL_PENDIENTE` o `RESERVA`; nunca como `PASS` narrativo.

### B. Gaps y agujeros
Clasificar cada gap > 1.5x el intervalo esperado:
- **Esperado**: fin de semana, festivo del mercado subyacente, rollover de futuro.
- **Feed hole**: pérdida de ticks / hueco no explicado por calendario.
- **Ajuste**: gap de dividendo / corporate action / cambio de contrato.
Regla: más de 0 feed holes materiales en la ventana IS → RECHAZADO (o APTO_CON_RESERVAS solo si son menos del 0.1% de las barras y están marcados para exclusión).

### C. Outliers y consistencia OHLC
- high >= max(open, close) y low <= min(open, close) en todas las barras.
- Barras con rango (high-low) mayor a N desviaciones del rango típico del régimen: listar y justificar (noticia, gap de apertura) o marcar sospechosas.
- No interpolar precios. Si hay que excluir barras, documentar índices exactos.

### D. Precio reportado (bid / ask / mid)
- Declarar qué representa el OHLC exportado del broker (bid, ask, mid, o desconocido).
- Si es desconocido → APTO_CON_RESERVAS obligatorio y nota en el reporte.
- No asumir mid si no está documentado.

### E. Spread y costos (microestructura)
- **Declaración obligatoria en todo reporte**: el spread histórico no viene incluido en OHLC. El backtest usa `spread_points`, `slippage_points_per_side`, comisión y swap de `config/instruments.json`; nunca asume spread cero ni lo infiere de high-low.
- `costs_verified=false` implica `RESERVE` y bloquea aprobación final. `true` solo confirma que el contrato vigente fue verificado; no convierte costos constantes en una reconstrucción histórica.
- Si hay histórico de spread o bid/ask real: estadísticos (mediana, p90, p99) en sesión normal vs. rollover/noticias.
- Verificar que el cost model incluye: spread + comisión + slippage estimado + swap/financing (CFDs). Si falta financing y el holding esperado es mayor a 1 día → RESERVAS.

### F. Sesión y alineación temporal
- Definir sesión de trading usada (RTH del subyacente vs. 24h del CFD).
- Barras de apertura/cierre deben alinearse con esa sesión.
- Excluir por defecto: 00:00-01:00 GMT y los últimos 15 minutos del viernes, por ensanchamiento de spread documentado.
- Para multi-activo (si aplica): misma timeline UTC y matriz de disponibilidad; rechazar pares con desalineación sistemática.

### G. Rollover / continuidad (futuros y CFDs sobre futuro)
- Si el símbolo es continuo: documentar método de ajuste (back-adjusted, ratio, none).
- Gaps de rollover deben estar clasificados y no tratarse como señales.
- Comparar una muestra corta vs. segunda fuente (Yahoo u otro broker) si está disponible; divergencias sistemáticas → RESERVAS o RECHAZADO.

### H. Cobertura de régimen
- La ventana IS debe contener al menos un tramo de alta volatilidad y uno de baja (o documentar que no).
- Cobertura mínima de calendario: no validar estrategias de estacionalidad con menos de 3 ciclos del fenómeno.

### I. Separación IS/OOS
- Confirmar que existen archivos o slices distintos para IS y OOS según la spec (70/30 por defecto) — creados por engine en su paso de división física, antes de este Gate.
- Este skill NO crea la separación, solo la verifica. Engine en los pasos posteriores solo debe leer IS. OOS queda exclusivamente para validator.
- Registrar hashes o fechas de los archivos usados en el reporte.

### J. As-of / estabilidad del histórico
- Cuando sea posible: re-descargar el mismo rango en otra fecha y medir divergencia de closes.
- Divergencia material → el feed se reescribe; marcar RESERVAS y no tratar el backtest como reproducible a largo plazo.
- Si no es posible re-descargar en esta pasada, documentarlo como limitación pendiente, no como fallo.

## Veredicto
- **APTO / `PASS`**: todos los checks automatizados críticos pasan y los campos `price_basis`, `calendar_verified`, `provenance_verified` y `costs_verified` del contrato permiten esa conclusión.
- **APTO_CON_RESERVAS / `RESERVE`**: usable para exploración IS, con cada reserva visible. No requiere confirmación conversacional para calcular IS; nunca autoriza OOS, aprobación o trading.
- **RECHAZADO**: integridad rota, feed holes materiales, OHLC inconsistente, o imposibilidad de definir sesión/costos de forma defendible.

## Salida obligatoria
Artefactos `reports/factory/runs/<run_id>/result.json` y `report.html` con:
1. Símbolo, timeframe, rutas de archivos, hashes/fechas.
2. Tabla check → resultado (PASS / RESERVA / FAIL) + evidencia breve.
3. Lista de barras excluidas (si las hay) con motivo.
4. Declaración bid/ask/mid y fuente del cost model.
5. Estado final mapeado: `PASS | RESERVE | FAIL` (`APTO | APTO_CON_RESERVAS | RECHAZADO` en presentación humana).
6. Bloque "Limitaciones conocidas" que validator debe leer.

## Prohibiciones
- No rellenar huecos con interpolación lineal ni forward-fill de precios.
- No "arreglar" outliers borrándolos en silencio.
- No declarar APTO si el spread/financing no está modelado y el holding es mayor a 1 día.
- No continuar a AED/backtest si el VEREDICTO es RECHAZADO.
