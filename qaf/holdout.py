"""Fail closed: exploratory scenarios cannot authorize final validation."""
def freeze(run_id, root=None):
    raise NotImplementedError('Validación final bloqueada: faltan costos históricos variables, calendario contrastado y auditoría de exposición previa. OOS no abierto. Ver docs/VALIDATION_ROADMAP.md.')

def validate_final(freeze_id, root=None):
    return freeze(freeze_id, root)
