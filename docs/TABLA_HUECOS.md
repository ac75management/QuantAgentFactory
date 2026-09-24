# TABLA DE HUECOS — QAF v1 vs. "Listo para producción"

**Versión:** 1.0  
**Última actualización:** 2026-09-24  
**Propósito:** Inventario explícito de "qué falta para que QAF sea profesional y escalable".

No es un plan de trabajo (eso es PROJECT_STATE.md). Es un **mapa de infraestructura**: qué piezas están montadas, cuáles faltan, impacto si faltan.

---

## Leyenda

| Estado | Significado |
|---|---|
| ✓ LISTO | Implementado, tests pasan, documentado |
| ⚠️ PARCIAL | Implementado pero incompleto, en progreso, o documentación falta |
| ✗ FALTA | No existe todavía |

---

## Componente 1: DATOS

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| Importación OHLC | ⚠️ PARCIAL | Existe qaf.data, pero solo importa desde CSV local | No se puede automatizar nuevos símbolos | Conexión a API de proveedor (ej. Darwinex, OANDA) |
| Calendario (sesiones) | ✓ LISTO | qaf/calendar.py con festivos USA/UK/EU por símbolo | Rollover incorrecto, operaciones fuera de horas | Auditoría post-validación (spot check) |
| Calendario (rollover) | ⚠️ PARCIAL | Implementado para futuros; CFD no tiene rollover, hay que verificar | Errores en datos continuos si ajuste es incorrecto | Tests de rollover por símbolo |
| Spread histórico | ✗ FALTA | Config tiene valores estáticos; no hay histórico real | Backtest optimista (spread constante en realidad varía) | Importar spread histórico por timeframe, broker |
| Slippage | ✗ FALTA | No modelado (asumir 0 hoy) | Backtest optimista | Modelo simple (ej. 0.5 pips promedio para CFD) |
| Quality Audit | ✓ LISTO | Codex ejecutó auditoría de datos; reporte en data/QUALITY_AUDIT.md | No sabemos si motor/datos están rotos | Auditoría automática pre-backtest (qaf.data.validate) |

---

## Componente 2: ESPECIFICACIÓN

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| Parámetros de hipótesis | ⚠️ PARCIAL | Existen en hypotheses.json; documentación en research_external/ para 007, 008 | Nuevas hipótesis pueden tener parámetros inventados | Checklist de "parámetros verificables" en review de investigator |
| Specs JSON | ⚠️ PARCIAL | Existen para hipótesis promovidas (001-009); congeladas | Cambio post-facto de parámetros (si no está congelado, es fácil de cambiar) | Bloquear edición de specs JSON sin pasar por protocol |
| Research Queue | ✓ LISTO | Existe; preguntas 007, 008 contestadas; procesos claro | Preguntas abiertas pueden dormir indefinidamente | Revisar trimestralmente |
| Research External | ✓ LISTO | Reportes para 007, 008; formato estándar | Investigación sin documentación (implícita) | Replicar formato para futuras investigaciones |

---

## Componente 3: ARQUITECTURA (Familias de señal)

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| streak_reversal | ✓ LISTO | Implementada en qaf/signals.py; tests en tests/test_engine.py | No se pueden expresar reglas de reversión | - |
| trend_cross | ✓ LISTO | Dos medias; tests OK | - | - |
| channel_breakout | ✓ LISTO | Ruptura de rango/canal | - | - |
| oscillator_reversion | ✓ LISTO | RSI, MACD, etc. con nivel de reversal | - | - |
| sma_band_session | ✓ LISTO | Media + banda + ventana de sesión (009) | - | - |
| calendar_window | ✓ LISTO | Entrada/salida por fechas de calendario (002) | - | - |
| ma_band_breakout | ✗ FALTA | Media móvil + banda % para ruptura (008) | 008 no puede ejecutar | Implementar en qaf/signals.py (baja prioridad: 008 bloqueada por datos) |
| KAMA | ✗ FALTA | Kaufman Adaptive Moving Average (007) | 007 no puede ejecutar | Implementar en qaf/signals.py (baja prioridad: 007 bloqueada por arquitectura) |
| Indicadores custom | ✗ FALTA | Extensibilidad para nuevos indicadores | Cada nueva familia requiere código nativo | Plantilla + documentación de cómo agregar familia |

