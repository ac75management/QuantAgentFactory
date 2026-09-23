# Hoja de ruta de validación final (OOS) — QuantAgentFactory

`qaf/holdout.py::freeze` y `validate_final` lanzan `NotImplementedError` a propósito. Este documento es la referencia que ese error apunta — lista lo que falta antes de que abrir Out-of-Sample tenga sentido, no es un checklist opcional.

## Por qué está bloqueado hoy
Todas las series activas (`config/instruments.json`) tienen `costs_verified: false` y reservas explícitas por campo (`price_basis: "unknown"`, `calendar_verified: false`, `provenance_verified: false`). Evaluar OOS con un escenario de costos no verificado gastaría el único intento permitido por estrategia (regla CLAUDE.md 13/`qaf/data.py::load_is`, cada símbolo tiene un corte IS/OOS fijo e inmutable) sobre un modelo que todavía puede estar mal, exactamente el error que ya causó el retiro de los backtests manuales anteriores.

## Pendiente antes de implementar `freeze`/`validate_final` de verdad

1. **Costos históricos variables, no solo el escenario actual.** Hoy `config/instruments.json` es una foto puntual (spread/slippage/swap del momento de la captura). OOS cubre años — el spread y el swap reales variaron en ese tiempo. Sin una serie histórica (o al menos un rango documentado con su fuente), cualquier P&L de OOS es tan poco fiable como los backtests ya retirados.
2. **Calendario contrastado.** `calendar_verified: false` en todos los símbolos — no hay confirmación independiente de qué gaps son fin de semana/feriado esperado vs. feed hole real. `qaf/data.py::inspect_frame` ya marca esto como reserva (`session_calendar`); falta resolverlo, no solo declararlo.
3. **Auditoría de exposición previa entre campañas.** `config/runner.json` trackea `campaign_max_trials`/`daily_max_trials` para esta campaña, pero no hay todavía un mecanismo que sume la exposición de campañas anteriores (si las hubiera) al corregir el p-valor por múltiples pruebas — `qaf/validation.py::diagnose` ya expone `p_campaign_bonferroni_upper_bound` como aproximación, pero es diagnóstico, no una corrección formal.
4. **Referencia mid/bid/ask real.** `price_basis: "unknown"` en todos los símbolos — el fill model asume mid sin confirmarlo. Antes de OOS hay que declarar esto con evidencia, no como supuesto.
5. **Segunda fuente para verificar el histórico (as-of stability).** No implementado — sin esto, un feed que se reescribe silenciosamente no se detectaría.
6. **Walk-forward real (CLAUDE.md regla 18).** `diagnostics.walk_forward` reporta `NOT_IMPLEMENTED`. `fixed_parameter_temporal_folds` son ventanas con parámetros fijos, útiles como diagnóstico de estabilidad, no como walk-forward: no hay reentrenamiento por ventana.
7. **Contrato congelado.** `freeze` debe registrar el hash de spec, costos, datos, política y código antes de abrir OOS, para que el único intento no pueda repetirse con otra configuración. No implementado.
8. **Partición sellada (hecho 2026-09-22).** Las 28 series de `data/clean/manifest.json` tienen sha256 de IS y OOS, esquema y rango temporal (`python -m qaf.partition seal`); `qaf.data.load_is` verifica ambos hashes en cada corrida. Es un sello "trust on first use": prueba que nada cambió desde el sello, no que los archivos eran correctos antes.

## Ya resuelto en el filtro IS (no bloquea OOS, pero es requisito para llegar a `READY_FOR_FROZEN_VALIDATION`)
- AED por permutación de la señal cruda (`qaf/aed.py`, regla 5), calibrado: ~4% de rechazos a α=5% sobre random walks.
- Baseline con mismo símbolo/timeframe/ventana/costos/capital (`qaf/baseline.py`, regla 19).
- Sensibilidad por parámetro ±10/20% + 200 vecinos Montecarlo (regla 14).
- Política de time-stop explícita y probada (`tests/test_engine_timestop.py`).

`qaf/holdout.py::PREREQUISITES` lista los pendientes que el error de bloqueo muestra; mantener esa lista y este documento sincronizados.

## Cuándo se puede reconsiderar
Cuando los puntos 1, 2 y 4 tengan evidencia concreta (no solo el campo puesto en `true` sin respaldo) para el símbolo/timeframe específico que se quiera validar. No hace falta resolver todos los puntos para *todo* el universo a la vez — se puede habilitar símbolo por símbolo, documentando cada uno.

## Mientras tanto
`engine`/`validator` no intentan destrabar esto con un script alterno. Una estrategia que llega a `READY_FOR_FROZEN_VALIDATION` se documenta como tal y queda esperando — no es una falla del pipeline, es el diseño: mejor cero validaciones OOS que una validación sobre un modelo de costos que sabemos que no es correcto todavía.
