# Automatización del catálogo de ideas

## Propósito

El catálogo alimenta a los agentes con ideas investigables. Una entrada del catálogo no es una estrategia validada y no puede entrar directamente al motor.

## Flujo

1. **Descubrimiento por lotes:** cuando Alexander lo decida, `source-sync` consulta las fuentes automáticas habilitadas y conserva solo metadatos.
2. **Captura idempotente:** guardar un snapshot con hash real y crear una sola ficha por identidad estable (DOI, URL o repositorio/ruta).
3. **Triaje automático:** medir completitud, coincidencia con el universo, marco temporal y requisitos de datos.
4. **Revisión de evidencia:** el investigador localiza la fuente primaria y separa reglas publicadas de interpretaciones.
5. **Decisión metodológica explícita:** registrar una revisión estructurada que rechaza, bloquea por datos o declara elegible la idea.
6. **Contrato:** el agente de protocolo crea una especificación congelada.
7. **Validación QAF:** ejecutar IS, puertas estadísticas y, cuando corresponda, OOS.

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

## Extracción periódica, no en tiempo real

No existe un servicio permanente ni un cron obligatorio. La extracción se ejecuta manualmente cuando se quiera revisar novedades:

```powershell
.\.venv\Scripts\python.exe -m qaf.cli source-sync --limit 20
```

También puede limitarse a una fuente o inspeccionarse sin escribir:

```powershell
.\.venv\Scripts\python.exe -m qaf.cli source-sync --provider arxiv_qfin --limit 10
.\.venv\Scripts\python.exe -m qaf.cli source-sync --provider quantconnect_lean_examples --limit 10 --dry-run
```

El comando:

- guarda snapshots inmutables en `catalog/discoveries/<provider>/`;
- crea candidatos nuevos en `catalog/candidates/` y los asigna a `investigator`;
- no descarga PDFs ni copia código fuente completo;
- no extrae reglas con un LLM, no elige instrumentos y no inventa parámetros;
- no sobreescribe un candidato existente: si cambian los metadatos, crea una tarea `evidence_refresh`;
- nunca promueve hipótesis, registra estrategias ni ejecuta backtests.

### Identidad y detección de cambios por conector

| Conector | Identidad del candidato | Qué dispara `evidence_refresh` | Qué NO la dispara |
|---|---|---|---|
| arXiv | ID sin versión (`2401.12345`); URL canónica `https://arxiv.org/abs/<id>` | nueva versión (`v1 → v2`), título o autores | cambio de `updated` sin nueva versión |
| Crossref | DOI en minúsculas | cambios de título, autores, fecha, revista o tipo | — |
| GitHub | `owner/repo:ruta` | cambio de contenido del archivo (`blob_sha`) | un commit nuevo del repositorio que no toca el archivo |

La huella (`metadata_sha256`) excluye `source_url` y `source_revision`, que cambian con cada commit o subida sin que cambie el contenido. El snapshot conserva el commit donde se vio por primera vez cada contenido, así que la referencia sigue siendo reproducible.

### Calidad de las fuentes (verificado con consultas reales el 2026-09-22)

- **arXiv q-fin.TR:** pertinente, con temas fuera de alcance (microestructura, cripto, prediction markets) que `investigator` debe rechazar.
- **Crossref:** solo sirve ordenado por relevancia, con `until-pub-date` = hoy y `type:journal-article`. Ordenado por fecha de publicación devolvía marketing, medicina y registros "Title Pending" con fechas de 2036-2115. Un mismo trabajo puede aparecer con varios DOI en revistas distintas; la deduplicación por DOI no lo detecta y queda para `investigator`. `access_level` queda `unknown`: un DOI no garantiza acceso abierto.
- **QuantConnect LEAN (`Algorithm.Python/`):** es sobre todo una suite de regresión y demos de la API (236 de 460 archivos contienen "Regression"). Con `include_regex` de palabras de estrategia y `exclude_regex` de regresiones y opciones quedan unos 10 archivos, varios fuera de alcance (rotación de cartera, pares de acciones). Rendimiento bajo como cantera; útil como código de referencia.
- El `--limit` corta la lista que devuelve cada fuente; no pagina. arXiv y Crossref devuelven lo más reciente o relevante en cada corrida; GitHub devuelve siempre los mismos archivos en orden alfabético.

`QAF_CONTACT_EMAIL` es opcional para identificar respetuosamente las consultas a Crossref. `GITHUB_TOKEN` es opcional para ampliar el límite público de GitHub; ninguna credencial se guarda en el repositorio.

## Fuentes manuales

Quantpedia, Alpha Architect y SSRN quedan en modo `manual_only`. Se pueden registrar referencias revisadas por una persona y seguirlas hasta el trabajo original, pero `source-sync` no las raspa.

Nunca se copiarán de forma silenciosa reglas de pago, métricas o código. Los resultados publicados se conservarán como evidencia externa y permanecerán separados de los resultados reproducidos por QAF.

## Captura manual

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

La fuente de verdad del catálogo es `catalog/candidates/`, versionada por Git. `state/` contiene únicamente la cola SQLite y otros datos operativos descartables.
