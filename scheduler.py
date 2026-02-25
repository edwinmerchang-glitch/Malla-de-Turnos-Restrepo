from collections import defaultdict
from datetime import timedelta

def generar_malla_inteligente(empleados, turnos, fecha_inicio, dias):
    """
    Genera asignaciones de turnos de manera equitativa
    
    Args:
        empleados: lista de objetos Empleado
        turnos: lista de objetos Turno
        fecha_inicio: fecha inicial
        dias: número de días a generar
    
    Returns:
        lista de tuplas (empleado_id, fecha, turno_nombre)
    """
    carga = defaultdict(int)
    resultado = []
    fecha = fecha_inicio

    for _ in range(dias):
        for turno in turnos:
            if empleados:  # Verificar que hay empleados
                emp = min(empleados, key=lambda e: carga[e.id])
                resultado.append((emp.id, fecha, turno.nombre))
                carga[emp.id] += 1
        fecha += timedelta(days=1)

    return resultado