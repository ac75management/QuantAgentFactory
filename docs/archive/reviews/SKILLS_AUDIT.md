# Auditoría de skills — QuantAgentFactory

Fecha: 2026-09-22

## Regla de decisión

Un skill pertenece al repositorio únicamente cuando define una tarea cuantitativa repetible, específica de este proyecto, con entradas, salida y condiciones de detención claras. Tener más skills no implica tener mejores agentes. Las instrucciones duplicadas o ambiguas aumentan contradicciones y consumo de contexto.

## Inventario local real

| Elemento | Tipo | Decisión | Motivo |
|---|---|---|---|
| `.claude/skills/data-quality-check/SKILL.md` | Skill cuantitativo | **Conservar y actualizar** | Gate 0 es obligatorio y específico del proyecto |
| `.claude/agents/investigator.md` | Rol | **Conservar como agente** | Investiga y documenta hipótesis |
| `.claude/agents/protocol.md` | Rol | **Conservar como agente** | Convierte hipótesis en contrato |
| `.claude/agents/engine.md` | Rol | **Conservar como agente** | Opera el runner determinista |
| `.claude/agents/validator.md` | Rol | **Conservar como agente** | Revisa evidencia y holdout cuando exista |

No existe un skill llamado `I have ADHD` dentro de este repositorio. Tampoco existe aquí una colección de skills de trading descargados.

## Skills globales o descargados

Se mantienen fuera del proyecto y se invocan solo cuando corresponda:

- **Apoyo ADHD/productividad:** reduce carga, ordena opciones y señala el siguiente paso. No modifica contratos, métricas, gates ni veredictos.
- **Pine Script:** se usa únicamente después de aprobar una estrategia y decidir exportarla a TradingView.
- **Análisis estadístico/datos:** sirve para una auditoría concreta. Las reglas de aceptación viven en `qaf`, con tests y versiones.
- **Documentos, PDF, hojas y presentaciones:** son herramientas de entrega; no forman parte del pipeline cuantitativo.
- **Skills financieros contables:** no son skills de trading algorítmico y no se incorporan.
- **Creadores/instaladores de skills:** se usan solo al crear o instalar uno; no son dependencias del motor.

## Skills cuantitativos futuros permitidos

No se crearán por adelantado. Solo se justifican cuando exista una tarea repetida que dependa de instrucciones manuales:

1. `evidence-intake`: valida dossiers externos y citas antes de registrarlos.
2. `hypothesis-triage`: clasifica una idea como documentable, bloqueada o duplicada, sin inventar reglas.
3. `report-review`: comprueba que un reporte contiene todos los artefactos obligatorios.

AED, baseline, permutación, walk-forward, costos, sizing y gates **no deben ser skills narrativos**. Son funciones deterministas del motor con pruebas.

## Riesgos encontrados

El skill Gate 0 mezclaba referencias históricas a `docs/cost_model.md` y `cost_key` con la implementación vigente, cuya fuente contractual es `config/instruments.json`. También describía un reporte Markdown separado cuando el runner ya guarda los checks en `result.json` y `report.html`. Se actualiza para que el agente no pueda llegar a una conclusión distinta del código.

## Política final

- Skills personales cambian la presentación y organización para Alexander.
- Skills del repositorio describen tareas específicas que el código todavía no puede expresar por sí solo.
- Código y contratos gobiernan dinero, causalidad, datos, costos y veredictos.
- Un skill nuevo requiere activador, entradas, salidas, prohibiciones y prueba de que no duplica otro componente.