---

## Componente 4: COSTOS

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| Spread static | ✓ LISTO | config/instruments.json con spread promedio por símbolo | Backtest optimista | Validar con backtest histórico real |
| Comisión | ✓ LISTO | config/instruments.json | - | - |
| Swap (CFD) | ⚠️ PARCIAL | Existe en config; valores por defecto retail | Backtest puede estar desfasado si swap actual cambió | Verificar swing trades regularmente con broker |
| Slippage | ✗ FALTA | No modelado en qaf.costs | Entrada/salida perfectas (optimista) | Agregar a qaf.costs.slippage_cost() |
| Cost Model Doc | ✓ LISTO | docs/cost_model.md explica supuestos | - | - |
| Cost Breakdown Reports | ✓ LISTO | Engine reporta P&L bruto vs. neto | - | - |

---

## Componente 5: VALIDACIÓN

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| AED (p-value test) | ✓ LISTO | Implementado en qaf.validator | - | - |
| Profit Factor ≥ 1.3 | ✓ LISTO | Gate 1 | - | - |
| P&L neto > 0 | ✓ LISTO | Gate 2 | - | - |
| Friction Ratio ≥ 3.0 | ✓ LISTO | Gate 3 (visto fallar en 001, 003, 002) | - | - |
| Bootstrap CI > 0 | ✓ LISTO | Gate 5 (visto fallar en 003) | - | - |
| Drawdown ≤ 0.2 | ✓ LISTO | Gate 6 | - | - |
| Sensibilidad (vecinos) ≥ 50% | ✓ LISTO | Gate 7 | - | - |
| IS/OOS Partition (sealed) | ✓ LISTO | Hashes criptográficos, sellos | - | - |
| OOS Holdout | ✗ FALTA | OOS nunca ha corrido en QAF v1 (no hay hipótesis que pase IS) | No se puede validar generalización | Esperar a que alguna hipótesis pase IS |

---

## Componente 6: COORDINACIÓN Y AUTOMATIZACIÓN

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| AGENTS.md (coordinación) | ✓ LISTO | File-based protocol entre Claude y Codex | - | - |
| SQLite coordination.sqlite | ✓ LISTO | Reservas atómicas de archivos | - | - |
| PROJECT_STATE.md | ✓ LISTO | Foto de estado; decisiones registradas | - | - |
| CHECKLIST (este doc) | ✓ LISTO | Ciclo de vida de hipótesis explícito | - | - |
| INFRAESTRUCTURA (este doc) | ✓ LISTO | Componentes críticos y roles | - | - |
| Tablero automático (Codex) | ✗ FALTA | Scrape de proyecto y reporte diario de avance | Manual y requiere interpretación | (low priority) Dashboard con métricas |
| Alertas de bloqueo | ✗ FALTA | Si una hipótesis falla Gate N, notificar | Bloqueos silenciosos | (low priority) Webhook o email a Alexander |

---

## Componente 7: DOCUMENTACIÓN Y VISIBILIDAD

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| AUDIT_PARAMETRIZATION.md | ✓ LISTO | Verificó 007 y 008 sin parámetros verificables | - | Ejecutar auditoría similar cada trimestre |
| Research_queue.md | ✓ LISTO | Preguntas y respuestas documentadas | - | - |
| Research_external/ | ✓ LISTO | Reportes de investigación formales | - | - |
| Cost_model.md | ✓ LISTO | Explica supuestos de costos | - | - |
| Hypotheses/_registry.md | ✓ LISTO | Vista legible de todas las hipótesis | - | - |
| VALIDATION_ROADMAP.md | ⚠️ PARCIAL | Explica qué falta para abrir OOS; sin fecha | Confusión sobre cuándo OOS está listo | Actualizar con hitos específicos |
| Specs/ (JSON) | ⚠️ PARCIAL | Existen para 001-009 congeladas | Nuevas familias pueden no estar documentadas | Plantilla de spec JSON obligatoria |
| Catalog/ (candidatos) | ⚠️ PARCIAL | 29 fichas; 3 promovidas, 7 rechazadas, 19 sin triaje | No sabemos qué candidatos del catálogo podrían ser valiosos | Triaje sistemático de los 19 (low priority) |

