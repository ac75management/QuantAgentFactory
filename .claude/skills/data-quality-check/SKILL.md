---
name: data-quality-check
description: Gate 0 obligatorio. Evalúa calidad de datos históricos de broker minorista (CFD/futuros) antes de cualquier AED o backtest. Úsalo solo desde el agente engine, sobre archivos en data/. Produce reports/<slug>/data_quality.md con veredicto APTO | APTO_CON_RESERVAS | RECHAZADO.
---

# Gate 0 — Calidad de datos (broker minorista)

## Cuándo correr
Antes de cualquier cálculo estadístico, indicador o backtest, sobre el archivo IS ya separado. Si el veredicto es RECHAZADO, engine se detiene. Si es APTO_CON_RESERVAS, engine reporta y no avanza sin confirmación explícita de Alexander.

**Nota (2026-09-22): esto ya corre automatizado.** `qaf/data.py::inspect_frame` implementa las secciones A, C, D, F (parcial) y I de este checklist como parte de `qaf.cli run` — su resultado (`PASS`/`RESERVE`/`FAIL` por check, dentro de `result.json`) es la fuente real, no un documento manual aparte en `reports/<slug>/data_quality.md`. El equivalente de `cost_key.status == CONFIRMED` de este documento es el campo `costs_verified` de `config/instruments.json` (hoy `false` para las 10 series activas). Las secciones B (gaps), E (2ª mitad — histórico de spread/slippage), G, H y J de este checklist **no están automatizadas todavía** — siguen siendo trabajo manual de quien corre `engine` hasta que se implementen en `qaf`.

## Entrada
- Ruta(s) a serie(s) OHLC (CSV/parquet) del activo y timeframe de la spec.
- Metadatos del símbolo si existen en `docs/universe.md` (sesión, tipo CFD/futuro, multiplicador, política de rollover).
- Cost model de referencia en `docs/cost_model.md` (si existe).

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
- **Declaración obligatoria en todo reporte**: el spread histórico NO viene incluido en las barras OHLC exportadas del bróker (son solo precio, no bid/ask con profundidad). Todo backtest usa el spread de `docs/cost_model.md`, nunca asume spread cero ni lo infiere de high-low.
- Busca en `docs/universe.md` el `cost_key` del símbolo, y en `docs/cost_model.md` su `status`.
  - `status=CONFIRMED` → el costo es real, no limita el veredicto por este punto.
  - `status=SIN_CONFIRMAR` (o cualquier valor distinto de CONFIRMED) → **el veredicto de este Gate 0 no puede ser mejor que APTO_CON_RESERVAS**, sin importar qué tan limpios estén los precios. No hay excepción: dato limpio con costo desconocido sigue siendo un backtest no confiable.
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
- **APTO**: todos los checks críticos pasan, limitaciones residuales menores documentadas, Y el `cost_key` del símbolo tiene `status=CONFIRMED` en `docs/cost_model.md`.
- **APTO_CON_RESERVAS**: usable solo con confirmación de Alexander; listar cada reserva (spread estático, timezone inferida, sin segunda fuente, `cost_key` sin confirmar, etc.). **Techo obligatorio** mientras el `cost_key` no esté `CONFIRMED` — nunca se declara APTO solo porque los precios están limpios.
- **RECHAZADO**: integridad rota, feed holes materiales, OHLC inconsistente, o imposibilidad de definir sesión/costos de forma defendible.

## Salida obligatoria
Archivo `reports/<slug>/data_quality.md` con:
1. Símbolo, timeframe, rutas de archivos, hashes/fechas.
2. Tabla check → resultado (PASS / RESERVA / FAIL) + evidencia breve.
3. Lista de barras excluidas (si las hay) con motivo.
4. Declaración bid/ask/mid y fuente del cost model.
5. Veredicto final en una línea: `VEREDICTO: APTO | APTO_CON_RESERVAS | RECHAZADO`
6. Bloque "Limitaciones conocidas" que validator debe leer.

## Prohibiciones
- No rellenar huecos con interpolación lineal ni forward-fill de precios.
- No "arreglar" outliers borrándolos en silencio.
- No declarar APTO si el spread/financing no está modelado y el holding es mayor a 1 día.
- No continuar a AED/backtest si el VEREDICTO es RECHAZADO.
