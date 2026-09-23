# Spec: eurusd-h1-intraday-reversal-currency-markets-alpha

**Estado: contrato generado por `protocol`; pendiente de registro, Gate 0 y backtest IS. No es una estrategia validada.**

- Hipótesis: `009`.
- Fuente primaria: implementación fijada de QuantConnect LEAN, commit `88bce0fc6f`, que cita a LeBaron & Zhao, *Foreign Exchange Reversals in New York Time*.
- Adaptación: EURUSD H1 en CFD retail, con costos y ejecución del contrato QAF.
- OOS no se abrió y ningún resultado se usó para elegir parámetros.

## Regla de entrada congelada por la fuente

En cada barra H1 con timestamp consciente de zona horaria se calcula la SMA simple de 5 cierres. La dirección es **larga** si `close < SMA(5) × 1.001` y **corta** en caso contrario. Solo se emite una señal cuando la dirección difiere de la última dirección observada dentro del flujo de señales. Las señales se evalúan únicamente entre 10:00 y 15:00 inclusive, en `America/New_York`; el cálculo aplica DST de la zona IANA, no la zona del equipo.

La señal del cierre de `t` se ejecuta al open de `t+1`. Si ese open ya cae después de la expiración de 15:01 NY en el mismo día, no se abre la operación: se registra como `session_expired`. En datos H1, la salida de 15:01 se representa por el primer open disponible posterior, normalmente 16:00 NY.

## Gestión de riesgo y salida de adaptación

La fuente LEAN no publica stop ni take-profit. Para no dejar una simulación sin control de riesgo, antes de mirar IS se congela esta adaptación del proyecto:

- `ATR(14)` causal calculado hasta el cierre de la barra de señal.
- Stop: `1.5 × ATR(14)`.
- Take-profit: `3.0 × ATR(14)`.
- Riesgo: 0.5% del equity por operación, con el sizing y límites del instrumento.
- `max_holding=6` barras como red de seguridad si falta una barra de salida de sesión; no sustituye la salida 15:01.
- Si stop/target y la salida de sesión compiten en el mismo open, el gap de stop/target prevalece; los toques intrabar posteriores no pueden adelantar la salida temporal.

Estos valores son una adaptación estructural documentada, no una optimización. Cambiarlos después de ver IS crea una hipótesis nueva.

La sensibilidad del motor perturba únicamente parámetros numéricos (`atr_period`, `sl_atr`, `tp_atr`, `max_holding`, `sma_period` y `band_fraction`). La zona IANA y los horarios son estructura de sesión: se reportan como fijos y no se multiplican artificialmente por ±10–20%.

## Contrato operativo

El JSON homónimo contiene `family=sma_band_session`, `sma_period=5`, `band_fraction=0.001`, `session_timezone=America/New_York`, `session_start=10:00`, `session_end=15:00`, `exit_time=15:01`, ATR14, SL 1.5, TP 3.0 y `max_holding=6`. `qaf/contracts.py` valida la zona, orden temporal y el requisito H1; `qaf/signals.py` falla cerrado ante timestamps ingenuos; `qaf/engine.py` evita fills expirados y registra `SESSION_EXIT`.

## Datos, costos y puertas

El lote raw disponible de EURUSD/H1 comienza el 2010-08-18, después del corte EURUSD ya sellado el 2010-02-17. `qaf.ingest` lo rechaza con `INSUFFICIENT_BEFORE_FIXED_CUTOFF` para no mezclar cortes ni sobrescribir sellos. Antes de `engine` se requiere reimportación controlada de D1/H4/H1 con un corte común compatible, o una decisión explícita de archivar 009. OOS queda físicamente separado y cerrado. Gate 0 debe confirmar frecuencia, huecos, duplicados, calendario, proveniencia y `price_basis`; `costs_verified=false` mantiene la reserva y bloquea una aprobación final.

La estrategia debe superar el baseline comprar-y-mantener de EURUSD/H1 con el mismo capital 1× y los mismos costos, tener al menos 30 operaciones, `profit_factor > 1.3`, drawdown máximo ≤20%, ratio de fricción ≥3.0, sensibilidad estable y las pruebas de robustez requeridas. `READY_FOR_FROZEN_VALIDATION` significará lista para entrar a validación congelada, nunca validada.
