# Método TIS — Filosofía del proyecto

Fuente: extracción propia (NotebookLM) del contenido gratuito de una trader algorítmica, 2026-09. Aquí solo se documenta la parte metodológica/técnica — se omite el contenido comercial de su mentoría.

## Principio: la IA como obrero, no como pensador
Un LLM es un predictor estocástico de texto: sesgado, no fiable generando ideas o estrategias "de la nada". Es fiable cuando ejecuta código determinista (Python) dentro de un sistema delimitado, con reglas, datos y puertas de validación explícitas. Por eso este proyecto restringe a cada agente a una función concreta (ver [CLAUDE.md](../CLAUDE.md)) en vez de pedirle a un chat sin contexto "dame una estrategia rentable".

## Regla de codificación
"Si una estrategia no se puede escribir en código, no existe." Toda regla de entrada/salida/riesgo debe ser numérica y no ambigua.

## Métrica central: Expectancy
Resultado promedio de operaciones ganadoras vs. perdedoras, ajustado por la máxima pérdida sostenida. Indica si existe edge real, no solo una curva bonita.

## Flujo estándar (8 fases)
1. **Hipótesis con lógica de comportamiento** — por qué existe la ineficiencia y por qué nadie la arbitró ya.
2. **AED (Análisis Exploratorio de Datos)** — confirmar estadísticamente que el patrón existe antes de programar reglas.
3. **Definición de reglas** — entrada, salida, riesgo, todo numérico.
4. **Backtest** — simulación histórica.
5. **Optimización** — ajuste delimitado, sin sobreajuste.
6. **Pruebas de robustez** — Montecarlo, Out-of-Sample, permutación.
7. **Sizing** — capital y lotaje según riesgo permitido.
8. **Deploy** — incubación y ejecución en VPS (fuera de alcance de este proyecto hasta aprobación explícita, ver CLAUDE.md regla 1-2).

## Riesgo de minería sin hipótesis
Herramientas de minería masiva de estrategias (ej. StrategyQuant) sin AED previo producen sobreajuste: curvas óptimas en backtest que quiebran en real porque no tienen valor predictivo. Este proyecto exige AED (fase 2) antes de aceptar cualquier regla (fase 3) — sin saltarse el orden.

## Glosario rápido
- **IS/OOS**: In-Sample (para diseñar) / Out-of-Sample (solo para validar, nunca para optimizar). Default 70/30.
- **Agente**: chat con capacidad de ejecución — lee archivos, corre código, itera.
- **Skill**: instrucciones o script especializado que un agente consulta antes de una tarea puntual.
- **Harness**: entorno de control que combina reglas duras + skills + validaciones + agentes para restringir al LLM.
- **Grafo**: lógica condicional de qué hacer según el resultado (ej. qué pasa si el backtest no cumple el profit factor mínimo).
- **MCP**: conector estandarizado entre el agente y sistemas externos (archivos, APIs, bases de datos).

## Niveles de madurez (referencia)
1. Chat básico
2. Generación de código en chat
3. Repositorio con control de versiones
4. Sistema agéntico (subagentes ejecutando tareas) ← **este proyecto arranca aquí**
5. Arnés completo (grafos de decisión, validación cruzada automática, producción)

## Stack mencionado en el video (no confirmado para este proyecto)
Datos: Norgate Data (pago, institucional). Herramientas: StrategyQuant, MultiCharts, TradeStation. Ver OPEN QUESTIONS en [PROJECT_STATE.md](../PROJECT_STATE.md) — todavía no decidimos con qué datos arrancamos aquí.

## Autores citados como fuente de hipótesis
- **Perry Kaufman** — *Trading Systems and Methods*; modelos adaptativos (KAMA), diseño de sistemas.
- **Linda Raschke** — patrones de reversión a la media y dinámicas de volatilidad.
