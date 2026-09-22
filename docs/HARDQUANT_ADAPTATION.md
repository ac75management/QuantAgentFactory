# Evaluación de HardQuant y adaptación para QuantAgentFactory

Fecha de revisión: 2026-09-22

## Dictamen

**Valor de la idea: 8/10. Evidencia verificable disponible: 5/10. Adaptación directa a QAF: 7/10.**

La biblioteca normalizada, la comparación antes/después de publicación y la
trazabilidad de reglas son aportes de alto valor. Las capturas y el hilo no
permiten auditar datos, código, costes, sesgos ni cifras; por eso sus resultados
son una referencia de producto e investigación, no evidencia para adoptar una
estrategia.

QAF ya tiene controles que no deben debilitarse para parecerse a la interfaz:
costes por contrato, Gate 0, separación IS/OOS, registro de ensayos, diagnósticos
y decisiones de descarte. La adaptación correcta es presentar esa evidencia con
la claridad de HardQuant.

## Qué se incorpora

1. Biblioteca filtrable con estrategia, instrumento, marco, decisión, operaciones,
   retorno neto, drawdown, profit factor, fricción y reporte.
2. Ficha individual con reglas, parámetros, reservas, procedencia, curva, puertas
   y artefactos reproducibles.
3. Catálogo de fuentes públicas y estrategias fallidas, no solamente ganadoras.
4. Comparación pre/post publicación cuando la fecha y el historial lo permitan.
5. Correlaciones y ensembles únicamente entre resultados admisibles y comparables.

## Qué no se copia

- CAGR, Sharpe o Sortino sin anualización definida para cada marco temporal.
- Matrices construidas con retornos que no comparten fechas suficientes.
- Optimización de pesos sobre las mismas observaciones usadas para seleccionar
  estrategias.
- Botón de live trading desde investigación.
- Código generado por agentes que omita la especificación y las puertas.

## Contrato mínimo para extraer una estrategia

Cada fuente debe producir un registro estructurado antes de crear código con:

- título, autor, URL primaria, fecha de publicación y fecha de consulta;
- tipo de fuente, universo y marco temporal originales;
- reglas literales de entrada, salida y sizing;
- costes declarados por la fuente;
- ambigüedades y adaptaciones necesarias;
- estado de réplica: literal, adaptada o inspirada;
- referencias archivadas de forma permitida;
- estado de revisión: capturada, revisada, aprobada para spec o rechazada.

Un agente puede recopilar y resumir. Otro debe contrastar el registro con la
fuente primaria. Solo después protocol puede convertirlo en hipótesis y spec.
El backtest no debe aceptar reglas inferidas silenciosamente.

## Pre/post publicación

Esta vista necesita una decisión del propietario del proyecto: QAF usa actualmente
IS/OOS como barrera contra selección. La fecha de publicación estudia erosión y
replicabilidad, pero no reemplaza OOS. Se recomienda mostrar cuatro segmentos
cuando los datos lo permitan:

1. periodo anterior a la publicación;
2. periodo posterior a la publicación dentro de IS;
3. OOS sellado;
4. seguimiento futuro sin reoptimización.

La publicación se excluye del corte y toda adaptación posterior queda versionada.

## Orden de construcción

**Ahora:** biblioteca visual basada en datos reales, ficha clara y contrato de
fuentes.

**Siguiente:** incorporar metadatos de fuente en el contrato de estrategia y un
flujo de captura/revisión.

**Después:** métricas anualizadas bien definidas, pre/post publicación y
correlaciones con mínimo de solapamiento.

**Más tarde:** ensembles con política pre-registrada y validación propia. La
automatización de trading en vivo queda fuera hasta validar datos, ejecución y
riesgo operativo.
