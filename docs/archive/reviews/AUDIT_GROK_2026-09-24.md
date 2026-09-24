# AUDIT_GROK_2026-09-24 — Auditoría externa independiente

**Auditor:** Grok (xAI), rol de auditor técnico senior (systematic trading / quant research / agentic systems)  
**Fecha:** 2026-09-24  
**Alcance:** Revisión del estado del laboratorio en rama `master` (documentación + árbol del repo).  
**Naturaleza:** Documento de referencia. **No es código ejecutable.** No modifica umbrales, OOS ni hipótesis cerradas.

**Dueño de implementación:** Claude (diseño de contratos) + Codex (código en `qaf/`), según `AGENTS.md`.  
**Dueño de decisiones reservadas:** Alexander (umbrales, budget de ensayos, ASSUMED por paywall, unlock OOS, bróker).

---

## 1. Veredicto ejecutivo

### Qué tienen realmente

Laboratorio **hipótesis-first** con:

- Ciclo de vida explícito (captura → investigación → protocol → engine → validator).
- Coordinación multi-agente con reservas SQLite (`AGENTS.md`).
- Motor `qaf` 2.0 con puertas IS **fail-closed**.
- Partición IS/OOS sellada; **OOS cerrado a propósito** hasta que algo pase IS.
- Resultado empírico honesto: **11 hipótesis, 0 aprobadas** (10 `discarded_is`, 1 `rejected_by_user`, 1 `invalid_por_datos`).

### Lo más importante

| Nivel | Evaluación |
|-------|------------|
| Hipótesis individual | **Fuerte** — difícil autoengañarse en un solo backtest |
| Programa de investigación (N ensayos del laboratorio) | **Incompleto** — falta contabilidad global de trials y deflación |

**Pregunta clave:** ¿El pipeline descubre edge o fabrica falsos positivos?  
**Hoy:** más capacidad de **rechazar** que de fabricar (0/11 lo demuestra).  
**Al escalar** catálogo + sensibilidad sin registry: la capacidad de fabricar falsos positivos crecerá más rápido que la de detectar edge.

**Prioridad del proyecto (confirmada por Alexander):**  
No producir más estrategias. Construir un laboratorio donde sea difícil engañarnos con un backtest.

---

## 2. KEEP / MODIFY / REMOVE / ADD

| Componente | Acción |
|------------|--------|
| Checklist de hipótesis / protocol | **KEEP** |
| Gates IS fail-closed | **KEEP** |
| OOS sellado + holdout cerrado | **KEEP** |
| Coordinación AGENTS + SQLite | **KEEP** |
| Catálogo versionado | **KEEP** |
| Investigator / Protocol / Engine / Validator | **KEEP** (no fusionar; no añadir más agentes LLM) |
| PROJECT_STATE como foto manual | **MODIFY** → verificada vs `qaf.pipeline` / preflight |
| Sensibilidad de parámetros | **MODIFY** → solo diagnóstico; cada vecino cuenta como trial |
| Cost model | **MODIFY** → histórico/stress documentado; `costs_verified` |
| Operación continua 24/7 multi-agente | **REMOVE** del roadmap hasta edge OOS |
| Optimización automática de parámetros | **REMOVE** (no añadir) |
| Experiment registry + contador de trials | **ADD** (CRÍTICO) |
| Lab-level deflation (DSR / ajuste por N) | **ADD** (ALTO; tras registry) |
| Walk-forward | **ADD** solo cuando exista un IS-pass |
| Equivalence / family clustering | **ADD** (MEDIO) |

---

## 3. Orden de implementación (estricto)

### CRÍTICO — hacer primero

#### A) Experiment Registry (determinístico — NO un agente LLM)

Cada run IS (y cada vecino de sensibilidad si se ejecuta) debe registrarse append-only con al menos:

- `run_id`
- `hypothesis_id`
- `spec_hash`
- `family`
- `symbol` / `timeframe`
- `seed`
- `costs_version`
- `gate_results` (por puerta)
- métricas clave (PF, net, DD, AED p, etc.)
- `timestamp`
- `agent`

**Debe poder responder:** ¿Cuántos ensayos lleva el laboratorio en total y por familia/hipótesis?

Implementación sugerida: JSONL o tabla SQLite dedicada + escritura desde el CLI/pipeline existente. No sustituye `reports/factory/runs/`; los indexa.

#### B) Inmutabilidad de umbrales

- Umbrales de validator / `config/runner.json` no se afinan tras ver fallos.
- Cambio de puerta = decisión explícita de Alexander + entrada en DECISIONS + test o lock versionado.
- Investigator/Protocol **no** editan thresholds del validator.

#### C) Rama canónica

- Una sola rama de trabajo (`master` hoy contiene el sistema; `main` estuvo casi vacío).
- Alinear `default_branch` y CI con esa rama.

### ALTO — justo después

#### D) Sensibilidad = trials

- Política ya dice “diagnóstica”.
- Prohibido elegir el “mejor” vecino y reportarlo como único ensayo.
- Si se corren vecinos, todos entran al registry.

#### E) Costos

