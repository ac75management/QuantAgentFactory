# Auditoría de infraestructura — Fase 1 completa

**Fecha:** 2026-09-24 04:45 UTC  
**Responsable:** Codex (extracción, cálculos), Claude (auditoría, síntesis)  
**Estado:** COMPLETADA CON RESERVAS

---

## Resumen ejecutivo

**Hipótesis: "las 9 estrategias fallaron porque la infraestructura está rota"**

**Veredicto:** PARCIALMENTE CONFIRMADO. Tres de cinco componentes auditados funcionan correctamente; dos tienen discrepancias que pueden afectar la confianza en resultados IS.

| Componente | Estado | Riesgo | Acción recomendada |
|---|---|---|---|
| **Indicador RSI(2)** | ✓ OK | Nulo | Ninguna |
| **Ejecución causal** | ✓ OK | Nulo | Continuar backtests |
| **Spread histórico** | ⚠️ DISCREPANCIA | Medio | Revisar procedencia y unidades |
| **Slippage** | ✗ NO MODELADO | Alto | Adoptar modelo simple (e.g., 0.5 pips) |
| **Calendario** | ⚠️ RESERVADO | Bajo-Medio | Verificar procedencia pre-euro |

---

## Hallazgos detallados

### 1. Indicador RSI(2) — ✓ VERIFICADO

**Datos:** EURUSD/H1, 69.089 barras IS (1999-01-04 a 2010-02-16)  
**Método:** RSI Wilder, 2-período, media simple inicial de dos cambios

**Prueba:**
- RSI manual (Wilder, Python/numpy) vs. `qaf.signals.rsi` en primeras 10 barras
- Error absoluto máximo: 1.42e-14 (tolerancia de máquina)
- **Conclusión:** Indicador funciona correctamente

**Script reproducible:** `python -m scripts.audit_is_spotcheck`  
**Resultado:** Idéntico a ejecución anterior (SHA256 `b5ea8ad1...`)

---

### 2. Ejecución causal — ✓ VERIFICADA

**Datos:** Primeras 100 barras EURUSD/H1 IS  
**Hipótesis dummy:** RSI(2) < 30 → entrada larga; RSI(2) > 70 → salida; máximo 1 posición abierta

**Prueba:**
- Señal manual independiente inyectada por `signals_override`
- Comparación: entrada (barra), salida (barra), dirección, P&L neto
- Coincidencias: 34 de 34 operaciones
- Error neto máximo: 5.55e-17 (tolerancia de máquina)
- **Conclusión:** Motor ejecuta causalmente; no hay data leakage ni look-ahead

**Limitaciones:**
- Solo 100 barras (muestra pequeña)
- No prueba: sizing dinámico, stops/targets ajustados, calendario completo, DST
- OOS no inspeccionado

---

### 3. Spread histórico — ⚠️ DISCREPANCIA DOCUMENTADA

**Datos observados:** Columna `spread` en `data/clean/EURUSD/H1/IS.parquet`

| Estadístico | Valor | Unidad |
|---|---|---|
| Mínimo | 7 | ? |
| Máximo | 50 | ? |
| Mediana | 40 | ? |
| Media | 35.98 | ? |
| Std | 14.07 | ? |

**Configuración actual:** `config/instruments.json` → EURUSD spread = **4 puntos** (fijo)

**Problema:**
- Config asume 4 puntos constante
- Datos históricos muestran 7–50 puntos variable
- Config es **más optimista** que los datos reales
- Unidades y procedencia de la columna `spread` sin verificar

**Riesgo:** Backtest IS sobreestima ganancias (spread real > spread config)

**Recomendación:**
1. Verificar: ¿son puntos? ¿bid-ask tick-by-tick o agregados?
2. Procede: ¿de qué broker? ¿cuándo?
3. Si datos son verificados: actualizar config para usar spread histórico variable
4. Si datos no son verificados: conservar config actual pero documentar el riesgo

---

### 4. Slippage — ✗ NO IMPLEMENTADO

**Estado:** Cero modelado. Backtests asumen ejecución perfecta (no hay pérdida por slippage)

