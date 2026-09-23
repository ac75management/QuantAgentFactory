# Catálogo versionado

Esta carpeta es la memoria compartida y auditable de las ideas externas.

- `candidates/`: expediente canónico de cada candidato y su revisión.
- `discoveries/<provider>/`: snapshots inmutables de metadatos obtenidos por `source-sync`.

Los snapshots prueban qué metadatos se observaron; no prueban que una estrategia sea correcta, reproducible o rentable. Los hashes se calculan sobre el JSON canónico realmente guardado. Una nueva extracción nunca modifica silenciosamente una revisión: crea otro snapshot y una tarea para `investigator`.

No almacenar aquí PDFs completos, contenido de pago, datos de mercado, credenciales ni copias automáticas de repositorios externos. `state/` queda reservado para SQLite, colas y cachés operativas no versionadas.
