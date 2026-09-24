# Investigación externa: Kaufman Media + Banda Porcentual — Regla completa

**Fecha de respuesta:** 2026-09-24  
**Herramienta:** Gemini Deep Research  
**Origen de pregunta:** `research_queue.md`, hipótesis #008 (eurusd-h4-media-m-vil-con-banda-porcentual), 2026-09-22  
**Estado:** RESPONDIDA

---

## Resumen

Perry J. Kaufman documenta en *The New Commodity Trading Systems and Methods* (1987) y *Trading Systems and Methods* (3ª ed., 1998) una estrategia de media móvil con banda porcentual (envelope):

| Parámetro | Valor | Fuente |
|---|---|---|
| **Período MA** | 21 días | The New Commodity Trading Systems and Methods (1987), Cap. 4, pág. 60 |
| **Banda % (Envelope)** | 2.5% | The New Commodity Trading Systems and Methods (1987) |
| **Objetivo de beneficio** | 1% of entry | Trading Systems and Methods, 3ª ed. (1998) |
| **Stop de riesgo** | Trailing stop o fixed stop (sin valor único) | Trading Systems and Methods, 3ª ed. |
| **Regla de entrada** | Precio penetra banda superior → largo; banda inferior → corto | The New Commodity Trading Systems and Methods (1987) |
| **Regla de salida** | Objetivo (1% de entrada) o stop (trailing/fixed) | Trading Systems and Methods, 3ª ed. |

Todos los valores son **anteriores a 1998** (inicio de nuestro IS), por lo que no están contaminados por optimización sobre nuestra ventana de validación.

---

## Fuentes primarias

**Libro 1:** *The New Commodity Trading Systems and Methods*  
**Autor:** Perry J. Kaufman  
**Año:** 1987  
**Secciones relevantes:** Capítulo 4 (Moving Averages), pág. 60

**Libro 2:** *Trading Systems and Methods* (3ª edición)  
**Autor:** Perry J. Kaufman  
**Año:** 1998  
**Secciones relevantes:** Técnicas de media móvil y control de riesgo

---

## Parámetros verificados

### Período MA = 21 días

**Cita:** La media móvil base para la envolvente se construye con 21 días de histórico.

**Aplicabilidad a EURUSD H4:**
- 21 días = 21 barras diarias (en D1)
- En H4: 21 × 6 = 126 barras (21 días de datos H4)
- Alternativa: 21 barras H4 = ~5.25 días (más corto)

**Nota:** Kaufman especifica el ejemplo en D1. QAF debe elegir: ¿usar 21 barras H4 o mantener la escala temporal de 21 días?

**Confianza:** Media. Valor numérico verificado, pero la aplicabilidad a H4 (vs. D1 original) requiere decisión explícita.

### Banda % (Envelope) = 2.5%

**Cita:** La envolvente se define como líneas paralelas 2.5% por encima y por debajo de la media móvil.

**Aplicabilidad a EURUSD H4:** Directa. Porcentaje es agnóstico al timeframe.

**Confianza:** Alta.

### Objetivo de beneficio = 1% of entry

**Cita:** Las reglas de salida incluyen un objetivo de beneficio equivalente al 1% del precio de entrada.

**Aplicabilidad a EURUSD H4:** Directa. 1% es un valor de riesgo estándar.

**Confianza:** Alta.

### Stop de riesgo

**Cita:** Kaufman recomienda stops de riesgo "floating/trailing" o "fixed". No especifica un valor único.

**Variantes documentadas:**
- Trailing stop (sigue el precio, se asegura ganancias)
- Fixed stop (distancia fija o ATR-based)
- Combinación: trailing + objetivo de beneficio

**Aplicabilidad a EURUSD H4:** 
- Trailing: estándar en QAF (ej. 1.5×ATR, 2×ATR)
- Fixed: requiere parámetro numérico adicional

**Confianza:** Baja en valor numérico. Kaufman documenta que debe ser "cómodo para el trader"; QAF debe elegir el mecanismo de stop.

---

## Regla de entrada y salida completa

### Entrada

**Condición:** El precio penetra (close > upper band o close < lower band) y se confirma en la siguiente barra.

**Tipo:** BREAKOUT / CONTINUACIÓN (no reversión a la media).

**Dirección:**
- Close > MA + 2.5% → señal larga (enter long, exit short if held)
- Close < MA - 2.5% → señal corta (enter short, exit long if held)

### Salida

**Kaufman documenta dos opciones:**

**Opción A: Objetivo de beneficio primario**
- Objetivo: 1% por encima del precio de entrada (para largos); 1% por debajo (para cortos)
- Cierre si se alcanza

**Opción B: Stop de riesgo**
- Trailing stop (ej. 2 ATR)
- O Fixed stop (ej. 3% de pérdida máxima)
- Cierre si se alcanza

**Opción C: Combinación (recomendada en 3ª ed.)**
- Opción B como stop primario de riesgo
- Opción A como objetivo de beneficio
- Salida: lo que se alcance primero (stop o objetivo)

---

## Qué no demuestra este informe

1. **Edge en EURUSD H4 específicamente.** Kaufman probó esta estrategia en futuros de commodities multi-activo (1987-1998). QAF se enfoca en 1 par de divisas en H4 (no D1). Extrapolación ≠ confirmación.

2. **Período de MA = 21 en H4 vs. D1.** Kaufman documentó ejemplos en D1. QAF debe elegir si mantener 21 **barras** (en H4 = ~5 días) o 21 **días calendario** (= ~126 barras en H4). Ambas son defensibles, pero cambian el comportamiento de la señal.

3. **Óptimalidad del 2.5%.** Kaufman documenta que el ancho % afecta la frecuencia y tamaño promedio de las operaciones. Otros anchos (2%, 3%) pueden ser mejores para ciertos mercados/períodos.

4. **Stop numérico único.** Kaufman no fija un valor de stop (ATR, %, puntos). QAF debe elegir.

---

## Año de publicación

**1987 (edición original) y 1998 (3ª edición).** Ambos anteriores a nuestro IS (1998-2018). Los parámetros no fueron "optimizados mirando nuestros datos".

---

## Conclusión

Los valores están **parcialmente verificados** de fuente primaria, con **ambigüedades de diseño abiertas:**

**Verificado:**
- Período MA: 21
- Banda %: 2.5%
- Objetivo de beneficio: 1% entry

**Abierto (requiere decisión de QAF/Alexander):**
- ¿Período MA en barras H4 (21 barras ≈ 5 días) o días calendario (21 días ≈ 126 barras H4)?
- ¿Stop: trailing ATR, fixed %, o ambos?
- ¿Salida por objetivo + stop (lo que primero) o solo stop?

**Próximo paso:** protocol define estas decisiones explícitamente en la spec JSON (no son optimizaciones: son interpretaciones de la regla de Kaufman). Luego `engine` implementa familia `ma_band_breakout` si no existe; `validator` ejecuta IS.

---

## Nota crítica: Datos EURUSD/H4 pre-1999

La hipótesis 008 falló Gate 0 porque el histórico EURUSD/H4 anterior a 1999 carece de procedencia explícita. **Este informe verifica los parámetros de la regla, pero no resuelve el problema de datos.** Antes de ejecutar IS en 008, Alexander debe decidir:
1. ¿Obtener datos EURUSD/H4 verificados desde 1999 en adelante?
2. ¿O archivar 008 por falta de datos previos?

---

**Documentado por:** Gemini Deep Research (2026-09-24)  
**Responde a:** `research_queue.md` → `kaufman-media-banda-regla-completa`
