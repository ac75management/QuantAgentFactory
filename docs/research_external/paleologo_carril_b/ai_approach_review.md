# Opinión crítica: enfoque de IA del curso FINC-B8420

**Lo que dice el curso (Lecture 1):** como prerrequisito, "use AI tools intelligently, debug, and explain your own code" (slide 3); como herramientas, "use coding tools (Claude Code, Codex, . . . )" (slide 4). Grok confirmó que es asistencia de código, no un sistema multiagente.

1. El uso es correcto y prudente: la IA acelera el código y el alumno responde por él ("explain your own code").
2. No es mejor que lo que QAF ya hace. Es un **subconjunto**: QAF ya usa IA para codificar (Codex) y además la ata a prompts disciplinados, reglas duras, tests (~191) y gates que fallan cerrados.
3. En el curso, lo que evita el autoengaño es el alumno y el profesor. En QAF lo evita la infraestructura: registry append-only, particiones selladas, OOS bloqueado en código.
4. El curso no aporta controles nuevos contra fuentes alucinadas ni contra el sobreajuste por iterar con el LLM, que son los riesgos propios de un lab con agentes.
5. Riesgo compartido: pedir a la IA que "explique" un resultado puede producir racionalizaciones a posteriori. QAF ya lo mitiga: cambiar la regla después de ver resultados crea una hipótesis nueva con otro ID.
6. Lo transferible ya existe en QAF: "explicar tu propio código" equivale a la auditoría cruzada Codex↔Claude↔Grok.
7. La slide 11 ("AI reshapes short-horizon strategies…") es contexto de industria, no método. No justifica sumar agentes ni tocar la orquestación.

**Recomendación: PARK.** No adoptar nada del enfoque de IA del curso. Se mantienen los prompts disciplinados, los tests y los gates actuales. El valor de Paleologo para QAF está en el contenido conceptual (`edge_filter.md`, `pipeline_map.md`), no en su uso de IA.
