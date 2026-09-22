# KAMA tendencial con Efficiency Ratio

Estado: **pendiente de protocolo**. Esta ficha registra una hipótesis investigable; no afirma rentabilidad y no contiene resultados de backtest.

## Trazabilidad

- Hipótesis: `007`
- Candidato: `IDEA-PILOT-KAMA-XAU-D1`
- Fuente primaria: [Kaufman Adaptive Moving Average | Trading Strategy (Setup)](https://oxfordstrat.com/trading-strategies/adaptive-moving-average-2/)
- Autores: Oxford Capital Strategies Ltd, Perry J. Kaufman (desarrollador del indicador)
- Mercado y vehículo originales: 42 futuros estadounidenses de materias primas, divisas, tipos de interés e índices / Cartera multi-activo de futuros
- Objetivo QAF: XAUUSD / D1
- Tratamiento: adaptation
- Regla fuente: `oxford-kama-turn-filter-atr6`
- Dimensiones adaptadas: costs, frequency, instrument, portfolio, session, vehicle

## Evidencia revisada

La fuente presenta una reproducción de una estrategia basada en AMA/KAMA y atribuye el indicador a Smarter Trading. Declara un universo de 42 futuros de materias primas, divisas, tipos e índices durante 1980-2011; especifica una prueba de sensibilidad de ER_Length y FastMA_Length y compara escenarios de fricción cero y 100 USD por vuelta. Esta revisión conserva las reglas publicadas, pero no adopta como evidencia propia sus resultados ni presupone que se transfieran a un CFD individual.

## Mecanismo propuesto

KAMA ajusta su velocidad mediante Efficiency Ratio: responde con mayor rapidez cuando el desplazamiento neto domina el recorrido bar a bar y se ralentiza cuando predomina el ruido. La hipótesis es que un giro confirmado de esa media puede capturar persistencia direccional reduciendo parte de los cambios falsos que sufriría una media de velocidad fija.

## Reglas publicadas que deben conservarse

- Calcular AMA con Efficiency Ratio, media rápida variable y media lenta de longitud 30.
- Definir giro alcista cuando AMA[i] supera AMA[i-1] y AMA[i-1] es inferior a AMA[i-2]; definir simétricamente el giro bajista.
- Confirmar la entrada cuando el desplazamiento desde el extremo del giro supera 0.01 por la desviación estándar de los cambios de AMA de 20 barras.
- La fuente coloca la entrada larga o corta al cierre de la barra que confirma la condición.
- Usar stop de seis ATR de 20 barras y tamaño fraccional fijo del uno por ciento sobre una cartera de futuros.

## Réplica o adaptación

QAF probaría un solo CFD XAUUSD D1 en lugar de una cartera de 42 futuros. La señal debe calcularse con una barra cerrada y ejecutarse como pronto en la barra siguiente; no puede asumir un fill al mismo cierre que revela la señal. Deben sustituirse el calendario, el rollover, el sizing de cartera y los 100 USD por vuelta por el contrato de costos real de XAUUSD. Esta adaptación requiere una familia KAMA nueva y no debe forzarse dentro de trend_cross.

## Ambigüedades todavía abiertas

- La página pública no declara el timeframe de las barras originales.
- La inicialización exacta de la primera AMA no está declarada en la especificación pública.
- La entrada al mismo cierre que confirma el giro no es reproducible causalmente con OHLC de barra y debe desplazarse.
- No se detalla aquí la construcción de series continuas ni el rollover de los futuros originales.

## Datos requeridos

- OHLC D1 de XAUUSD con barras cerradas y orden cronológico verificado.
- Calendario y zona horaria de sesión del CFD documentados.
- Historial suficiente para inicializar KAMA, desviación estándar de 20 barras y ATR de 20 barras.

## Costos y fricciones que el contrato debe modelar

- Aplicar spread, slippage, comisión y swap/rollover de XAUUSD definidos en config/instruments.json.
- La prueba de 100 USD por vuelta de la fuente es evidencia externa y no sustituye el modelo de costos del CFD.
- La ejecución causal debe usar el precio disponible de la barra posterior a la señal.

## Límites de la evidencia

- La fuente pública es una reproducción de la regla atribuida a Kaufman; esta revisión no inspeccionó el texto completo de Smarter Trading.
- Los resultados de una cartera diversificada de 42 futuros no demuestran edge en XAUUSD CFD.
- La fuente explora una cuadrícula amplia de ER_Length y FastMA_Length, por lo que sus gráficos de sensibilidad no deben tratarse como confirmación fuera de muestra.
- QAF todavía no implementa una familia KAMA y el protocolo puede bloquear la hipótesis antes del backtest.

## Decisión de la revisión

La reproducción pública de Oxford especifica cálculo, giro, filtro, entrada, stop y sizing con suficiente detalle para formular una hipótesis falsable. La promoción solo autoriza el trabajo de protocolo: no valida rentabilidad y exige documentar los cambios de cartera de futuros a XAUUSD CFD, de frecuencia no declarada a D1 y de entrada al cierre a una ejecución causal posterior.

Siguiente paso: `protocol` debe convertir esta hipótesis en reglas numéricas congeladas o bloquearla si las ambigüedades impiden una implementación fiel. OOS permanece cerrado.
