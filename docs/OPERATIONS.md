# Modelo operativo de QuantAgentFactory

Este documento responde tres preguntas: qué es seguro hacer ahora, cómo se evita que dos agentes se sobreescriban y qué significa realmente optimizar una estrategia.

## Coordinación

El ciclo de cualquier agente (preflight, reserva atómica, tablero, pruebas y cierre) está en `AGENTS.md`, que es la única copia. Las fuentes operativas son `python -m qaf.preflight` (salud), `python -m qaf.pipeline` (fase y siguiente actor de cada hipótesis) y `python -m qaf.coordination status` (reservas).

## Pipeline de investigación y optimización permitido

1. **Catálogo:** capturar una idea y su fuente; todavía no es hipótesis ejecutable.
2. **Revisión de evidencia:** distinguir réplica de adaptación y declarar reservas.
3. **Hipótesis:** fijar mecanismo causal, instrumento, timeframe y motivo económico.
4. **Protocol:** congelar reglas, fill model y como máximo 3-4 parámetros libres antes de observar el backtest.
5. **Gate 0:** datos, partición, contrato del instrumento y reservas explícitas.
6. **AED en IS:** comprobar si la señal cruda tiene relación direccional antes de costos y sizing.
7. **Backtest IS:** ejecutar una sola spec registrada con ledger de costos reproducible.
8. **Robustez IS:** baseline de igual capital 1x, costos x2, bootstrap, segmentos temporales y sensibilidad ±10/20%.
9. **Decisión IS:** descartar, declarar inconclusa o dejar candidata. Un vecino de sensibilidad nunca reemplaza la spec original.
10. **Prerrequisitos finales:** costos históricos, calendario, bid/ask/mid, procedencia, multiplicidad y walk-forward real.
11. **Freeze:** congelar hashes de spec, código, datos, costos y política.
12. **OOS único:** una apertura sin iteración. Fallar implica rechazo; no se vuelve a IS para rescatar la misma hipótesis.
13. **Incubación:** solo una estrategia aprobada puede pasar a demo y luego lote mínimo, cada paso con autorización fresca.

Cambiar una regla o parámetro después de ver resultados no es “mejorar la misma estrategia”: es una hipótesis nueva, con nuevo ID y otro consumo del presupuesto de pruebas.

## Decisiones metodológicas fijadas

- El baseline 1x se conserva como costo de oportunidad absoluto: la estrategia debe ser positiva y superar su P&L neto. No se presenta como comparación ajustada por riesgo.
- La sensibilidad no optimiza. Sus valores y umbrales viven en `config/runner.json`: 200 vecinos, rango ±20%, al menos 100 válidos, percentil original máximo 0.80 y al menos 50% de vecinos rentables.
- Estos umbrales son una política conservadora inicial. Solo pueden cambiarse antes de una campaña nueva, documentando motivo y efecto; nunca para rescatar una corrida observada.

## Modelos por tarea (acordado por Claude y Codex, 2026-09-22; ajustado el mismo día tras consultarlo de nuevo)

Alexander usa suscripciones, no pago por token: los planes de Claude y de ChatGPT son presupuestos separados. Se escala el modelo solo al tomar una tarea que lo justifique, y por defecto se usa el nivel barato — "Codex" o "Claude" en la tabla es la familia/el rol, no autorización permanente para su nivel más caro.

| Tarea | IA / modelo |
|---|---|
| Método, diseño y auditoría de cambios en costos, puertas, datos, OOS o el motor | Claude Opus / Codex en razonamiento alto |
| Implementación normal de código en `qaf/` con pruebas | Codex en razonamiento medio |
| Triaje y revisión de evidencia (`investigator`), borradores de `protocol` | Claude Sonnet (o equivalente medio) como subagente |
| Mecánico: preflight, pruebas, `qaf.cli run`, reportes de estado, formato | Claude Haiku o el modelo barato de Codex |

- **Auditoría proporcional al riesgo.** Lo crítico (dinero, costos, puertas, datos, OOS) lo audita la otra IA, en su nivel alto. El formato y los reportes basta con validarlos con pruebas deterministas.
- **Un rol por tarea:** quien implementa no aprueba su propio cambio. Si la otra IA no está disponible, la tarea queda `PENDIENTE_REVISION` en el tablero, nunca `TERMINADO`.

### Operación continua — en espera, punto objetivo acordado (2026-09-22)

Alexander pidió no construir esto (recordaba que GPT ya se lo había dicho antes) sin que las dos IA coincidieran primero en el momento. Consultado de nuevo: **se espera.**

**Señal de arranque, acordada por Claude y Codex:** al menos una hipótesis que recorra las 5 fases (catálogo → investigator → protocol → engine → validator) y llegue a `READY_FOR_FROZEN_VALIDATION` con artefactos, puertas y fallos cerrados reproducibles — sin exigir abrir OOS, que sigue bloqueado a propósito por `qaf/holdout.py`. Hasta que eso ocurra, ninguna IA construye lo de abajo por su cuenta.

Diseño ya acordado para cuando llegue ese momento (sigue sin implementarse):
- Un ciclo del Programador de tareas de Windows cada 2 horas, sin demonio permanente. `qaf.pipeline` y la cola SQLite deciden si hay trabajo; si no hay, el ciclo termina sin gastar.
- Un interruptor durable `RUN` / `STOP` / `DRAIN` en archivo o SQLite: no depende de interpretar mensajes. Una reserva impide que dos ciclos se solapen, y hay un tope diario de ejecuciones por IA.
- Las decisiones reservadas a Alexander (método, commits, extracciones, costos, OOS, bróker) se registran como aprobaciones persistidas, con identificador e idempotencia. Una notificación al celular no cuenta como aprobación.

**"OmniRoot"** (mencionado por Alexander en otra conversación, conectar skills para ahorrar tokens): consultado con Codex el 2026-09-22 — no existe con ese nombre en la documentación oficial de OpenAI ni es un término que Codex reconozca con certeza. Ninguna IA le inventa una definición. Si aparece algo verificable, se evalúa después de la señal de arranque de arriba, no antes.

## Prioridad actual

Vive en un solo lugar: la sección NEXT ACTION de `PROJECT_STATE.md`. OOS y cualquier afirmación de estrategia validada siguen bloqueados hasta cumplir `docs/VALIDATION_ROADMAP.md`.
