# Opinión crítica: enfoque de IA del curso FINC-B8420

**Hecho auditado (Grok):** en el curso, la IA solo asiste al código (Claude Code / Codex) para depurar y explicar. No es un sistema multiagente.

1. Es un uso correcto y prudente: la IA acelera el código y el humano mantiene el juicio de inversión.
2. No es mejor que lo que QAF ya hace. Es un **subconjunto**: QAF ya usa IA para codificar (Codex) y además la ata a prompts disciplinados, reglas duras, tests (~191) y gates que fallan cerrados.
3. En el curso, lo que evita el autoengaño es el rigor del alumno y del profesor. En QAF lo evita la infraestructura: registry append-only, partición sellada, OOS bloqueado en código.
4. El curso no aporta ningún control que QAF no tenga para sesgo de IA, alucinación de fuentes ni sobreajuste por iteración con el LLM.
5. Riesgo que sí comparten: usar la IA para "explicar" un resultado puede generar racionalizaciones a posteriori. QAF ya lo mitiga: cambiar una regla después de ver resultados crea una hipótesis nueva con otro ID.
6. Lo único transferible es un hábito que QAF ya practica: pedir a la IA que explique el código antes de confiar en él (auditoría cruzada Codex↔Claude↔Grok).
7. No justifica tocar la orquestación, sumar agentes ni cambiar el flujo actual.

**Recomendación: PARK.** No adoptar nada del enfoque de IA del curso. Se mantienen los prompts disciplinados, los tests y los gates actuales. El valor de Paleologo para QAF está en el contenido conceptual (`edge_filter.md`, `pipeline_map.md`), no en su uso de IA.
