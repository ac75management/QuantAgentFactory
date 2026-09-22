# Modelo operativo de QuantAgentFactory

Este documento responde tres preguntas: qué es seguro hacer ahora, cómo se evita que dos agentes se sobreescriban y qué significa realmente optimizar una estrategia.

## Fuentes operativas

No se deduce el estado actual leyendo toda la bitácora:

- `python -m qaf.preflight`: salud del repositorio, coherencia, reservas y cambios pendientes.
- `python -m qaf.pipeline`: fase y siguiente actor de cada hipótesis.
- `python -m qaf.coordination status`: archivos reservados en este working tree.
- `PROJECT_STATE.md`: historial append-only; aporta contexto, no autoridad operativa.

## Ciclo obligatorio de cualquier agente

1. Ejecutar `python -m qaf.preflight` y leer `AGENTS.md`.
2. Consultar `python -m qaf.pipeline --hypothesis <id> --as <agente>` cuando el trabajo pertenece a una hipótesis.
3. Revisar el diff de cada archivo que se piensa tocar.
4. Adquirir el conjunto completo de archivos de forma atómica:

   ```powershell
   .venv\Scripts\python.exe -m qaf.coordination claim --agent "Claude-app" --objective "objetivo concreto" qaf/modulo.py tests/test_modulo.py
   ```

5. Reflejar la reserva en `AGENTS.md`. Durante trabajos largos, enviar heartbeat antes de 120 minutos.
6. Implementar una unidad terminada, sin stubs que aparenten pasar.
7. Ejecutar preflight y la suite completa con un `--basetemp` exclusivo.
8. Registrar resultado en `PROJECT_STATE.md` y `AGENTS.md`; liberar las reservas al final.

La base `state/coordination.sqlite3` está ignorada por git porque coordina procesos locales. La clave primaria por ruta y `BEGIN IMMEDIATE` impiden que dos agentes adquieran simultáneamente el mismo archivo. Una reclamación con un conflicto no adquiere ningún archivo.

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

## Prioridad actual

**Ahora:** consolidar en un commit el lote estable cuando Alexander lo autorice. Mientras permanezca sin commit, el preflight mostrará una advertencia deliberada.

**Siguiente:** `protocol` para la hipótesis 007, sin escoger parámetros por el mejor resultado. Si la fuente no permite congelarlos de forma defendible, bloquearla.

**Bloqueado:** OOS y cualquier afirmación de estrategia validada, hasta cumplir `docs/VALIDATION_ROADMAP.md`.

**Puede esperar:** nuevas familias, agentes adicionales, despliegue, sizing avanzado y expansión de mercados.
