import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Turnos",
    page_icon="📅",
    layout="wide"
)

# Crear directorio data si no existe
if not os.path.exists('data'):
    os.makedirs('data')

# Título
st.title("📅 Gestión de Malla de Turnos - Febrero 2026")

# Códigos de turnos
CODIGOS_TURNOS = {
    '': 'Descanso',
    'VC': 'Vacaciones',
    'CP': 'Cumpleaños',
    'PA': 'Incapacidad',
    '151': 'Turno 05:00-13:30',
    '155': 'Turno 06:00-14:00',
    '70': 'Turno 06:00-14:30',
    '177': 'Turno 08:00-16:00',
}

def init_db():
    """Inicializa la base de datos"""
    conn = sqlite3.connect('data/turnos.db')
    c = conn.cursor()
    
    # Tabla de empleados
    c.execute('''CREATE TABLE IF NOT EXISTS empleados
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT NOT NULL,
                  cargo TEXT,
                  documento TEXT UNIQUE,
                  area TEXT)''')
    
    # Tabla de turnos
    c.execute('''CREATE TABLE IF NOT EXISTS turnos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  empleado_id INTEGER,
                  fecha TEXT,
                  codigo_turno TEXT,
                  FOREIGN KEY (empleado_id) REFERENCES empleados (id),
                  UNIQUE(empleado_id, fecha))''')
    
    conn.commit()
    conn.close()

def cargar_datos_prueba():
    """Carga datos de prueba"""
    conn = sqlite3.connect('data/turnos.db')
    
    # Verificar si hay datos
    df_emp = pd.read_sql("SELECT COUNT(*) as count FROM empleados", conn)
    if df_emp['count'].iloc[0] == 0:
        empleados = [
            ('MERCHAN EDWIN', 'SUBDIRECTOR/REGENTE', '1055272480', 'TIENDA'),
            ('SANCHEZ BEYANIDA', 'JEFE DE TIENDA', '23755474', 'TIENDA'),
            ('QUINTERO DANIELA', 'COORDINADOR DE DOMICILIOS', '1032504934', 'DOMI'),
        ]
        
        for emp in empleados:
            c = conn.cursor()
            c.execute('''INSERT INTO empleados (nombre, cargo, documento, area)
                        VALUES (?, ?, ?, ?)''', emp)
        conn.commit()
    
    conn.close()

# Inicializar
init_db()
cargar_datos_prueba()

# Obtener días de febrero 2026
dias_febrero = []
fecha_actual = datetime(2026, 2, 1)
while fecha_actual.month == 2:
    dias_febrero.append(fecha_actual)
    fecha_actual += timedelta(days=1)

# Menú lateral
with st.sidebar:
    st.header("Menú")
    opcion = st.radio("Seleccionar:", ["📊 Ver Turnos", "👥 Empleados", "✏️ Editar Turno"])

# Conectar a BD
conn = sqlite3.connect('data/turnos.db')

if opcion == "📊 Ver Turnos":
    st.header("Malla de Turnos")
    
    # Filtro por área
    areas = pd.read_sql("SELECT DISTINCT area FROM empleados", conn)['area'].tolist()
    areas = ['TODOS'] + areas
    area_filtro = st.selectbox("Filtrar por área", areas)
    
    # Cargar empleados
    if area_filtro == 'TODOS':
        df_emp = pd.read_sql("SELECT * FROM empleados ORDER BY area, nombre", conn)
    else:
        df_emp = pd.read_sql(f"SELECT * FROM empleados WHERE area = '{area_filtro}' ORDER BY nombre", conn)
    
    # Cargar turnos
    df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
    
    # Crear tabla
    data = []
    for _, emp in df_emp.iterrows():
        fila = {
            'Nombre': emp['nombre'],
            'Cargo': emp['cargo'],
            'Área': emp['area']
        }
        
        for fecha in dias_febrero[:5]:  # Solo primeros 5 días para prueba
            fecha_str = fecha.strftime('%Y-%m-%d')
            turno = df_turnos[(df_turnos['empleado_id'] == emp['id']) & 
                            (df_turnos['fecha'] == fecha_str)]
            codigo = turno['codigo_turno'].iloc[0] if not turno.empty else ''
            fila[fecha.strftime('%d/%m')] = codigo
        
        data.append(fila)
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay empleados")

elif opcion == "👥 Empleados":
    tab1, tab2, tab3 = st.tabs(["Lista", "Agregar", "Eliminar"])
    
    with tab1:
        df_emp = pd.read_sql("SELECT * FROM empleados", conn)
        st.dataframe(df_emp)
    
    with tab2:
        with st.form("nuevo_empleado"):
            nombre = st.text_input("Nombre")
            cargo = st.text_input("Cargo")
            documento = st.text_input("Documento")
            area = st.selectbox("Área", ["TIENDA", "DOMI"])
            
            if st.form_submit_button("Agregar"):
                if nombre and cargo and documento:
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO empleados (nombre, cargo, documento, area) VALUES (?, ?, ?, ?)",
                            (nombre, cargo, documento, area)
                        )
                        conn.commit()
                        st.success("Empleado agregado!")
                        st.rerun()
                    except:
                        st.error("Error al agregar")
    
    with tab3:
        df_emp = pd.read_sql("SELECT * FROM empleados", conn)
        if not df_emp.empty:
            empleado = st.selectbox("Seleccionar", df_emp['nombre'].tolist())
            if st.button("Eliminar"):
                cursor = conn.cursor()
                cursor.execute("DELETE FROM turnos WHERE empleado_id = (SELECT id FROM empleados WHERE nombre = ?)", (empleado,))
                cursor.execute("DELETE FROM empleados WHERE nombre = ?", (empleado,))
                conn.commit()
                st.success("Eliminado!")
                st.rerun()

elif opcion == "✏️ Editar Turno":
    st.header("Editar Turno")
    
    df_emp = pd.read_sql("SELECT * FROM empleados", conn)
    
    if not df_emp.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            empleado = st.selectbox("Empleado", df_emp['nombre'].tolist())
        
        with col2:
            fecha = st.date_input("Fecha", 
                                 value=datetime(2026, 2, 1),
                                 min_value=datetime(2026, 2, 1),
                                 max_value=datetime(2026, 2, 28))
        
        with col3:
            codigo = st.selectbox("Turno", list(CODIGOS_TURNOS.keys()),
                                 format_func=lambda x: f"{x} - {CODIGOS_TURNOS[x]}")
        
        if st.button("Guardar"):
            empleado_id = df_emp[df_emp['nombre'] == empleado]['id'].iloc[0]
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO turnos (empleado_id, fecha, codigo_turno) VALUES (?, ?, ?)",
                (empleado_id, fecha.strftime('%Y-%m-%d'), codigo)
            )
            conn.commit()
            st.success("Turno guardado!")
    else:
        st.warning("No hay empleados. Agrega uno primero.")

conn.close()

# Footer
st.markdown("---")
st.caption("Sistema de Gestión de Turnos v1.0")