---

## Componente 8: TESTS Y CI/CD

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| Unit tests (qaf/) | ✓ LISTO | 189 tests pasan (como de 2026-09-24) | - | - |
| Integration tests | ⚠️ PARCIAL | Tests de "hipótesis completa" existen pero limitados | No se prueba el flujo end-to-end antes de backtest | Agregar test "dummy hypothesis" que pase todas fases |
| Regression tests | ✗ FALTA | No hay test para "si cambio X, hipótesis Y sigue pasando/fallando" | Cambios silenciosos que rompen hipótesis viejas | (low priority) Baseline de hipótesis conocidas |
| CI/CD Pipeline | ✗ FALTA | No hay GitHub Actions ni CI automatizado | Cambios de código no se validan antes de merge | (medium priority) GitHub Actions: run tests on push |
| Pre-commit hooks | ⚠️ PARCIAL | Existe `qaf.preflight`, pero no es un hook de git | Posible commitear cambios que violarían reglas | Activar pre-commit hook si no corre qaf.preflight |

---

## Componente 9: ESCALABILIDAD Y MANTENIMIENTO

| Pieza | Estado | Descripción | Impacto si falta | Próximo |
|---|---|---|---|---|
| Logging | ⚠️ PARCIAL | Engine/validator logean, pero no centralizados | Debugging difícil; no hay trail de "qué pasó" | Logging estructurado (JSON) + centralizado |
| Config management | ✓ LISTO | config/ es la única fuente de verdad | - | - |
| Database schema | ✓ LISTO | SQLite coordination.sqlite y manifest.json | - | - |
| API (future) | ✗ FALTA | No hay API REST ni interfaz web | No se puede consultar estado desde afuera | (low priority, future) FastAPI endpoint |
| Performance monitoring | ✗ FALTA | No hay métricas de velocidad de backtest | Cambios silenciosos pueden ralentizar IS | (low priority) Benchmarks por hipótesis |

---

## Resumen por criticidad

### 🔴 CRÍTICO (bloquea producción)
- Data: spread histórico, slippage (hoy asume 0)
- Arquitectura: ma_band_breakout, KAMA (bloquean 007, 008)
- Validación: OOS holdout (nunca ejecutado porque no hay hipótesis que pase IS)

**Nota:** Los últimos dos son "críticos" solo si Alexander decide continuar 007 y 008; si los archiva, no lo son.

### 🟡 IMPORTANTE (afecta confianza)
- Datos: spread histórico por timeframe (varía), slippage (varía por hora)
- Tests: regression tests (cambio invisible rompe hipótesis)
- CI/CD: GitHub Actions (cambios sin validar)

### 🟢 NICE-TO-HAVE (mejora escalabilidad)
- Indicadores custom (extensibilidad)
- Alertas de bloqueo
- Dashboard/tablero automático
- API REST
- Performance monitoring

---

## Próximos pasos recomendados

**Inmediato (Alexander):**
1. ¿Descartar 007 y 008 (parar ambición de arquitectura) o implementar ma_band_breakout + KAMA?
2. ¿Priorizar spread/slippage históricos o aceptar modelo actual como "suficientemente realista"?

**Corto plazo (Codex + Claude):**
1. Triaje de los 19 candidatos sin revisar en catálogo
2. Regression tests: hipótesis dummy que pasa todas las fases
3. GitHub Actions básico: run tests on push

**Mediano plazo:**
1. Logging centralizado
2. Spread/slippage históricos
3. Alertas de bloqueo

---

**Propósito:** Que Alexander (y futuro equipo) sepan exactamente "cuál es el estado de salud de QAF, qué falta, y cuál es el impacto si no lo hacemos".
