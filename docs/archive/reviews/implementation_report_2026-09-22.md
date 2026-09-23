# Informe de implementación — 2026-09-22 (Claude, app de escritorio)

Origen: encargo redactado por Copilot/GPT y pegado por Alexander, con la instrucción de **auditar cada punto contra el código antes de ejecutarlo**. Este informe separa lo que se implementó, lo que se rechazó por incorrecto y lo que sigue pendiente.

## 1. Estado inicial encontrado
- Working tree con muchos cambios sin commit de dos agentes (Claude y GPT/Copilot). Último commit: `8b0f61d`.
- Otro agente (Copilot) **seguía activo** durante todo el trabajo: su orden de detenerse falló ("Write to Agent failed"). Editó `catalog.py`, `dashboard.py`, `test_factory.py`, `PROJECT_STATE.md` y una vez `tests/test_aed.py` (reclamado por Claude); ese cambio era correcto y se conservó (ver `AGENTS.md`, "Hallazgos cruzados").
- `qaf/aed.py` (escrito por Claude en el turno anterior) omitía la puerta cuando el AED era `INCONCLUSIVE` y usaba una nula de barras sueltas que inflaba falsos positivos.
- Baseline de 1 lote fijo: exposición no comparable entre símbolos.
- Sensibilidad: solo SL y TP movidos juntos (incumple CLAUDE.md regla 14).
- Manifest de datos sin hashes ni rangos de IS/OOS.
- Documentación desalineada (`docs/architecture.md` decía "ninguna hipótesis procesada"; CLAUDE.md regla 17 apuntaba a `docs/cost_model.md`).
- Tests: `test_factory.py` fallaba con `PermissionError` en `%TEMP%\pytest-of-keysi` (dos agentes corriendo pytest a la vez).

## 2. Auditoría del encargo, punto por punto

| # | Punto del encargo | Veredicto | Acción |
|---|---|---|---|
| 1 | AED: `INCONCLUSIVE` no debe omitirse; tests | **Válido** | Implementado. Además se encontró y corrigió un problema no mencionado: la nula inflaba falsos positivos (8.5% a α=5%). |
| 2 | Baseline obligatorio, mismo capital, exposición documentada | **Válido** | Implementado (capital 1x). Ausencia de baseline = FAIL. |
| 3 | Sensibilidad por parámetro | **Válido** (regla 14) | Implementado: uno a la vez ±10/20% + 200 vecinos Montecarlo. |
| 4 | Time-stop: "si no se toca stop/target intrabar, aplicar time-stop al open" | **Incorrecto como está escrito** | Rechazado: al open no se conoce el rango posterior de la barra (look-ahead). La política vigente (salir al open) es correcta. Se corrigió un error real distinto: en la barra límite, un gap a través del target se pagaba al open (más favorable) en vez del target (conservador). |
| 5 | Integridad IS/OOS: hashes, rangos, esquema, duplicados | **Válido** | Implementado con sello TOFU; OOS nunca se parsea en el flujo IS. |
| 6 | OOS fail-closed con documento | **Ya estaba hecho** | Se hizo explícita la lista de prerrequisitos y se agregó test. |
| 7 | Walk-forward: no presentarlo como hecho | **Válido** | `diagnostics.walk_forward = NOT_IMPLEMENTED`; folds rotulados como diagnóstico. |
| 8 | Documentación y agentes alineados | **Válido** | Hecho, salvo `investigator.md` (reclamado por GPT; desalineación anotada en `AGENTS.md`). |
| 9 | Estados de hipótesis coherentes | **Parcialmente hecho por GPT** (el runner ya no repetía descartadas) | Agregado vocabulario y verificador `qaf/consistency.py`. |
| 10 | Tests con directorio temporal propio | **Válido** | Hecho con `--basetemp` fuera de OneDrive, no en `.pytest-temp` dentro del repo (evita ensuciar el working tree). |

