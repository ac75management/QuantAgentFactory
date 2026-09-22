# Revisión de nuevas fuentes de investigación

Fecha: 2026-09-22

## Dictamen

Las fuentes mejoran QuantAgentFactory si funcionan como índices de descubrimiento sometidos a una revisión de fuente primaria. No deben clonarse, instalarse ni importarse masivamente al motor. El cuello de botella útil es la calidad de las hipótesis que llegan a validación, no la cantidad de PDFs almacenados.

## 1. Awesome LLM Quantitative Trading Papers

**Qué es:** lista curada de trabajos sobre agentes de trading, benchmarks financieros, minería de factores, forecasting y evaluación de LLM. Su licencia CC BY 4.0 cubre la lista; cada paper o repositorio enlazado conserva sus propios derechos.

**Qué aporta:** arquitectura de agentes, pruebas contra alucinación, benchmarks de generación de estrategias, memoria y debate multiagente. Puede ayudarnos a evaluar cómo investigan los agentes.

**Qué no aporta directamente:** una biblioteca madura de reglas sencillas para CFDs de Darwinex. Gran parte se concentra en acciones, cripto, predicción, aprendizaje por refuerzo o sistemas recientes con requisitos de datos y cómputo superiores a QAF.

**Destino:** `agent_research`. Priorizar surveys y benchmarks de fiabilidad antes que instalar frameworks o adoptar modelos de trading autónomo.

**Decisión operativa:** aparcado y deshabilitado como fuente activa. No genera tareas en la campaña actual.

## 2. Quant Research Paper Dump

**Qué es:** depósito amplio de documentos organizado por años, con temas de estrategias, cartera, machine learning, fintech y macroeconomía. El repositorio advierte que deben respetarse autoría y propiedad intelectual, pero no presenta en su portada un proceso fuerte de selección o verificación individual.

**Qué aporta:** cobertura histórica y posibilidad de encontrar fuentes olvidadas.

**Riesgos:** duplicados, papers irrelevantes, versiones no definitivas, ausencia de metadatos homogéneos, derechos variables y fuerte coste de lectura. La presencia de un PDF no prueba calidad, reproducibilidad ni permiso de redistribución.

**Destino:** `broad_paper_discovery`, con prioridad baja. Extraer primero metadatos; abrir el documento solo cuando título/resumen encaje con un hueco concreto del catálogo.

**Decisión operativa:** descartado de la ingesta activa. Solo se consultará puntualmente si una búsqueda dirigida conduce a un documento concreto.

## 3. Alpha Architect

**Qué es:** blog de investigación y análisis secundario con archivos sobre value, momentum, trend, costes, construcción de cartera, factores y robustez.

**Qué aporta ahora:** evidencia contradictoria, problemas de implementación, costes, capacidad, decaimiento y construcción de cartera. Sus artículos suelen señalar el paper original y ayudan a decidir si una idea merece réplica.

**Qué no es:** un sistema matemático autoritativo de descarte. Sus artículos son evidencia secundaria y parte de su investigación está orientada a acciones, ETF y carteras long-only; no se transfiere automáticamente a CFDs individuales.

**Destino:** `methodology` para costes, robustez y sesgos; `strategy` únicamente cuando exista una regla reproducible y una fuente primaria rastreable.

## Responsabilidad de agentes

No se crea un quinto agente todavía.

| Etapa | Responsable | Resultado |
|---|---|---|
| Captura y triaje mecánico | `qaf/catalog.py` | prioridad, bloqueos y carril |
| Lectura y verificación de fuente | `investigator` | dossier de evidencia |
| Reglas numéricas congeladas | `protocol` | spec narrativa y JSON |
| Datos, costes y simulación IS | `engine` | artefactos reproducibles |
| Crítica y decisión | `validator` | veredicto sin reinterpretar métricas |

Un agente recolector separado solo se justificará cuando haya un trabajo programado, repetitivo y medible de cientos de entradas. Antes de eso duplicaría a `investigator` y añadiría coordinación sin mejorar la evidencia.

## Filtro de admisión

Cada idea debe registrar:

1. fuente índice y fuente primaria;
2. clase de activo, vehículo y ticker originales;
3. timeframe, frecuencia de decisión y holding;
4. datos requeridos y disponibilidad real;
5. reglas publicadas y ambigüedades;
6. costes y supuestos del estudio original;
7. mecanismo económico o conductual;
8. diferencia entre réplica y adaptación;
9. coincidencia con MT5 ahora o carril futuro;
10. derechos de acceso al documento o código.

## Orden recomendado

**AHORA:** mantener Quantpedia y Alpha Architect como fuentes de mayor señal. El repositorio LLM queda aparcado y el depósito de papers queda fuera de la ingesta activa. Seleccionar un máximo de diez candidatos por campaña.

**SIGUIENTE:** hacer un piloto de cinco candidatos `mt5_now`, dos metodológicos y dos de arquitectura de agentes. Medir cuántos terminan con fuente primaria y reglas reproducibles.

**DESPUÉS:** automatizar revisión periódica de índices. La API de Quantpedia puede reemplazar la entrada manual cuando se contrate, sin cambiar las puertas posteriores.

## Criterio de éxito

La ampliación sirve si aumenta el porcentaje de hipótesis con reglas trazables y datos disponibles. Si solo aumenta PDFs, ideas pendientes o familias que el motor no puede ejecutar, está empeorando el sistema y debe reducirse la ingesta.
