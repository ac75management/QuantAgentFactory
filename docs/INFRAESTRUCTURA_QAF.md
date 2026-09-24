# INFRAESTRUCTURA — QuantAgentFactory

**Documento de referencia:** Mapeo de componentes críticos, roles y responsabilidades.

**Versión:** 1.0  
**Última actualización:** 2026-09-24  
**Estado:** VIVO — es la fuente de verdad para qué agente hace qué, cuándo, y qué se considera "listo".

---

## 5 Componentes críticos de QAF

### 1. **DATOS** — Limpieza, validación, procedencia

**Qué es:** OHLC histórico, calendario (sesiones, festivos, rollover), spread/slippage, comisiones.

**Quién verifica:**
- **Procedencia:** Alexander (decisión final sobre fuentes aceptadas)
- **Limpieza:** Claude (WebSearch, validación de URLs, deduplicación)
- **Normalización:** Codex (scripts de importación, qaf.data module)

**Definition of Done:**
- ✓ Fuente verificable (URL, DOI, fecha de descarga)
- ✓ Rango de fechas documentado
- ✓ Calendario de sesiones implementado en qaf/calendar.py (festivos, rollover por símbolo/timeframe)
- ✓ Spread/slippage en config/instruments.json con justificación
- ✓ Data Quality Audit generado (`data/QUALITY_AUDIT.md`)

**Resultado:** `data/clean/manifest.json` + `data/QUALITY_AUDIT.md` + sellos criptográficos de partición IS/OOS

**Bloqueos comunes:**
- Datos pre-1999 sin procedencia (visto en EURUSD/H4 — 008)
- Spread histórico desconocido (asumir "realista" y validar post-backtest)
- Rollover mal calculado (ej. viernes 3× o cambios horarios por zona)

---

### 2. **ESPECIFICACIÓN** — Parámetros verificables de fuente primaria

**Qué es:** Valores numéricos (ER_Length, período MA, %, etc.) y reglas de entrada/salida definidas en fuentes primarias (libros, papers, documentación oficial).

**Quién verifica:**
- **Fuente primaria:** Alexander (decisión final sobre qué cuenta como "verificable")
- **Búsqueda:** Claude + Codex (Deep Research, WebSearch, papers académicos)
- **Documentación:** Claude (síntesis en `docs/research_external/<slug>.md`)

**Definition of Done:**
- ✓ Cada parámetro tiene cita textual de fuente primaria (libro/página, paper/DOI, documentación oficial)
- ✓ Año de publicación anterior al IS (no "optimizado mirando nuestros datos")
- ✓ Ambigüedades documentadas explícitamente (no ocultas)
- ✓ Reporte en `docs/research_external/<slug>.md` con: fuente, cita, qué demuestra, qué no, aplicabilidad

**Resultado:** `research_queue.md` se marca "RESPONDIDA"; hypotheses.json agrega campo `parameters` con valores congelados

**Bloqueos comunes:**
- Parámetros "sugeridos por usuarios" sin autoría de la fuente original (visto en 007, 008)
- Valores optimizados sobre datos que solapan con IS (rechazar explícitamente)
- Reglas de salida abiertas ("múltiples variantes sin una única") — documentar ambas

---

### 3. **ARQUITECTURA** — Familias de señal implementadas

**Qué es:** Familias de señal (streak_reversal, trend_cross, channel_breakout, oscillator_reversion, sma_band_session, calendar_window, ma_band_breakout, KAMA, etc.) en `qaf/signals.py` y contratos en `qaf/contracts.py`.

**Quién verifica:**
- **Diseño:** Codex + Claude (¿es una familia genérica o ad-hoc? ¿qué parámetros?)
- **Implementación:** Codex (código en qaf/signals.py)
- **Tests:** Claude (cobertura en tests/test_engine_*.py)

**Definition of Done:**
- ✓ Familia documentada en qaf/contracts.py::FAMILIES con nombre, parámetros, ejemplo
- ✓ Código en qaf/signals.py::Signal.<familia>() con docstring y tests
- ✓ Tests pasen: pytest tests/test_engine_<familia>.py
- ✓ Integración con qaf.engine.apply_signal() verificada
- ✓ Ejemplo de uso en una hipótesis que pasó a protocol

**Resultado:** Hipótesis pasa validate_spec; engine puede generar señales

**Bloqueos comunes:**
- Familia "casi lista" pero sin tests (visto con sma_band_session inicialmente)
- Parámetros de familia no coinciden con lo que la hipótesis necesita ("trend_cross requiere 2 medias, no 1 media + banda %")
- Salida no expresable en la familia existente (ej. stop-and-reverse en un sistema que solo tiene exit por precio)

---

### 4. **COSTOS** — Model realista de spread, slippage, comisión, swap

**Qué es:** Spread histórico (bid/ask), slippage por ejecución, comisión, swap/rollover de financiamiento.