## 3. Archivos modificados o creados por Claude
- Código: `qaf/aed.py`, `qaf/baseline.py`, `qaf/validation.py`, `qaf/engine.py` (solo la regla de time-stop), `qaf/data.py` (`load_is`), `qaf/ingest.py`, `qaf/holdout.py`, `qaf/runner.py` (solo `execute`), `qaf/reporting.py` (solo `render_run`/`gates_table`/estilo), nuevos `qaf/partition.py` y `qaf/consistency.py`.
- Tests: `tests/test_aed.py`, `tests/test_baseline.py`, nuevos `tests/test_engine_timestop.py`, `tests/test_partition_integrity.py`, `tests/test_consistency_and_holdout.py`. `tests/test_factory.py` no se tocó.
- Datos: `data/clean/manifest.json` (28 series selladas; respaldo previo fuera del repo en el scratchpad de la sesión).
- Documentación: `AGENTS.md` (nuevo), `.github/copilot-instructions.md` (nuevo), `CLAUDE.md`, `docs/architecture.md`, `docs/VALIDATION_ROADMAP.md`, `.claude/agents/engine.md`, `validator.md`, `protocol.md`, este informe, `PROJECT_STATE.md` (sección agregada al final).

## 4. Cambios funcionales
1. **AED** (`qaf/aed.py`): permutación por **rotación circular** de las entradas dentro del rango válido. Conserva número de señales, secuencia de direcciones y rachas. Horizonte = `max_holding`. Menos de 20 señales → `INCONCLUSIVE`.
2. **Puertas fail-closed** (`screening_gates`): `beats_baseline`, `aed_pattern_confirmed` y `parameter_sensitivity` siempre aparecen. Diagnóstico ausente → `FAIL` (`NOT_COMPUTED`/`NOT_EXECUTED`). Puerta `INCONCLUSIVE` → decisión `INCONCLUSIVE` (si ninguna otra falla). p-valor no finito, ≤0 o >1 → `FAIL`.
3. **Baseline** (`qaf/baseline.py`): por defecto, lotes = capital inicial / nocional por lote a la entrada, redondeado hacia abajo a `volume_step`. Liquidación `INSOLVENT_OPEN` como el motor. Se registra `sizing` (método, lotes, nocional/capital).
4. **Sensibilidad** (`parameter_sensitivity`): cada parámetro de `spec.parameters` a -20/-10/+10/+20% (enteros redondeados, al menos 1 unidad); 200 vecinos con todos los parámetros a la vez uniforme en ±20%. Vecinos inválidos se registran, no se simulan. FAIL si percentil de la spec > 0.8 o < 50% de vecinos con neto > 0.
5. **Time-stop** (`qaf/engine.py`): en la barra límite, `STOP_GAP` y `TARGET_GAP_CONSERVATIVE` preceden a `TIME`; toques intrabar no aplican.
6. **Integridad** (`qaf/partition.py`, `qaf/data.py`, `qaf/ingest.py`): sello con sha256 de IS/OOS, esquema y rango temporal del footer parquet; verificación de ambos hashes en cada `load_is`; IS que invade su propio corte → error. `qaf.ingest` sella al crear.
7. **OOS** (`qaf/holdout.py`): `FinalValidationBlocked` con los 7 prerrequisitos y la ruta al roadmap.
8. **Estados** (`qaf/consistency.py`): vocabulario, paridad `config/hypotheses.json` ↔ `_registry.md`, y aviso si SQLite ya registra `DISCARDED_IS` para una hipótesis aún ejecutable.
9. **Reporte**: secciones de modelo de ejecución, AED, sensibilidad, baseline con mismo capital, integridad de partición y walk-forward pendiente.

## 5. Decisiones metodológicas (reversibles, a confirmar por Alexander)
- **Baseline = mismo capital invertido 1x**, P&L neto absoluto, no ajustado por riesgo. Alternativa descartada: 1 lote fijo (apalancamiento distinto por símbolo).
- **Umbrales de sensibilidad provisionales**: percentil ≤ 0.8 y ≥ 50% de vecinos rentables. Se perturban **todos** los parámetros, no solo los "libres" (las specs no declaran cuáles lo son); es más conservador.
- **AED** reutiliza `bootstrap_iterations` y `seed` de `config/runner.json` para el número de rotaciones; no agrega campos a la política.
- **`INCONCLUSIVE` en vez de `INVALID_POR_DATOS`** para pocas señales: es el vocabulario de decisión de `qaf`; `validator` traduce a `INVALID_POR_DATOS` cuando corresponde (regla 20).

