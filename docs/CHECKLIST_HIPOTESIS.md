# CHECKLIST — Ciclo de vida de una hipótesis

**Versión:** 1.0  
**Última actualización:** 2026-09-24

Antes de pasar de una fase a la siguiente, todas las cajas deben estar ✓. Si alguna está ✗, la hipótesis queda **bloqueada** y se documenta el motivo en hypotheses.json.

---

## FASE 0: Captura del candidato

**Estado esperado:** `status: "captured"` en `catalog/candidates/`

- [ ] Fuente primaria identificada (URL o DOI o libro)
- [ ] Resumen de reglas en lenguaje natural (sin código)
- [ ] Símbolos/timeframes propuestos que existan en config/instruments.json
- [ ] Datos requeridos (OHLC, volumen, calendario) disponibles
- [ ] Familia de señal necesaria identificada (¿streak_reversal, trend_cross, ...?)

**Resultado:** Candidato entra en review de investigator.

---

## FASE 1: Investigación de evidencia

**Estado esperado:** `status: "promoted"` a hipótesis en hypotheses.json

### 1.1 — Parámetros verificables

- [ ] **Cada parámetro tiene fuente primaria documentada** (libro + página, paper + DOI, documentación oficial)
  - ✗ Si no: marcar como ambigüedad en review; pedir a Alexander que ejecute Deep Research o rechazar
- [ ] **Año de publicación anterior al IS** (1998 para nuestro IS 1998-2018)
  - ✗ Si no: rechazar (parámetros "optimizados mirando nuestros datos")
- [ ] **Valores numéricos congelados**, no rangos vagas ("larga media" = mal; "21 períodos" = bien)
  - ✗ Si no: marcar como incompleta; no pasar a protocol

### 1.2 — Reglas de entrada y salida

- [ ] **Entrada:** criterio claro y reproducible de cuándo abrir posición
  - ✗ Si es "cuando sienta el momentum": rechazar (subjetivo, no reproducible)
- [ ] **Salida:** criterio claro de cuándo cerrar
  - ✗ Si es "cuando se le acabe el dinero": rechazar
  - ⚠️ Si hay múltiples variantes (ej. "stop o take profit, lo que primero"): documentar explícitamente; no rechazar

### 1.3 — Datos y calendario

- [ ] **Símbolo existe en config/instruments.json**
- [ ] **Timeframe es H1, H4 o D1** (pertenencia a proyecto)
- [ ] **Histórico disponible desde procedencia clara** (fecha de inicio ≥ 1998 para IS; ≥ la fecha de publicación del paper/libro)
  - ✗ Si no: bloquear (Gate 0 fail); marcar como `invalid_por_datos`
- [ ] **Calendario**: sesiones, festivos, rollover documentados para el símbolo

### 1.4 — Familia de señal

- [ ] **¿Existe familia que pueda expresar esta regla?** (FAMILIES en qaf/contracts.py)
  - ✓ Si existe: proceder
  - ✗ Si no existe: bloquear con `reason_code: FAMILY_NOT_IMPLEMENTED`; no pasar a protocol
  - ⚠️ Si existe pero es "casi": marcar como bloqueada; architecture decision to Alexander

**Resultado si TODO pasa:** `status: "promoted"` → pasar a FASE 2 (protocol).  
**Resultado si falla:** `status: "rejected"` o `"blocked_architecture"` + motivo claro

---

## FASE 2: Especificación congelada (protocol)

**Estado esperado:** `status: "pending_protocol"` o `"protocol_done"` en hypotheses.json; spec JSON en `docs/specs/`

### 2.1 — Parámetros congelados en JSON

- [ ] **Todos los parámetros de FASE 1 están en el JSON** (sin cambios post-investigación)
- [ ] **Cada parámetro tiene `source` y `verified_date`**
- [ ] **Familia de señal está en el JSON con parámetros mapeados**

### 2.2 — Entrada y salida

- [ ] **Entrada:** regla concreta, no interpretable (pseudocódigo o fórmula matemática)
- [ ] **Salida:** idem
- [ ] **Stop y take profit:** valores concretos o fórmulas (ATR, %, puntos)

### 2.3 — Costos y fricción

- [ ] **Spread por símbolo/timeframe en spec** (de config/instruments.json)
- [ ] **Swap/comisión documentado**
- [ ] **Slippage asumido documentado** (ej. 0.5 pips)

### 2.4 — Validación de spec

- [ ] **validate_spec() pasa**: familia existe, parámetros son interpretables
- [ ] **No hay ambigüedades sin resolver** (cada decisión de design congelada)

**Resultado si TODO pasa:** `status: "protocol_done"` → pasar a FASE 3 (engine).  
**Resultado si falla:** `status: "blocked_protocol"` + error específico

---

## FASE 3: Ejecución (engine)

**Estado esperado:** `status: "engine_running"` → IS backtest ejecutándose

