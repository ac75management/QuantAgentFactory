# Gate 0 — pendiente de correr

Este stub existe solo para dejar constancia de dónde va a escribir sus resultados el chequeo de calidad de datos, todavía no se corrió sobre nada real.

Cuando el agente `engine` procese una estrategia, corre el checklist completo de [.claude/skills/data-quality-check/SKILL.md](../../.claude/skills/data-quality-check/SKILL.md) sobre los archivos en `data/clean/<SYMBOL>/<TF>/IS.parquet`, y escribe el veredicto en `reports/<slug>/data_quality.md` (una carpeta por hipótesis/estrategia, no aquí).

Este README no se actualiza automáticamente — es solo el marcador de que el paso de extracción (`scripts/extract_darwinex_ohlc.py`) y limpieza (`scripts/build_clean_data.py`) es anterior y separado del Gate 0 real, que corre el agente, no un script suelto.