## 6. Tests ejecutados y resultados exactos
```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "<scratchpad>\ptfinal"
```
- **99 pasados, 0 fallidos, 0 errores, 0 warnings** (Python 3.12.14).
- Por archivo: `test_aed.py` 18, `test_baseline.py` 12, `test_consistency_and_holdout.py` 7, `test_engine_timestop.py` 7, `test_factory.py` 45, `test_partition_integrity.py` 10.
- Error de entorno previo (no de código): `PermissionError` en `%TEMP%\pytest-of-keysi` y en `.pytest_cache` dentro de OneDrive cuando dos agentes corren pytest a la vez. Se evita con `--basetemp` propio y `-p no:cacheprovider` (documentado en `AGENTS.md`).
- Calibración del AED (script ad-hoc, 200 random walks por familia, α=5%): rotación 3.5% (breakout), 3.5% (cruce), 4.5% (racha); diseño anterior 8.5% (breakout).

## 7. Corrida real (IS, datos sellados, carpeta temporal, sin escribir en `reports/` ni SQLite)

| Hip. | Serie | Operaciones | Neto IS | AED p | Sensibilidad (percentil / vecinos >0) | Decisión |
|---|---|---|---|---|---|---|
| 001 | XAUUSD D1 | 458 | -43,390.57 | 0.446 | 0.545 / 0% | DISCARDED_IS |
| 003 | SP500 D1 | 148 | +5,550.07 | 0.111 | 0.92 / 50% | DISCARDED_IS |
| 004 | US30 D1 | 60 | -7,929.87 | 0.630 | 0.34 / 0% | DISCARDED_IS |
| 005 | US30 H1 | 1,194 | -57,437.38 | 0.656 | 0.42 / 0% | DISCARDED_IS |
| 006 | DAX H4 | 160 | -20,707.85 | 0.990 | 0.025 / 0% | DISCARDED_IS |

Ningún estado de hipótesis cambia. La 003 ahora tiene dos evidencias nuevas en contra: la señal cruda no supera la permutación (p=0.11) y la spec está en el 8% superior de su vecindad (ganadora aislada).

**Baseline con mismo capital: insolvente en las 5 series (≈ -100.5k).** Buena parte es artefacto de costos constantes (C4): el swap está en efectivo por lote al valor actual, y al comprar más lotes cuando el precio histórico era bajo, la financiación anualizada queda muy por encima de la real en los primeros años. No cambia ninguna decisión (todas fallan también por otras puertas), pero el baseline no sirve como referencia fina hasta resolver C4.

Tiempo por estrategia: 6–19 s en D1/H4, 68 s en US30 H1.

## 8. Limitaciones que permanecen
- C4: costos constantes (swap/spread actuales sobre todo el histórico). Afecta P&L de estrategias y, sobre todo, del baseline.
- Walk-forward real no implementado.
- Sello TOFU: prueba que nada cambió desde el sello, no que los archivos eran correctos antes.
- Umbrales de sensibilidad provisionales.
- `investigator.md` y el mensaje de error de `run_daily` siguen desalineados (archivos de GPT, anotados en `AGENTS.md`).

## 9. Qué falta para abrir OOS
Los 7 puntos de `qaf/holdout.py::PREREQUISITES` / `docs/VALIDATION_ROADMAP.md`: costos históricos variables, calendario contrastado, precio de referencia, auditoría de exposición previa, walk-forward real, contrato congelado (el sello de partición ya está).

## 10. Qué falta para declarar una estrategia aprobada
Que una hipótesis pase **todas** las puertas IS (hoy ninguna lo hace) y luego el OOS único, walk-forward, permutación final y Montecarlo, más incubación demo y lote mínimo real (regla 15) con confirmación de Alexander. Hoy no existe ninguna estrategia aprobada ni candidata.

## Comandos reproducibles
```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "$env:LOCALAPPDATA\Temp\qaf-pytest-claude"
.venv\Scripts\python.exe -m qaf.partition seal        # idempotente: ALREADY_SEALED
.venv\Scripts\python.exe -m qaf.consistency           # [] = coherente
.venv\Scripts\python.exe -m qaf.cli run               # escribe en reports/factory y state/ (compartido)
```
