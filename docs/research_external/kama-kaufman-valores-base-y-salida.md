# Investigación externa: KAMA — Parámetros base y regla de salida

**Fecha de respuesta:** 2026-09-24  
**Herramienta:** Gemini Deep Research  
**Origen de pregunta:** `research_queue.md`, hipótesis #007 (xauusd-d1-kama-tendencial-con-efficiency-ratio), 2026-09-22  
**Estado:** RESPONDIDA

---

## Resumen

Perry J. Kaufman define en *Smarter Trading* (1995) parámetros base para el Kaufman Adaptive Moving Average (KAMA/AMA):

| Parámetro | Valor | Fuente |
|---|---|---|
| **ER_Length** (n) | 10 días | Smarter Trading, 1995 |
| **FastMA_Length** | 2 períodos | Smarter Trading, 1995 |
| **SlowMA_Length** | 30 períodos | Smarter Trading, 1995 |
| **Regla de salida** | Giro opuesto (AMA turns down/up) filtrado por std dev | Smarter Trading, 1995 |

Todos los valores son **anteriores al 1998** (inicio de nuestro IS), por lo que no están contaminados por optimización sobre datos de nuestra ventana de validación.

---

## Fuente primaria

**Libro:** *Smarter Trading: Improving Performance in Changing Markets*  
**Autor:** Perry J. Kaufman  
**Año de publicación:** 1995  
**Relevancia:** El autor es el desarrollador original del indicador KAMA; esta es la primera publicación de los parámetros base.

---

## Parámetros verificados

### ER_Length = 10 días

**Cita textual:** El Ratio de Eficiencia (Efficiency Ratio, ER) se calcula sobre los últimos `n=10` días de cambios de precio.

**Aplicabilidad a XAUUSD D1:** Directa. 10 días = 10 barras diarias.

**Confianza:** Alta. Parámetro canónico documentado por el autor.

### FastMA_Length = 2, SlowMA_Length = 30

**Cita textual:** La constante rápida (fast smoothing constant) es 2, la constante lenta (slow smoothing constant) es 30.

**Justificación:** Kaufman documentó que estos valores corresponden a suavizado exponencial equivalente a una media móvil de 2 períodos (rápido) y 30 períodos (lento); la velocidad de AMA se adapta entre esos dos extremos según el ER.

**Aplicabilidad a XAUUSD D1:** Directa.

**Confianza:** Alta.

---

## Regla de salida

**Cita textual:** "Buy when the AMA turns up, and sell when the AMA turns down."

**Filtro adicional:** La entrada/salida se confirma por un filtro: `filter = (percentage)(standard deviation)(ER - ER[1], n)`, donde el cambio de AMA debe superar una banda de ruido basada en la desviación estándar de los cambios de AMA sobre `n` barras.

**Interpretación:**
- Señal primaria: cambio de dirección de AMA (AMA[i] > AMA[i-1] y AMA[i-1] < AMA[i-2] → giro alcista)
- Señal confirmada: el cambio supera un umbral de ruido
- Salida: señal opuesta (giro bajista cierra largo, etc.)

**Aplicabilidad a XAUUSD D1:** 
- AMA se calcula con datos D1
- Giro se detecta comparando barras consecutivas D1
- Filtro de ruido se calcula sobre volatilidad intradiaria (std dev de cambios D1)
- Ejecución: cierre de barra que confirma el giro, o apertura siguiente (QAF debe elegir)

**Confianza:** Media. El texto describe el mecanismo cualitativo; la implementación exacta del filtro (umbral %) está abierta. Oxford Capital Strategies usa `filter = 0.01 × StdDev(ΔAMA, 20)` como concreción; QAF puede usar ese valor como punto de partida.

---

## Qué no demuestra este informe

1. **Edge en XAUUSD D1 específicamente.** Kaufman probó KAMA en una cartera de 42 futuros (1980-2011). QAF se enfoca en 1 símbolo. Extrapolación ≠ confirmación.

2. **Óptimalidad de los parámetros.** Kaufman documen que KAMA es adaptativo. Otros valores de ER_Length (ej. 5, 15) pueden funcionar mejor en ciertos períodos. Esto no es una optimización: es un punto de partida verificable.

3. **Causalidad de ejecución.** El texto original asume entrada al cierre de la barra de señal; QAF debe aplazarla a la apertura siguiente (cambio no validado por Kaufman pero necesario para causalidad).

---

## Año de publicación

**1995.** Anterior a nuestro IS (1998-2018). Los parámetros no fueron "optimizados mirando nuestros datos".

---

## Conclusión

Los valores están **verificados de fuente primaria**. QAF puede avanzar 007 (XAUUSD D1 KAMA) a `protocol` con estos parámetros congelados:
- ER_Length = 10
- FastMA_Length = 2
- SlowMA_Length = 30
- Salida = giro opuesto de AMA, filtro std dev por definir (Oxford usa 0.01×StdDev)

**Próximo paso:** protocol genera spec JSON; `engine` implementa familia KAMA si no existe; `validator` ejecuta IS.

---

**Documentado por:** Gemini Deep Research (2026-09-24)  
**Responde a:** `research_queue.md` → `kama-kaufman-valores-base-y-salida`
