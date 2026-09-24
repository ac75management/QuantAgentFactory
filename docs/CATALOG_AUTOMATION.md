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
- **Crossref:** se usa como muestra ordenada por relevancia, dentro de una ventana de fecha de creación y con `type:journal-article`; no se presenta como cosecha completa. Ordenar por publicación devolvía marketing, medicina y registros "Title Pending" con fechas de 2036-2115. Un mismo trabajo puede aparecer con varios DOI en revistas distintas: si coinciden el título normalizado (4 palabras o más) y el apellido del primer autor, el candidato nuevo se crea igual y lleva `provenance.possible_duplicate_of` apuntando al anterior; `investigator` decide si es el mismo trabajo. Nunca se descarta por esa coincidencia, porque título + autor puede colisionar. `access_level` queda `unknown`: un DOI no garantiza acceso abierto.
- **QuantConnect LEAN (`Algorithm.Python/`):** es sobre todo una suite de regresión y demos de la API (236 de 460 archivos contienen "Regression"). Con `include_regex` de palabras de estrategia y `exclude_regex` de regresiones y opciones quedan unos 10 archivos, varios fuera de alcance (rotación de cartera, pares de acciones). Rendimiento bajo como cantera; útil como código de referencia.
- `--limit` cuenta acciones realmente nuevas por proveedor: candidatos creados, tareas recuperadas o refrescos nuevos. Los registros ya procesados no consumen presupuesto.

## Recorrido seguro entre corridas

No existe un cursor universal: cada fuente se recorre según lo que su API puede garantizar.

| Conector | Contrato vigente | Límite reconocido |
|---|---|---|
| arXiv | escaneo completo en cada corrida, ordenado por última actualización; `totalResults`, entradas recibidas e IDs únicos deben coincidir | falla cerrado si el total supera 2.000; la consulta real del 2026-09-22 devolvió 330 |
| Crossref | muestra explícita por relevancia dentro de una ventana de fecha de creación, con siete días de solape y score mínimo | no es una cosecha exhaustiva; cambios de un DOI conocido solo se detectan si vuelve a aparecer en la muestra (`refresh_known_dois: false`) |
| GitHub | árbol completo del commit, paths filtrados y ordenados antes de aplicar el límite | falla cerrado si GitHub responde `truncated: true` o si un blob no tiene SHA válido |

Crossref guarda únicamente el final de la última ventana exitosa en una tabla con versión de esquema dentro de `state/research.sqlite3`. Un cursor ausente usa `initial_created_from` de la configuración; uno corrupto o de versión desconocida falla cerrado. No se conserva un cursor opaco de la API.

### Crossref: recomendación y procesamiento de candidatos

**Recomendación (no es regla):** usar Crossref para la muestra inicial (`initial_created_from` hasta hoy) y no para revisiones periódicas. Medición del 2026-09-22 con la consulta configurada:

- Ventana de 3 años: 429.700 coincidencias; en el top 20 por relevancia, 19 son pertinentes (score 20-29).
- Ventana de una semana: 4.083 coincidencias; en el top 20, unas 5 son pertinentes. Los pertinentes puntúan 12-14 y el ruido 10-16, así que ningún `minimum_score` los separa.

Si aun así se corre de forma periódica, el costo recae en `investigator`. Para mantenerlo bajo, cada candidato de Crossref se procesa en este orden:

1. **Triaje por metadatos, sin abrir el texto completo.** Solo título, revista y autores del snapshot. Se rechaza de inmediato si trata de otro dominio (medicina, marketing, energía eléctrica, gestión) o si queda fuera del alcance de `CLAUDE.md`: scalping o alta frecuencia, rebalanceo de cartera, solo acciones o cripto sin un CFD equivalente, o datos que QAF no tiene.
2. **Rechazo barato.** Una revisión mínima con `catalog-review`: `decision: rejected`, `reviewer`, `reason_code` (`OUT_OF_DOMAIN`, `OUT_OF_SCOPE` o `DATA_UNAVAILABLE`) y una línea en `decision_reason`. Los demás campos solo se exigen para `eligible`.
3. **Solo si pasa el triaje:** revisión completa de evidencia con la plantilla, fuente primaria y distinción entre réplica y adaptación, igual que cualquier candidato.
4. **Posibles duplicados** (`provenance.possible_duplicate_of`): revisar primero el candidato original. Si es el mismo trabajo, rechazar el nuevo con `DUPLICATE_WORK` y apuntar al original.

## Concurrencia, escrituras y recuperación

- Toda corrida que escribe adquiere una única reserva global mediante `qaf.coordination` para `catalog/candidates` y `catalog/discoveries`. Renueva y comprueba la reserva antes de cada escritura; si otro proceso la recuperó, se detiene.
- Candidatos y snapshots se crean de forma exclusiva: nunca reemplazan un archivo existente. Un snapshot solo se crea cuando existe una acción nueva; los duplicados exactos no producen snapshots huérfanos.
- Si la corrida cayó después del snapshot o del candidato, la siguiente valida la huella y reconstruye la tarea determinista que falte.
- Un snapshot existente se vuelve a calcular y comparar con el SHA-256 de su nombre. JSON ilegible, contenido alterado o una huella falsa bloquean la corrida.
- `updates_queued` solo aumenta cuando SQLite creó realmente una tarea nueva. Repetir un refresco ya encolado no consume `--limit`.
- Al terminar una tarea `evidence_refresh`, `investigator` ejecuta `catalog-ack-refresh <candidate_id> <metadata_sha256>`. La huella queda en `provenance.acknowledged_fingerprints`, dentro del candidato versionado; perder SQLite no reabre ese refresco atendido.
- `--dry-run` consulta las fuentes y, si existe, abre el estado en solo lectura. No crea SQLite, reservas, snapshots, candidatos, tareas ni cursores.

La implementación tiene pruebas de drenaje por lotes, deduplicación global, pérdida de reserva, árbol truncado, total incompleto de arXiv, cursor corrupto, snapshot alterado, refresco repetido, recuperación sin SQLite y `dry-run` sin mutaciones. Los tres conectores pasaron además una consulta real de solo lectura el 2026-09-22.

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

`catalog-add` compara las URL declaradas (`source_url` y `primary_source_url`) con las fichas existentes y guarda posibles coincidencias en `assessment.possible_duplicates`; elimina diferencias comunes de mayúsculas del dominio, barra final y parámetros de seguimiento. La alerta es informativa: no bloquea ni rechaza la captura, porque URLs iguales pueden apuntar a versiones o usos distintos y una coincidencia no demuestra identidad de estrategia. Revisa los candidatos señalados antes de investigar o promover.

Cuando `investigator` termine, copiar `docs/sources/evidence_review.template.json`, completar la revisión y ejecutar:

```powershell
.\.venv\Scripts\python.exe -m qaf.cli catalog-review IDEA-XXXXXXXXXX ruta\revision.json
.\.venv\Scripts\python.exe -m qaf.cli catalog-promote IDEA-XXXXXXXXXX
```

`catalog-review` conserva la evidencia y cierra la tarea de investigación. `catalog-promote` crea de forma idempotente la fila de `config/hypotheses.json`, el documento en `docs/hypotheses/`, actualiza el registro legible y pone una sola tarea de contrato en la cola de `protocol`. Todavía no genera una estrategia ni ejecuta un backtest.

La fuente de verdad del catálogo es `catalog/candidates/`, versionada por Git. `state/` contiene únicamente la cola SQLite y otros datos operativos descartables.
