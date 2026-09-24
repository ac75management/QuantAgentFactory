# Instrucciones para Codex — QuantAgentFactory

**CRÍTICO: Leer antes de cada sesión de trabajo**

Versión: 1.0  
Última actualización: 2026-09-24  
Razón: Codex se quedó sin tokens (2026-09-24) porque no compactaba sesiones.

---

## REGLA 1: `/COMPACT` OBLIGATORIO — NO NEGOCIABLE

**Cuándo:**
- Después de completar CUALQUIER investigación, reporte o tarea
- Después de cada conversación importante (no esperar a que sea perfecto)
- Si ya usaste más de 40,000 tokens en la sesión actual

**Cómo:**
```
/compact
```

**Propósito:** Resumir contexto sin perder estado. Ahorra 30-50% de tokens por sesión.

**Si NO lo haces:**
- Sesión anterior queda consumida (tokens perdidos)
- Tarea bloqueada cuando se acaban tokens
- Alexander espera, proyecto se detiene

---

## REGLA 2: Monitoreo de tokens

**Observa en cada respuesta:**
- Línea con `<total_tokens>XXXX tokens left</total_tokens>` al final
- Si baja de 100,000: **COMPACTA INMEDIATAMENTE**
- Si baja de 50,000: pausa, comunica a Alexander, prepara `/compact`

**Aviso anticipado:**
- Si vas a quedar sin tokens antes de terminar: reporta aquí en AGENTS.md
  ```
  ### 2026-09-24 HH:MM — Codex: PAUSA por tokens bajo
  - Tokens restantes: 45,000
  - Tarea: [qué estaba haciendo]
  - Estado: [dónde paré]
  - Próximo: necesita `/compact` antes de continuar
  ```

---

## REGLA 3: Ciclo de trabajo Codex

**Cada sesión de Codex:**
1. Revisa AGENTS.md / PROJECT_STATE.md
2. ¿Hay orden nueva? → ejecuta
3. Reporta resultado aquí en AGENTS.md (3-5 líneas máximo)
4. **EJECUTA `/compact`**
5. Espera siguiente ventana (15-20 min)

**Nunca:**
- Dejes sesión sin `/compact`
- Trabajes más de 1 hora sin compactar
- Ignores avisos de tokens bajo

---

## REGLA 4: Dónde leer órdenes

**Órdenes nuevas de Alexander aparecen aquí:**
1. `AGENTS.md` → "Hallazgos cruzados" (sección de arriba)
2. `PROJECT_STATE.md` → `NEXT ACTION`
3. Si hay orden clara: clama el archivo, trabaja, reporta

**Ejemplo de orden:**
```
### 2026-09-24 — ORDEN DE ALEXANDER PARA CODEX: Auditoría de infraestructura

**Para:** Codex
**Acción:** Extrae datos EURUSD/H1, calcula RSI, compara vs. qaf
**Resultado esperado:** data/audit/*.json
```

---

## REGLA 5: Coordinación con Claude

**No duplices trabajo:**
- Si Claude está triando candidatos, tú NO trias
- Si tú estás en auditoría, Claude NO audita
- Comunica en AGENTS.md qué estás haciendo

**Intercambio de datos:**
- Tú: extrae datos, corre backtests → archivos JSON en `data/audit/`
- Claude: revisa archivos → propone diagnóstico
- Sincroniza cada 15-20 min

---

## REGLA 6: Si se acaban tokens (EMERGENCIA)

**Si llegas a < 10,000 tokens:**
1. PAUSA inmediatamente
2. Escribe aquí en AGENTS.md:
   ```
   ### CODEX EMERGENCIA: SIN TOKENS
   - Tokens: 5,000
   - Tarea: [qué hacía]
   - Estado guardado: [dónde paré, archivos guardados]
   - Esperando /compact desde Alexander
   ```
3. **NO continúes** sin `/compact`
4. Espera a Alexander

---

## Checklist de inicio (cada sesión)

Antes de trabajar, verifica:
- [ ] Leí AGENTS.md — ¿hay orden nueva?
- [ ] Leí PROJECT_STATE.md — ¿hay NEXT_ACTION para mí?
- [ ] Tokens disponibles: > 100,000
- [ ] Guardé resultado previo (si lo hay)
- [ ] Estoy listo para `/compact` al terminar

---

## Contacto

Si algo está bloqueado o confuso:
- Escribe en AGENTS.md → "Hallazgos cruzados"
- Claude te responde en la próxima ronda
- Alexander decide si hay cambio

---

**Recordatorio final:**

El proyecto QuantAgentFactory necesita que Codex Y Claude trabajen juntos SIN gastar tokens innecesarios. **`/compact` es la herramienta clave.** Úsala después de cada ciclo.

**Frase clave:** "Al terminar, `/compact`. Siempre."
