import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import streamlit as st

# Códigos de turnos y sus significados
CODIGOS_TURNOS = {
    '': 'Descanso',
    'VC': 'Vacaciones',
    'CP': 'Cumpleaños',
    'PA': 'Incapacidad',
    'inc': 'Incapacidad',
    'cap': 'Capacitación',
    '107': 'Turno 107',
    '149': 'Turno 149',
    '151': 'Turno 151',
    '153': 'Turno 153',
    '154': 'Turno 154',
    '155': 'Turno 155',
    '157': 'Turno 157',
    '158': 'Turno 158',
    '177': 'Turno 177',
    '207': 'Turno 207',
    '208': 'Turno 208',
    '209': 'Turno 209',
    '210': 'Turno 210',
    '211': 'Turno 211',
    '212': 'Turno 212',
    '213': 'Turno 213',
    '214': 'Turno 214',
    '215': 'Turno 215',
    '216': 'Turno 216',
    '217': 'Turno 217',
    '225': 'Turno 225',
    '15': 'Turno 15',
    '16': 'Turno 16',
    '17': 'Turno 17',
    '19': 'Turno 19',
    '20': 'Turno 20',
    '25': 'Turno 25',
    '26': 'Turno 26',
    '63': 'Turno 63',
    '70': 'Turno 70',
    '97': 'Turno 97',
}

# Horarios por código
HORARIOS = {
    '151': {'entrada': '05:00', 'salida': '13:30'},
    '155': {'entrada': '06:00', 'salida': '14:00'},
    '70': {'entrada': '06:00', 'salida': '14:30'},
    '149': {'entrada': '07:00', 'salida': '15:00'},
    '97': {'entrada': '07:00', 'salida': '15:30'},
    '207': {'entrada': '08:00', 'salida': '16:30'},
    '177': {'entrada': '08:00', 'salida': '16:00'},
    '153': {'entrada': '09:00', 'salida': '17:00'},
    '208': {'entrada': '09:00', 'salida': '17:30'},
    '16': {'entrada': '09:00', 'salida': '18:00'},
    '154': {'entrada': '10:00', 'salida': '18:00'},
    '20': {'entrada': '10:00', 'salida': '19:00'},
    '209': {'entrada': '10:30', 'salida': '19:00'},
    '155': {'entrada': '11:00', 'salida': '19:00'},
    '210': {'entrada': '11:30', 'salida': '20:00'},
    '26': {'entrada': '12:30', 'salida': '21:00'},
    '212': {'entrada': '12:30', 'salida': '21:00'},
    '213': {'entrada': '12:30', 'salida': '21:00'},
    '214': {'entrada': '13:00', 'salida': '20:30'},
    '158': {'entrada': '13:30', 'salida': '21:00'},
    '215': {'entrada': '13:00', 'salida': '21:30'},
    '216': {'entrada': '13:30', 'salida': '22:00'},
    '217': {'entrada': '13:30', 'salida': '22:00'},
    '225': {'entrada': '09:30', 'salida': '18:00'},
}

def init_db():
    """Inicializa la base de datos SQLite"""
    conn = sqlite3.connect('data/turnos.db')
    c = conn.cursor()
    
    # Tabla de empleados
    c.execute('''CREATE TABLE IF NOT EXISTS empleados
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT NOT NULL,
                  cargo TEXT,
                  documento TEXT UNIQUE,
                  area TEXT,
                  horario_entrada TEXT,
                  horario_salida TEXT)''')
    
    # Tabla de turnos diarios
    c.execute('''CREATE TABLE IF NOT EXISTS turnos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  empleado_id INTEGER,
                  fecha DATE NOT NULL,
                  codigo_turno TEXT,
                  FOREIGN KEY (empleado_id) REFERENCES empleados (id),
                  UNIQUE(empleado_id, fecha))''')
    
    conn.commit()
    conn.close()

def cargar_datos_ejemplo():
    """Carga datos de ejemplo desde el Excel si la BD está vacía"""
    conn = sqlite3.connect('data/turnos.db')
    
    # Verificar si hay empleados
    df_emp = pd.read_sql("SELECT COUNT(*) as count FROM empleados", conn)
    if df_emp['count'].iloc[0] == 0:
        # Datos de empleados del Excel
        empleados = [
            ('MERCHAN EDWIN', 'SUBDIRECTOR/REGENTE', '1055272480', 'TIENDA', '06:00', '14:00'),
            ('SANCHEZ BEYANIDA', 'JEFE DE TIENDA', '23755474', 'TIENDA', '05:00', '13:30'),
            ('ABRIL JOHANNA', 'COORDINADORA DE DROGUERIA', '1000119978', 'TIENDA', '06:00', '14:30'),
            ('SUAREZ YULY ANDREA', 'AIS EN DROGUERIA', '1024533554', 'TIENDA', '07:00', '15:00'),
            ('GUERRERO ANA LUCIA', 'AIS EN DROGUERIA', '27387869', 'TIENDA', '07:00', '15:30'),
            ('ALEXANDRA CARDONA', 'AIS EN DROGUERIA', '1025140016', 'TIENDA', '08:00', '16:30'),
            ('TAMAYO ADRIANA', 'COORDINADOR DE CAJAS Y TESORERIA', '1109843094', 'TIENDA', '09:00', '17:00'),
            ('PARADA CLAUDIA', 'SUPERVISORA DE CAJAS', '53890126', 'TIENDA', '09:00', '17:30'),
            ('REYES EDWIN', 'AIS EN CAJAS', '74339325', 'TIENDA', '09:00', '18:00'),
            ('DUQUE SANDRA LORENA', 'AIS EN CAJAS', '1024526086', 'TIENDA', '09:00', '17:30'),
            ('QUINTERO DANIELA', 'COORDINADOR DE DOMICILIOS', '1032504934', 'DOMI', '13:30', '21:30'),
            ('LEON NICOLAS', 'AIS EN DOMICILIOS', '1019088886', 'DOMI', '09:30', '18:00'),
        ]
        
        for emp in empleados:
            c = conn.cursor()
            c.execute('''INSERT OR IGNORE INTO empleados 
                        (nombre, cargo, documento, area, horario_entrada, horario_salida)
                        VALUES (?, ?, ?, ?, ?, ?)''', emp)
        
        conn.commit()
    
    conn.close()

def get_febrero_dias():
    """Genera lista de días de febrero 2026"""
    start_date = datetime(2026, 2, 1)
    end_date = datetime(2026, 2, 28)
    return [start_date + timedelta(days=x) for x in range((end_date-start_date).days + 1)]

def get_dia_semana(fecha):
    """Retorna día de la semana abreviado"""
    dias = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb']
    return dias[fecha.weekday()]

def get_color_para_turno(codigo):
    """Retorna color para cada tipo de turno"""
    colores = {
        '': '#ffffff',
        'VC': '#ff9999',
        'CP': '#99ff99',
        'PA': '#ffcc99',
        'inc': '#ffcc99',
        'cap': '#99ccff',
        '151': '#90EE90',
        '155': '#87CEEB',
        '70': '#DDA0DD',
        '177': '#F0E68C',
        '207': '#FFB6C1',
        '149': '#98FB98',
    }
    return colores.get(codigo, '#ffffff')