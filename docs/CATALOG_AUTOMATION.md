# Automatización del catálogo de ideas

## Propósito

El catálogo alimenta a los agentes con ideas investigables. Una entrada del catálogo no es una estrategia validada y no puede entrar directamente al motor.

## Flujo

1. **Captura:** registrar el enlace, descripción y contexto original.
2. **Triaje automático:** medir completitud, coincidencia con el universo, marco temporal y requisitos de datos.
3. **Revisión de evidencia:** el investigador localiza la fuente primaria y separa reglas publicadas de interpretaciones.
4. **Decisión metodológica explícita:** registrar una revisión estructurada que rechaza, bloquea por datos o declara elegible la idea.
5. **Contrato:** el agente de protocolo crea una especificación congelada.
6. **Validación QAF:** ejecutar IS, puertas estadísticas y, cuando corresponda, OOS.

La puntuación del triaje decide prioridad de investigación. No mide rentabilidad ni calidad estadística.

La ficha separa `instruments` y `original_timeframes` (lo que estudió la fuente) de `proposed_targets` (símbolo y marco que QAF podría estudiar). Esa separación evita presentar una adaptación de futuros o de una cartera como si ya fuera evidencia sobre el CFD objetivo.

La revisión y la promoción son acciones separadas. Una puntuación alta nunca crea una hipótesis por sí sola. La promoción exige una fuente primaria, un identificador estable de la regla, reglas publicadas, mecanismo, contexto original, datos, costos, limitaciones y una declaración explícita de réplica o adaptación. Toda adaptación enumera qué cambia: vehículo, instrumento, sesión, frecuencia, cartera o costos. Solo acepta el carril `mt5_now`, evita una segunda hipótesis con la misma fuente/regla/objetivo y deja OOS cerrado.

## Carriles de investigación

- `mt5_now`: coincide con un símbolo de investigación actual y puede seguir hacia una hipótesis.
- `future_market`: usa futuros, ETF, acciones, cripto u otro vehículo pendiente; se conserva para una expansión futura y no se fuerza a un CFD.
- `methodology`: aporta pruebas, estadística, costes o criterios de descarte; puede mejorar el motor, no es una estrategia.
- `agent_research`: estudia LLM, agentes, benchmarks o minería de factores; sirve para mejorar el proceso después de verificar el paper.
- `manual_review`: todavía no hay información para clasificar.

## Estados

- `captured`: idea guardada.
- `triage`: información en clasificación.
- `eligible`: fuente y reglas suficientes para formular una hipótesis.
- `needs_data`: requiere datos que QAF no tiene.
- `rejected`: idea no reproducible o fuera de alcance.
- `promoted`: ya originó una hipótesis registrada.

## Quantpedia

Quantpedia está configurada inicialmente como `manual_public`. Se pueden registrar sus páginas públicas y seguir sus referencias hasta el trabajo original. En el futuro, `licensed_api` sustituirá la captura manual sin modificar las etapas posteriores.

Nunca se copiarán de forma silenciosa reglas de pago, métricas o código. Los resultados publicados se conservarán como evidencia externa y permanecerán separados de los resultados reproducidos por QAF.

## Uso actual

Copiar `docs/sources/strategy_candidate.template.json`, completar la ficha y ejecutar:

```powershell
.\.venv\Scripts\python.exe -m qaf.cli catalog-add ruta\candidato.json
.\.venv\Scripts\python.exe -m qaf.cli catalog-list
```

Cuando `investigator` termine, copiar `docs/sources/evidence_review.template.json`, completar la revisión y ejecutar:

```powershell
.\.venv\Scripts\python.exe -m qaf.cli catalog-review IDEA-XXXXXXXXXX ruta\revision.json
.\.venv\Scripts\python.exe -m qaf.cli catalog-promote IDEA-XXXXXXXXXX
```

`catalog-review` conserva la evidencia y cierra la tarea de investigación. `catalog-promote` crea de forma idempotente la fila de `config/hypotheses.json`, el documento en `docs/hypotheses/`, actualiza el registro legible y pone una sola tarea de contrato en la cola de `protocol`. Todavía no genera una estrategia ni ejecuta un backtest.