### 3.1 — Motor

- [ ] **Engine puede parsear la spec JSON**
- [ ] **Familia de señal está implementada en qaf/signals.py**
- [ ] **Tests de la familia pasan** (pytest tests/test_engine_<familia>.py)

### 3.2 — Datos cargados

- [ ] **Histórico del símbolo/timeframe cargado correctamente**
- [ ] **Calendario aplicado** (sesiones, festivos, rollover)
- [ ] **Partición IS/OOS sellada** (hashes criptográficos verificados)

### 3.3 — Ejecución causal

- [ ] **Entradas:** el precio/indicador se conoce al cierre de la barra que genera la señal (no forward-looking)
- [ ] **Ejecución:** entrada al cierre de esa barra O apertura siguiente (documentado)
- [ ] **No hay "look-ahead bias"**

**Resultado si TODO pasa:** Backtest IS completa, reporte generado en `reports/factory/runs/<run_id>/`.  
**Resultado si falla:** `status: "blocked_engine"` + error (ej. "datos corrupto", "familia no implementada")

---

## FASE 4: Validación (validator)

**Estado esperado:** Puertas de IS/OOS pasan → `status: "ready_oos"` o fallan → `status: "discarded_is"`

### 4.1 — Análisis de rentabilidad

- [ ] **Profit factor ≥ 1.3**
  - ✗ Si < 1.3: FAIL Gate 1
- [ ] **P&L neto (después de costos) > 0**
  - ✗ Si ≤ 0: FAIL Gate 2
- [ ] **Ratio de fricción ≥ 3.0** (P&L neto / costos totales)
  - ✗ Si < 3.0: FAIL Gate 3 (fricción domina edge)

### 4.2 — Robustez estadística

- [ ] **AED (Ancillary Empirical Distribution) p < 0.05**
  - ✗ Si ≥ 0.05: FAIL Gate 4 (no se distingue de azar)
- [ ] **Bootstrap IC 95% > 0**
  - ✗ Si ≤ 0: FAIL Gate 5 (no es rentable en el muestreo)

### 4.3 — Drawdown y estabilidad

- [ ] **Max drawdown ≤ 0.2** (20% del capital)
  - ✗ Si > 0.2: FAIL Gate 6 (riesgo excesivo)
- [ ] **Sensibilidad ≥ 50%** (≥50% de los vecinos de parámetros son rentables)
  - ✗ Si < 50%: FAIL Gate 7 (frágil a cambios pequeños)

### 4.4 — Decisión

- [ ] **Todas las puertas pasan** → hipótesis→ `status: "ready_oos"` → OOS se abre (si Alexander lo autoriza)
- [ ] **Al menos una puerta falla** → `status: "discarded_is"` → sin OOS, sin revisión; documentar qué puerta(s) y motivo

**Nota:** No se hace "ajuste de parámetros" post-fallo. Si alguien cree que una variante distinta pasaría, es una **nueva hipótesis** con nuevo ID.

**Resultado:** Hipótesis entra en archivo y PROJECT_STATE.md se actualiza.

---

## FASE 5: Out-of-sample (OOS) — FUTURA

**Estado esperado:** `status: "oos_running"` o `"oos_done"` (no ejecutado aún en QAF v1)

(Planos: mismas puertas pero sobre datos sellados post-IS. No ejecutado todavía; está en roadmap.)

---

## Bloqueos documentados

Si una hipótesis queda bloqueada, el motivo va aquí con ejemplo:

| Motivo | Reason_code | Ejemplo | Resolución |
|---|---|---|---|
| Parámetros no verificables | RULES_UNDERSPECIFIED | 007 (ER_Length sin fuente primaria) | Deep Research → obtener parámetro + rellenar en hypotheses.json |
| Datos sin procedencia | GATE0_FAIL_PRE_EURO_PROVENANCE | 008 (EURUSD pre-1999) | Importar datos verificados O archivar |
| Familia no implementada | FAMILY_NOT_IMPLEMENTED | 007 inicialmente (no había KAMA en qaf/signals.py) | Implementar familia O descartar |
| Ambiente no listo | ENGINE_NOT_READY | (hipotético) | Esperar a que ambiente se estabilice |

---

## Cómo usar este checklist

1. **Cuando investiga una hipótesis nueva:** comienza en FASE 0, revisa cada caja.
2. **Cuando avanza a una fase nueva:** verifica que TODO de la fase anterior está ✓.
3. **Cuando se bloquea:** marca ✗ en la caja relevante, documenta motivo en hypotheses.json + AGENTS.md.
4. **Cuando resuelve un bloqueo:** marca ✓, actualiza estado en hypotheses.json, continúa.

---

**Propósito:** Que no hay ambigüedad sobre "cuándo una hipótesis está lista para pasar de fase". Todo está documentado y verificable.