**Quién verifica:**
- **Valores:** Alexander (revisión de spread histórico; swap según vehículo: CFD vs. futuro)
- **Implementación:** Codex (qaf.costs.py, aplicación en engine)
- **Validación:** Claude (backtest de hipótesis conocidas para verificar que costos sean realistas)

**Definition of Done:**
- ✓ Spread histórico documentado por símbolo/timeframe en config/instruments.json con rango (min/max/promedio)
- ✓ Swap documentado (punto de venta de CFD, comisión en futuros)
- ✓ Slippage asumido (ej. 0.5 pips promedio) documentado y justificado
- ✓ Validación: una hipótesis conocida (ej. 002 antes de ser descartada) que debería tener edge bajo estos costos se simula; si pierde por costos, son realistas; si gana de forma improbable, revisar
- ✓ Reports de engine muestran desglose de P&L bruto vs. neto (separan edge de fricción)

**Resultado:** `docs/cost_model.md` + config/instruments.json + reports detallados

**Bloqueos comunes:**
- Swap desconocido (usar "promedio de CFD retail" como placeholder y documentar)
- Spread histórico no disponible (buscar datos de plataforma coimpatible: Darwinex, OANDA)
- "Slippage perfecto" (0 pips) — rechazar, usar realista (ej. 0.3-0.5 pips en CFD, mayor en horas de baja liquidez)

---

### 5. **VALIDACIÓN** — Puertas de IS/OOS que son "fail-closed"

**Qué es:** Criterios estadísticos y económicos que una hipótesis debe pasar para abrir OOS: AED p<0.05, profit factor ≥1.3, friction ratio ≥3.0, drawdown ≤0.2, bootstrap CI >0, sensibilidad ≥50% vecinos positivos.

**Quién verifica:**
- **Criterios:** Alexander + Claude (revisión de métodos; justificación de thresholds)
- **Implementación:** Codex (qaf.validator.py)
- **Ejecución:** Claude + Codex (engine corre IS, validator evalúa)

**Definition of Done:**
- ✓ Cada puerta tiene documentación: qué mide, por qué ese threshold, qué sucede si falla
- ✓ Validator emite reporte claro (PASS / FAIL por cada puerta, motivos)
- ✓ Fallo en cualquier puerta → OOS cerrado automáticamente, no se abre
- ✓ Hipótesis descartada documenta qué puerta(s) falló y por qué
- ✓ No hay "variantes de parámetros" reoptimizadas post-fallo (nueva hipótesis con nuevo ID)

**Resultado:** `reports/factory/runs/<run_id>/validator_report.md` + actualización de hypotheses.json con `reason_code` específico

**Bloqueos comunes:**
- "Ajustar parámetros mirando resultados IS" (rechazar: es optimización, requiere nueva hipótesis)
- OOS abierto sin pasar todas las puertas (rechazar: violación del protocolo)
- Bootstrap CI incluye cero pero p-value < 0.05 (documentar ambigüedad; decidir por CI)

---

## Roles y responsabilidades

| Rol | Quién | Decisiones | Operaciones | Escaladas a Alexander |
|---|---|---|---|---|
| **Autoridad Final** | Alexander | ¿qué datos aceptar? ¿qué parámetros verificables? ¿descartar o continuar?  | (ninguna; solo decisión) | N/A |
| **Datos + Investigación** | Codex | (consulta a Alexander) | WebSearch, importación, limpieza, scripts | Procedencia dudosa, ambigüedades de fuente |
| **Coordinación + Síntesis** | Claude | (consulta a Alexander) | Deep Research, reportes, documentación, coordinación entre agentes | Decisiones de arquitectura, conflictos de interpretación |
| **Ejecución (Engine)** | Codex | (consulta) | Backtests, tests unitarios, implementación de familias | Bugs en motor, cambios de lógica |
| **Validación + Auditoría** | Claude + Codex | (consulta) | Revisión de puertas, reportes de validator | Criterios de validación insuficientes, falsos positivos |

---

## Cómo escalada funciona

1. **Si no está en la lista reservada de CLAUDE.md:** Codex y Claude lo resuelven por archivo, reportan resultado. No preguntarle a Alexander turno a turno.
2. **Si está reservado O requiere decisión de arquitectura:** Se documenta en AGENTS.md / hallazgos cruzados. Alexander lo ve y decide.
3. **Si es bug o conflicto:** Se reporta en PROJECT_STATE.md OPEN_QUESTIONS; Alexander lo resuelve.

---

## Próxima auditoría

Este documento debe revisarse cuando:
- [ ] Una nueva familia se agrega a qaf/signals.py (¿está el checklist cumplido?)
- [ ] Un nuevo símbolo/timeframe se añade (¿están todos los 5 componentes listos?)
- [ ] Un bloqueo ocurre más de una vez (¿es una brecha sistémica que debería estar documentada aquí?)

---

**Propósito:** Que cualquier agente (Claude, Codex, Alexander futuro) pueda abrir este documento y saber exactamente qué se necesita para avanzar, quién lo verifica, y cuándo está hecho.
