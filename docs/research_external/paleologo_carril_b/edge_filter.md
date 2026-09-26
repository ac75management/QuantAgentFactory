# Edge Filter – Paleologo (Carril B)

Fuente primaria: Lecture 1, slide 39 (Six mechanisms) + slides 21-27 (Investing vs Trading).

## 1. Distinción Investing vs Trading (slides 21-27)

| Tipo         | Fuente principal de PnL                                      | Rol del trading              | Horizonte                  |
|--------------|--------------------------------------------------------------|------------------------------|----------------------------|
| **Investing** | Información diferencial vs consenso de mercado              | Es un costo                  | Puede ser corto o largo    |
| **Trading**   | Estructura de mercado + preferencias heterogéneas de participantes | Es la fuente de ganancia     | Usualmente más corto       |

Pregunta obligatoria de filtro: **¿Quién está al otro lado del trade?** (slide 34)

## 2. Los 6 mecanismos (literales slide 39)

1. **Pure arbitrage** – inconsistencia de precios (law of one price)
2. **Risk preferences** – compensación por soportar incertidumbre
3. **Liquidity** – proveer inmediatez
4. **Funding** – escasez de capital / funding constraints
5. **Predictable flow** – demanda institucional predecible
6. **Information** – mejores forecasts

## 3. Clasificación de alcance para QAF (interpretación lab)

| Mecanismo          | Alcance QAF          | Motivo / Nota                                              | Acción recomendada     |
|--------------------|----------------------|------------------------------------------------------------|------------------------|
| Pure arbitrage     | Fuera de alcance     | Requiere multi-leg simultáneo y financiación               | PARK                   |
| Risk preferences   | Dentro               | Compatible con risk premia y factor exposure               | KEEP como filtro       |
| Liquidity          | Condicionado         | Solo si horizonte de evento (no market making intradía)    | KEEP condicionado      |
| Funding            | Difícil / costoso    | QAF puede modelar el costo aunque no lo cobre              | KEEP como costo        |
| Predictable flow   | Dentro               | Útil para hipótesis de flujos institucionales              | KEEP                   |
| Information        | Dentro               | Núcleo de la mayoría de hipótesis sistemáticas             | KEEP                   |

**Nota:** Las columnas “Alcance QAF” y “Acción” son interpretación del lab, no del curso de Paleologo.

## 4. Uso operativo en QAF

Antes de registrar una hipótesis nueva, responder:

1. ¿Qué mecanismo de los 6 es la fuente principal de edge?
2. ¿Es Investing o Trading según la definición de arriba?
3. ¿Quién está al otro lado del trade?
4. ¿El mecanismo está en KEEP / KEEP condicionado / PARK según la tabla?

Si cae en PARK → no registrar como experimento activo.
