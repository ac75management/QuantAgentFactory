# STANDING ORDERS — Alexander ausente (2026-09-24)

**Autoridad:** Alexander (dueño del proyecto).  
**Canal de comunicación:** solo archivos del repo (`AGENTS.md` Hallazgos cruzados + `PROJECT_STATE.md` bitácora).  
**No cerrar el proyecto.** Hay trabajo útil de laboratorio aunque no haya edge todavía.

---

## Qué hizo Grok en GitHub (remoto `master`)

| Archivo | Estado |
|---------|--------|
| `docs/archive/reviews/AUDIT_GROK_2026-09-24.md` | **Existe en remoto** (si no lo ves en disco local: `git pull origin master`) |
| `AGENTS.md` en remoto | Quedó **recortado** por un accidente de escritura; **restaurar** desde historial local o commit previo y fusionar con el trabajo del Experiment Registry |
| Código `qaf/experiment_registry.py` | Según Claude/Codex: **implementado en working tree local** — debe **commitearse y pushearse** a `master` si aún no está en remoto |

**Si Claude no ve el AUDIT:** no inventarlo de nuevo. Hacer `git fetch` + `git pull` en `master`. URL:  
https://github.com/ac75management/QuantAgentFactory/blob/master/docs/archive/reviews/AUDIT_GROK_2026-09-24.md

---

## Respuesta a la pregunta de Claude

> ¿Guardar el audit o cerrar el proyecto?

1. **No cerrar el proyecto.**
2. El audit **ya está en el remoto**; sincronizar local.
3. El Experiment Registry (si está solo local) **debe quedar en git** + bitácora.
4. Seguir la **cola de abajo** en orden, sin pedir permiso turno a turno salvo bloqueos listados en §Prohibido.

---

## Límites duros (no negociables mientras Alexander está ausente)

| Prohibido | Motivo |
|-----------|--------|
| Abrir OOS / tocar `holdout` | Reservado a Alexander |
| Conectar bróker / demo / live | Reservado |
| Cambiar umbrales de validator / `runner.json` gates | Reservado |
| Rescatar o re-parametrizar 001–011 | Sin evidencia nueva |
| Operación continua 24/7 / nuevos agentes LLM | Fuera de alcance |
| Optimización automática de parámetros | Overfitting |
| Campañas masivas de nuevos IS runs | Sin budget fijado |
| Commits que no pasen preflight + suite | Calidad |

**Permitido sin preguntar:** endurecer laboratorio, tests, docs, backfill del registry, alineación PROJECT_STATE, CI, costs_verified docs, restore AGENTS.

---

## Cola de trabajo (orden estricto — avanzar lo máximo posible)

### BLOQUE 0 — Sincronización (hacer YA, ambos)

1. `git status` / `git pull origin master`.
2. Confirmar que existe `docs/archive/reviews/AUDIT_GROK_2026-09-24.md` en disco.
3. Si el Experiment Registry solo está en local: **commit + push** a `master` (código + tests + entrada en bitácora).
4. **Restaurar `AGENTS.md` completo** (historial de coordinación) si el remoto sigue recortado; conservar el schema del registry y esta orden.
5. Anotar en Hallazgos cruzados: “sync OK / registry en remoto: sí|no”.

### BLOQUE 1 — Cerrar el DoD del Experiment Registry

1. Verificar que cada IS run nuevo escribe una fila en el registry (JSONL u store acordado).
2. CLI `count-trials` (o equivalente) responde **N total** y por hypothesis/family.
3. **Backfill:** registrar runs históricos ya existentes bajo `reports/factory/runs/*` (best-effort, documentar gaps).
4. Test que falla si un run de engine no registra trial (si es viable sin fragilidad excesiva).
5. Actualizar `PROJECT_STATE.md`: NEXT ACTION = laboratorio endurecido; registry operativo.

### BLOQUE 2 — ALTO de la auditoría (sin tocar umbrales)

1. **Sensibilidad = trials:** documentar + código: vecinos de sensibilidad, si se ejecutan, incrementan N; no elegir “el mejor” como único ensayo.
2. **Foto vs pipeline:** preflight WARN si `PROJECT_STATE` contradice `qaf.pipeline` (o checklist manual en preflight docs).
3. **Costos:** documentar `costs_verified` / `price_basis` reales en instruments; no reabrir hipótesis.
4. **Rama canónica:** `master` como única fuente; no dejar trabajo solo en otra rama sin push.

### BLOQUE 3 — Higiene del laboratorio (si 0–2 hechos)

1. Suite verde estable; eliminar tests acoplados a estados “vivos” de hipótesis si aún fallan por eso.
2. Activar o documentar CI (workflow ya existe): tests on push en `master`.
3. Revisar que `gitignore` no ignore el registry si debe versionarse (o versionar snapshots de N, no secretos).
4. Una pasada de **docs consistency**: enlaces rotos al AUDIT, TABLA_HUECOS, VALIDATION_ROADMAP.

### BLOQUE 4 — Solo si sobra capacidad (bajo prioridad)

1. Diseño **en papel** (doc corto) de walk-forward post primer IS-pass — **sin implementar**.
2. Triaje **pasivo** de candidatos del catálogo (clasificar reject reasons) — **sin** promover ni correr IS en masa.
3. Lista de “decisiones para cuando vuelva Alexander” en `PROJECT_STATE` OPEN QUESTIONS (008 datos, budget N semanal, CI on/off).

---

## Roles mientras Alexander está ausente

| Quién | Hace |
|-------|------|
| **Claude** | Coordinación, docs, diseño de contratos, auditoría de diffs de Codex, bitácora, restore AGENTS |
| **Codex** | Código `qaf/`, tests, backfill registry, preflight hooks |
| **Grok** | Órdenes en este archivo / AUDIT; no implementa motor |
| **Alexander** | Vuelve para: OOS, umbrales, budget, ASSUMED, bróker, archivar 008 |

Comunicación: **no** esperar chat. Todo en `AGENTS.md` → Hallazgos cruzados (3–10 líneas por avance) + bitácora PROJECT_STATE.

---

## Criterio de “avanzamos suficiente” (parar y esperar a Alexander)

Se considera buen punto de pausa cuando:

- [ ] Registry en remoto + backfill de runs históricos (o gaps documentados)
- [ ] `count-trials` usable
- [ ] AGENTS.md restaurado y coherente
- [ ] PROJECT_STATE actualizado
- [ ] Suite verde
- [ ] Lista OPEN QUESTIONS para Alexander (máx. 5 ítems)

**No** es éxito: “cerrar el proyecto” o “buscar la estrategia que pase IS a toda costa”.

---

## Mensaje corto para Hallazgos cruzados (copiar)

```
STANDING ORDERS activos: docs/STANDING_ORDERS_ALEXANDER_AWAY.md
Alexander ausente. No cerrar proyecto. No OOS.
Orden: BLOQUE 0 sync → BLOQUE 1 cerrar DoD registry + backfill → BLOQUE 2 ALTO auditoría.
Canal: solo AGENTS.md + PROJECT_STATE.
```

---

*Fin de standing orders. Cualquier duda de alcance: elegir la opción que **no** aumente N de ensayos IS ni abra OOS.*
