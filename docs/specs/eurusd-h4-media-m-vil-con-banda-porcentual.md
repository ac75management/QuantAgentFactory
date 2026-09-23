# Spec: eurusd-h4-media-m-vil-con-banda-porcentual

**Estado: BLOQUEADA — contrato JSON no generado.**

- Hipótesis: `008`.
- Objetivo: EURUSD / H4.
- Fuente registrada: Perry J. Kaufman, *Trading Systems and Methods*, 5th Edition.
- Tipo: adaptación desde un sistema diario genérico multi-activo a EURUSD H4 CFD.
- No se abrió OOS ni se ejecutó un backtest.

## Regla cualitativa sustentada

La evidencia disponible describe una media móvil con una banda porcentual simétrica. Una penetración de la banda superior indica largo y una penetración de la banda inferior indica corto. El objetivo de la banda es reducir cambios de dirección causados por ruido alrededor de la media.

## Bloqueantes del contrato

1. **Periodo de la media (`N`)**: no está verificado en el texto primario.
2. **Ancho de la banda (`P%`)**: no está verificado en el texto primario.
3. **Tipo de media e inicialización**: la revisión dice "media suavizada", pero no congela una definición numérica reproducible.
4. **Ejecución y salida**: la fuente secundaria enumera varias variantes; no existe una regla única verificada que determine fill, salida, stop, take profit o tiempo máximo.
5. **Arquitectura**: `qaf` no implementa la familia precio contra media ± banda porcentual. `trend_cross` compara dos medias y no representa esta regla.
6. **AED y sizing**: sin salida ni stop verificados no se puede fijar el horizonte del AED ni un riesgo por operación coherente.

Los valores 10 y 3% mencionados por fuentes secundarias no se adoptan. Elegirlos por popularidad o por el resultado del IS convertiría la investigación en selección de parámetros no contabilizada.

## Contrato previsto

| Campo | Valor | Estado |
|---|---:|---|
| `id` | `eurusd-h4-media-m-vil-con-banda-porcentual` | congelado |
| `symbol` | `EURUSD` | congelado |
| `timeframe` | `H4` | congelado como adaptación |
| `direction` | `both` | sustentado cualitativamente |
| `family` | media con banda porcentual | no implementada |
| periodo/tipo de media | — | pendiente de fuente primaria |
| ancho porcentual | — | pendiente de fuente primaria |
| entrada/fill | — | pendiente |
| stop/salida | — | pendiente |
| riesgo/sizing | — | pendiente |

## Decisión

La hipótesis se bloquea con `RULES_UNDERSPECIFIED_AND_FAMILY_NOT_IMPLEMENTED`. No se crea `docs/specs/eurusd-h4-media-m-vil-con-banda-porcentual.json`, porque hacerlo exigiría inventar parámetros o forzar la regla dentro de una familia distinta.

## Qué la desbloquea

1. Una referencia verificable a la edición y página de Kaufman que fije periodo y tipo de media, ancho de banda, momento de entrada, salida y control de riesgo.
2. Una decisión de Alexander para implementar la familia solo después de tener esa regla completa.
3. Un nuevo paso de `protocol` que genere el JSON sin consultar resultados IS para elegir valores.