- Mantener stress / spreads reales donde existan.
- Documentar `costs_verified` y `price_basis`.
- No reabrir hipótesis solo por costos salvo cambio material versionado.

#### F) Foto de estado

- `PROJECT_STATE.md` no debe contradecir `qaf.pipeline` / preflight.
- Mínimo: preflight avisa divergencia. Ideal: foto generada o verificada.

### Fuera de alcance (esta fase)

- Abrir OOS.
- Walk-forward / CPCV / PBO completo (se puede **diseñar** interfaz; implementar solo con IS-pass).
- Nuevas familias “por completar huecos”.
- Lotes grandes de candidatos sin budget de ensayos.
- Operación 24/7 entre agentes.
- Rescatar 001–011 con retoques de parámetros.

---

## 4. Política ante paywalls / fuentes incompletas

1. Si un parámetro **no** está en fuente abierta verificable:
   - `blocked` / `rejected` por `RULES_UNDERSPECIFIED`, **o**
   - si Alexander autoriza: etiquetar en spec  
     `"source": "assumed"`, `"rationale": "..."`, `"risk": "high"`  
   - Nunca presentar ASSUMED como valor “canónico” de Kaufman u otro autor de pago.

2. Preferir reglas reproducibles en abierto (docs públicos, LEAN examples, open access) sobre libros no accesibles.

3. No gastar ciclos infinitos de research en un solo autor sin acceso al texto.

---

## 5. División de trabajo

| Quién | Hace | No hace |
|-------|------|--------|
| **Claude** | Diseño del registry (schema, dónde engancha el pipeline, DoD), docs, auditoría del diff | Reescribir el motor por estética; cambiar umbrales |
| **Codex** | Implementación mínima en `qaf/` + tests | Features no pedidas; abrir OOS |
| **Alexander** | Umbrales, budget N, ASSUMED, unlock OOS, bróker | Mediar cada paso Claude↔Codex |
| **Grok** | Auditoría externa (este doc) | Commits de código del motor (salvo docs de auditoría autorizados) |

**Arranque:**

1. Claude lee este archivo + `PROJECT_STATE.md` + `AGENTS.md`.
2. Claude publica en `AGENTS.md` (Hallazgos cruzados) el diseño del registry (≤40 líneas + schema).
3. Codex hace `claim` de archivos `qaf` e implementa.
4. Claude audita el diff (no reescribe).
5. Reportan a Alexander: hecho / bloqueado / decisión requerida.

---

## 6. Definition of Done — esta fase

1. Experiment registry usable desde CLI/pipeline.
2. Comando o reporte muestra **N total** de ensayos y por hypothesis/family.
3. Umbrales de validator no cambiables sin proceso acordado (test o lock documentado).
4. `PROJECT_STATE` / `AGENTS` actualizados.
5. Suite verde; preflight OK.
6. **Nadie abrió OOS ni tocó bróker.**

---

## 7. Red-team (ataques prioritarios a bloquear con el registry)

| Ataque | Bloqueo |
|--------|--------|
| Repetir ideas “nuevas” con misma familia y params cercanos | Registry + N por family; futuro DSR |
| Elegir mejor vecino de sensibilidad y ocultar el resto | Todos los vecinos = trials |
| Escalar catálogo sin budget | Tope de IS runs tras registry |
| Relajar umbrales tras fails | Inmutabilidad + autorización Alexander |
| Presentar ASSUMED como canónico | Etiqueta obligatoria en spec |

---

## 8. Referencias metodológicas (para diseño, no para copiar papers de pago)

Prácticas ampliamente aceptadas a tener en cuenta **después** del registry:

- Contar el número de ensayos del programa de investigación (multiple testing).
- Deflated Sharpe / ajustes por selección (Bailey & López de Prado).
- Probability of Backtest Overfitting / CSCV cuando haya grillas o muchos trials.
- Holdout sellado y walk-forward cuando exista el primer IS-pass.
- Purge/embargo si hay labels con horizonte temporal.

No implementar CPCV/PBO completo en esta fase.

---

## 9. Notas de alcance de la auditoría

- Inspección basada en docs y árbol del repo en `master` (p. ej. `PROJECT_STATE.md`, `AGENTS.md`, `docs/INFRAESTRUCTURA_QAF.md`, `docs/TABLA_HUECOS.md`, `docs/CHECKLIST_HIPOTESIS.md`, `docs/AUDIT_PARAMETRIZATION.md`, specs, catálogo).
- Tras re-privatizaciones intermitentes, no se re-leyó línea a línea todo `qaf/*.py`. Si el diseño del registry choca con el código real, **documentar discrepancia con path** y no inventar módulos.

---

## 10. Mensaje operativo para Claude / Codex

Copiar a Hallazgos cruzados si hace falta recordatorio corto:

> Fase post-auditoría Grok: **Experiment Registry primero**. Claude diseña schema + puntos de enganche. Codex implementa mínimo + tests. No abrir OOS. No rescatar 001–011. No nuevos agentes LLM. No cambiar umbrales. Paywall → ASSUMED etiquetado o reject. DoD en §6 de `docs/archive/reviews/AUDIT_GROK_2026-09-24.md`.
