"""Falla cerrada: ningun camino de codigo abre OOS hasta cumplir docs/VALIDATION_ROADMAP.md.
Ni freeze ni validate_final leen datos; lanzan antes de tocar cualquier archivo."""

ROADMAP = "docs/VALIDATION_ROADMAP.md"
PREREQUISITES = (
    "costos históricos variables (hoy: escenario constante de config/instruments.json)",
    "calendario de sesiones contrastado (calendar_verified=false)",
    "precio de referencia bid/ask/mid confirmado (price_basis='unknown')",
    "auditoría de exposición previa entre campañas para la corrección por múltiples pruebas",
    "walk-forward real con reentrenamiento por ventana (diagnostics.walk_forward = NOT_IMPLEMENTED)",
    "partición IS/OOS sellada y verificada (python -m qaf.partition seal)",
    "contrato congelado: hash de spec, costos, datos, política y código (freeze no implementado)",
)


class FinalValidationBlocked(NotImplementedError):
    pass


def _blocked():
    items = "; ".join(f"{i}) {item}" for i, item in enumerate(PREREQUISITES, 1))
    return FinalValidationBlocked(f"Validación final bloqueada, OOS no abierto. Faltan: {items}. Ver {ROADMAP}.")


def freeze(run_id, root=None):
    raise _blocked()


def validate_final(freeze_id, root=None):
    raise _blocked()