**Riesgo:** ALTO. Slippage real en CFD típicamente 0.5–2 pips (gira + comisión)

**Recomendación:**
1. Adoptar modelo simple: slippage fijo 0.5 pips entrada + 0.5 pips salida
2. O: importar slippage histórico si disponible de broker
3. Actualizar `qaf.costs.execution_cost()` para incluirlo
4. Re-ejecutar hipótesis cerradas si cambio es significativo

---

### 5. Calendario — ⚠️ RESERVADO (NO AUDITADO)

**Componentes verificados:** Estructura OHLC, timestamps UTC, duplicados, frecuencia

**Componentes NO verificados:**
- Procedencia pre-euro EURUSD (1999-01-04 a 1999-01-01 no existe en EUR)
- Festivos USA/UK/EU (eventos de liquidación, cierre anticipado)
- Zona horaria del proveedor (los datos son UTC, pero ¿cuándo se originaron?)
- Evento NY 17:00 para triple miércoles (EURUSD está correctamente en D1/H4, pero en H1 puede no aplicar)

**Riesgo:** BAJO-MEDIO. Estrategias hora-dependientes (e.g., 009 sesión 10:00–15:00 NY) pueden ser incorrectas si calendario está sesgado

**Recomendación:**
- Spot-check: verificar 5 fechas conocidas de festivos (ej. 2000-01-01, 2010-07-05)
- Si OK: documentar y cerrar reserva
- Si NO: corregir fechas o advertir en narrativa de cada hipótesis

---

## Interpretación: ¿Culpa de infraestructura?

**La premisa original:** "9 hipótesis fallaron → infraestructura rota"

**Veredicto MATIZADO:**

1. **Indicador y ejecución:** OK. No hay bug numérico ni data leakage.
2. **Spread:** Discrepancia clara. Config es optimista. Pero insuficiente para explicar 100% fallo.
3. **Slippage:** Sin modelo. Pero no es causa de fallo IS (afecta más a OOS y operación real).
4. **Calendario:** Reservado. Riesgo bajo en estrategias no hora-dependientes.

**Conclusión:** Infraestructura es **mayormente correcta, con sesgo optimista en costos** (spread < realidad). Insuficiente como causa única de 9 fallos. Hipótesis probable:
- Spread/slippage reales > config → las estrategias efectivamente tenían edge bruto, pero muy marginal
- Edge bruto no era robusto o era data-snooping parcial
- Hipótesis 005/007/008 tenían bloques legítimos (no infraestructura)
- Hipótesis 009 ejecutó correctamente, descartada vállidamente en IS

---

## Recomendaciones — Orden de prioridad

**INMEDIATO (Alexander decide):**
1. ¿Mantener spread config = 4 pips (optimista), o importar histórico 7–50?
2. ¿Implementar slippage simple 0.5 pips, o conservar 0?

**CORTO PLAZO (post-auditoría):**
3. Spot-check calendario EURUSD pre-1999 (5 festivos conocidos)
4. Re-ejecutar hipótesis 001–009 con spread/slippage ajustado si hay cambio

**FUTURO (infraestructura robusta):**
5. Importar spread + slippage histórico de MT5 / Darwinex
6. Alertas automáticas si config diverge de datos reales
7. Auditoría trimestral de datos nuevos

---

## Archivos generados

- `data/audit/is_spotcheck.json` — RSI, spread stats, reproducible
- `data/QUALITY_AUDIT.md` — sondeo ejecución, limitaciones
- `scripts/audit_is_spotcheck.py` — script reproducible

---

## Estado de tests

✓ **189 pasan** (antes: 187 pasan, 2 fallan por estado de 007)  
✓ **Preflight OK** (sin cambios no consolidados tras esta auditoría)

---

## Próximo paso

Codex/Claude: Esperar decisión de Alexander sobre spread/slippage.  
Alexander: Decide (A) mantener config actual, (B) importar histórico, (C) adoptar slippage modelo.  
Después: Re-ejecutar hipótesis si cambio es significativo, o proceder a triaje de 19 candidatos pendientes.
