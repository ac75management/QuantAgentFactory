# Costs Status — Current State

**Last updated:** 2026-09-24  
**Status:** Documented; no rebaselining planned.

## Summary
All 10 research instruments have **`costs_verified: false`** and **`price_basis: "unknown"`** in `config/instruments.json`. This is by design: costs are current estimates from the instrument snapshots, not verified against historical data.

## Current Costs (from 2026-09-22 snapshot)

| Instrument | Spread (pts) | Slippage (pts/side) | Commission | Swap Long | Swap Short | Status |
|---|---|---|---|---|---|---|---|
| XAUUSD | 55 | 13.75 | 2.5e-5 (notional) | -62.6 | 35.4 | Estimated |
| XAGUSD | 4.5 | 1.1 | 2.5e-5 (notional) | -0.5 | 0.1 | Estimated |
| EURUSD | 1.2 | 0.3 | 1.0e-5 (notional) | -5.2 | 2.8 | Estimated |
| GBPUSD | 2.0 | 0.5 | 1.0e-5 (notional) | -4.5 | 2.1 | Estimated |
| USDJPY | *(no data)* | *(no data)* | *(no data)* | *(no data)* | *(no data)* | **Missing** |
| NAS100 | 3.0 | 0.75 | 1.5e-5 (notional) | -1.2 | 0.3 | Estimated |
| SP500 | 2.5 | 0.6 | 1.5e-5 (notional) | -1.0 | 0.2 | Estimated |
| US30 | 2.5 | 0.6 | 1.5e-5 (notional) | -0.8 | 0.1 | Estimated |
| DAX | 2.0 | 0.5 | 1.5e-5 (notional) | -0.6 | 0.1 | Estimated |
| WTI | 0.05 | 0.01 | 3.0e-5 (notional) | -0.15 | 0.08 | Estimated |

## Policy
- **No cost rebaselining:** Historical cost estimates are held constant for each hypothesis/family run. Costs do not change post-result.
- **Snapshot versioned:** Each run stores `costs_version: <sha256 of snapshot>` in the registry. This allows backward cost lookup if needed.
- **No 001–011 reopening:** Historical runs (001–006, 009–011) are sealed. Conclusions stand regardless of cost reestimation.
- **Future step:** Only when a strategy passes IS + OOS + validation (→ READY_FOR_FROZEN_VALIDATION) should costs be re-verified against live broker data for deployment.

## Verification Path (deferred)
1. Extract live tick data and L2 order book from MT5.
2. Simulate spreads, slippage, and swap accrual over the same date range as IS.
3. Rerun the strategy with actual costs.
4. If PnL changes meaningfully (>10% of final result), flag the result as "cost-sensitive."

**Not required for:** IS runs, sensitivity analysis, catalog triage, or OOS validation in this phase.
