# MISIÓN DEL LABORATORIO — Criterio de continuidad

**Fuente:** Alexander (2026-09-24).  
**Uso:** Criterio para decidir qué construir y qué no. No reinicia el plan actual. No sustituye `AUDIT_GROK` ni `STANDING_ORDERS`; los acota.

---

## Meta real

Construir un **laboratorio cuantitativo asistido por IA** que pueda:

investigar ideas → formular hipótesis → probarlas → rechazarlas o validarlas → **aprender** de los resultados,

buscando ventajas de trading con **posibilidad real de sobrevivir fuera de muestra**.

**No es la meta:** el repo más complejo, muchos agentes, muchos protocolos, ni “infraestructura por infraestructura”.

Agentes (Claude, Codex, Grok, …) son **trabajadores** del laboratorio, no el laboratorio. El conocimiento debe vivir en **Git, registry, results y docs**.

---

## Equilibrio obligatorio

| Rigor (controlar contaminación) | Libertad (no limitar el pensamiento) |
|----------------------------------|--------------------------------------|
| Overfitting, leakage, falsos positivos | Razonar, investigar, cuestionar reglas |
| Irreproducibilidad, OOS contaminado | Crear hipótesis y proponer soluciones |
| Repetir los mismos ensayos sin registro | Aprender de fracasos y éxitos |
| Historial perdido | Continuar donde otro agente dejó |

**Regla:** las reglas controlan lo que se puede **contaminar o fingir**, no lo que se puede **pensar o proponer**.

---

## Anti-sobreingeniería

Cada regla, archivo, gate, agente o proceso nuevo debe responder:

> ¿Qué problema **real** resuelve ahora?

Si se puede más simple y seguro → **preferir lo simple**.  
La complejidad crece **solo cuando hace falta** (p. ej. más ensayos → más deflación; primer IS-pass → walk-forward).  
No aplicar “todas las pruebas estadísticas del mundo” a cada idea inicial; tampoco dejar pasar a etapas serias con validación débil.

---

## Memoria del laboratorio

Conservar, de éxitos y fracasos:

- qué se probó, con qué datos, parámetros, resultado, qué se aprendió.

Para que dentro de meses nadie repita el mismo experimento a ciegas.  
El Experiment Registry y el catálogo de rechazos existen **por esto**, no por ceremonia.

---

## Alineación con el plan actual (no cambiar de rumbo)

| Pieza actual | ¿Alineada con la misión? |
|--------------|---------------------------|
| Fail-closed IS, OOS cerrado, no rescatar 001–011 | Sí — rigor |
| Experiment Registry + count-trials | Sí — memoria y no repetir a ciegas |
| Standing orders / no cerrar proyecto | Sí — continuidad |
| No abrir OOS ni cambiar gates sin Alexander | Sí — control de contaminación |
| No añadir agentes LLM ni orquestación 24/7 | Sí — anti-sobreingeniería |
| Cron cada 15 min “por si acaso” | **No** — ruido y tokens; preferir HANDOFF en archivos |
| Re-auditoría o reconstrucción desde cero | **No** — no hace falta |

**Falta importante (simple):** que el registry y los HANDOFF estén **en git y se usen**; no más marcos teóricos.

**Complejidad innecesaria a evitar ahora:** más agentes, dashboards, CPCV completo, optimizadores, “cerrar el laboratorio porque no hay edge”.

---

## Cómo continuar

1. Seguir `docs/STANDING_ORDERS_ALEXANDER_AWAY.md` y el plan del registry.  
2. Antes de añadir algo nuevo: releer esta misión.  
3. Comunicar por `AGENTS.md` + `PROJECT_STATE.md`.  
4. No abrir otra auditoría general salvo que Alexander lo pida.

---

*Fin.*
