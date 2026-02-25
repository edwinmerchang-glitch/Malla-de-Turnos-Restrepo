from datetime import datetime, timedelta

CODIGOS_TURNOS = {
    '': 'Descanso',
    'VC': 'Vacaciones',
    'CP': 'Cumpleaños',
    'PA': 'Incapacidad',
    'cap': 'Capacitación',
    '151': 'Turno 151',
    '155': 'Turno 155',
    '70': 'Turno 70',
    '149': 'Turno 149',
    '207': 'Turno 207',
}

HORARIOS = {
    '151': ('05:00', '13:30'),
    '155': ('11:00', '19:00'),
    '70': ('06:00', '14:30'),
    '149': ('07:00', '15:00'),
    '207': ('08:00', '16:30'),
}

def get_febrero_2026():
    inicio = datetime(2026,2,1)
    fin = datetime(2026,2,28)
    return [inicio + timedelta(days=i) for i in range((fin-inicio).days + 1)]

def dia_semana(fecha):
    dias = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
    return dias[fecha.weekday()]