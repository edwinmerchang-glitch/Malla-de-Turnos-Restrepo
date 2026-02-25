from collections import defaultdict
from datetime import timedelta

def generar_malla_inteligente(empleados, turnos, fecha_inicio, dias):
    carga = defaultdict(int)
    resultado = []
    fecha = fecha_inicio

    for _ in range(dias):
        for turno in turnos:
            emp = min(empleados, key=lambda e: carga[e.id])
            resultado.append((emp.id, fecha, turno.nombre))
            carga[emp.id] += 1
        fecha += timedelta(days=1)

    return resultado