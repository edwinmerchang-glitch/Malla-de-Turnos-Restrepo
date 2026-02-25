import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Turnos - Febrero 2026",
    page_icon="📅",
    layout="wide"
)

# Crear directorio data si no existe
if not os.path.exists('data'):
    os.makedirs('data')

# Título
st.title("📅 Gestión de Malla de Turnos - Febrero 2026")
st.markdown("---")

# Códigos de turnos
CODIGOS_TURNOS = {
    '': 'Descanso',
    'VC': 'Vacaciones',
    'CP': 'Cumpleaños',
    'PA': 'Incapacidad',
    'inc': 'Incapacidad',
    'cap': 'Capacitación',
    '151': 'Turno 05:00-13:30',
    '155': 'Turno 06:00-14:00',
    '70': 'Turno 06:00-14:30',
    '149': 'Turno 07:00-15:00',
    '97': 'Turno 07:00-15:30',
    '207': 'Turno 08:00-16:30',
    '177': 'Turno 08:00-16:00',
    '153': 'Turno 09:00-17:00',
    '208': 'Turno 09:00-17:30',
    '16': 'Turno 09:00-18:00',
    '154': 'Turno 10:00-18:00',
    '20': 'Turno 10:00-19:00',
    '209': 'Turno 10:30-19:00',
    '210': 'Turno 11:30-20:00',
    '26': 'Turno 12:30-21:00',
    '212': 'Turno 12:30-21:00',
    '213': 'Turno 12:30-21:00',
    '214': 'Turno 13:00-20:30',
    '158': 'Turno 13:30-21:00',
    '215': 'Turno 13:00-21:30',
    '216': 'Turno 13:30-22:00',
    '217': 'Turno 13:30-22:00',
    '225': 'Turno 09:30-18:00',
    '15': 'Turno 15',
    '17': 'Turno 17',
    '19': 'Turno 19',
    '63': 'Turno 63',
    '107': 'Turno 107',
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
                  fecha TEXT NOT NULL,
                  codigo_turno TEXT,
                  FOREIGN KEY (empleado_id) REFERENCES empleados (id),
                  UNIQUE(empleado_id, fecha))''')
    
    conn.commit()
    conn.close()

def cargar_datos_iniciales():
    """Carga datos iniciales de empleados"""
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
            ('OLAYA DIANA MILENA', 'AIS EN DOMICILIOS', '1018458087', 'DOMI', '08:00', '17:00'),
            ('LANDAZURI EMELI', 'AIS EN DOMICILIOS', '1089539083', 'DOMI', '06:00', '15:00'),
        ]
        
        for emp in empleados:
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO empleados 
                            (nombre, cargo, documento, area, horario_entrada, horario_salida)
                            VALUES (?, ?, ?, ?, ?, ?)''', emp)
            except:
                pass  # Ignorar duplicados
        
        conn.commit()
    
    conn.close()

def get_febrero_dias():
    """Genera lista de días de febrero 2026"""
    start_date = datetime(2026, 2, 1)
    end_date = datetime(2026, 2, 28)
    return [start_date + timedelta(days=x) for x in range((end_date-start_date).days + 1)]

def get_dia_semana(fecha):
    """Retorna día de la semana abreviado"""
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    return dias[fecha.weekday()]

# Inicializar
init_db()
cargar_datos_iniciales()

# Obtener días de febrero
dias_febrero = get_febrero_dias()
dias_str = [d.strftime("%d/%m") for d in dias_febrero]
dias_semana = [get_dia_semana(d) for d in dias_febrero]

# Menú lateral
with st.sidebar:
    st.header("📋 Menú Principal")
    opcion = st.radio(
        "Seleccionar:",
        ["📊 Vista de Turnos", "👥 Gestión de Empleados", "✏️ Editar Turno", "📊 Reportes"]
    )
    
    st.markdown("---")
    st.caption("Febrero 2026 - 28 días")

# Conectar a BD
conn = sqlite3.connect('data/turnos.db')

if opcion == "📊 Vista de Turnos":
    st.header("📊 Malla de Turnos")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        areas = pd.read_sql("SELECT DISTINCT area FROM empleados", conn)['area'].tolist()
        areas = ['TODAS'] + areas
        area_filter = st.selectbox("Filtrar por área", areas)
    
    with col2:
        dias_mostrar = st.slider("Días a mostrar", 5, 28, 10)
    
    # Cargar empleados
    if area_filter == 'TODAS':
        df_empleados = pd.read_sql("SELECT * FROM empleados ORDER BY area, nombre", conn)
    else:
        df_empleados = pd.read_sql(f"SELECT * FROM empleados WHERE area = '{area_filter}' ORDER BY nombre", conn)
    
    # Cargar turnos existentes
    df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
    
    if not df_empleados.empty:
        # Crear matriz de turnos
        turnos_data = []
        for _, emp in df_empleados.iterrows():
            fila = {
                'Cargo': emp['cargo'][:20] + '...' if len(emp['cargo']) > 20 else emp['cargo'],
                'Nombre': emp['nombre'],
                'Área': emp['area']
            }
            
            for i, fecha in enumerate(dias_febrero[:dias_mostrar]):
                turno = df_turnos[(df_turnos['empleado_id'] == emp['id']) & 
                                (df_turnos['fecha'] == fecha.strftime('%Y-%m-%d'))]
                codigo = turno['codigo_turno'].iloc[0] if not turno.empty else ''
                fila[fecha.strftime('%d/%m')] = codigo
            
            turnos_data.append(fila)
        
        df_vista = pd.DataFrame(turnos_data)
        
        # Mostrar tabla
        st.dataframe(
            df_vista,
            use_container_width=True,
            height=500,
            column_config={
                "Cargo": st.column_config.TextColumn("Cargo", width=150),
                "Nombre": st.column_config.TextColumn("Nombre", width=150),
                "Área": st.column_config.TextColumn("Área", width=70),
                **{fecha: st.column_config.TextColumn(f"{fecha}\n{dias_semana[i]}", width=60) 
                   for i, fecha in enumerate(dias_str[:dias_mostrar])}
            }
        )
        
        # Leyenda de códigos
        with st.expander("📖 Ver significado de códigos"):
            col1, col2, col3 = st.columns(3)
            items = list(CODIGOS_TURNOS.items())
            for i, (codigo, desc) in enumerate(items):
                if i % 3 == 0:
                    with col1:
                        st.text(f"{codigo}: {desc}" if codigo else "Vacío: Descanso")
                elif i % 3 == 1:
                    with col2:
                        st.text(f"{codigo}: {desc}" if codigo else "")
                else:
                    with col3:
                        st.text(f"{codigo}: {desc}" if codigo else "")
    else:
        st.info("No hay empleados registrados")

elif opcion == "👥 Gestión de Empleados":
    st.header("👥 Gestión de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista", "➕ Agregar", "🗑️ Eliminar"])
    
    with tab1:
        df_emp = pd.read_sql("SELECT id, nombre, cargo, documento, area, horario_entrada, horario_salida FROM empleados ORDER BY area, nombre", conn)
        if not df_emp.empty:
            st.dataframe(df_emp, use_container_width=True)
        else:
            st.info("No hay empleados registrados")
    
    with tab2:
        with st.form("form_empleado"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre completo*")
                cargo = st.text_input("Cargo*")
                documento = st.text_input("Documento*")
            with col2:
                area = st.selectbox("Área*", ["TIENDA", "DOMI"])
                horario_entrada = st.text_input("Horario entrada", value="08:00")
                horario_salida = st.text_input("Horario salida", value="17:00")
            
            if st.form_submit_button("✅ Agregar Empleado"):
                if nombre and cargo and documento:
                    cursor = conn.cursor()
                    try:
                        cursor.execute('''INSERT INTO empleados 
                                        (nombre, cargo, documento, area, horario_entrada, horario_salida)
                                        VALUES (?, ?, ?, ?, ?, ?)''',
                                        (nombre, cargo, documento, area, horario_entrada, horario_salida))
                        conn.commit()
                        st.success("✅ Empleado agregado correctamente!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Ya existe un empleado con ese documento")
                else:
                    st.error("❌ Complete todos los campos obligatorios")
    
    with tab3:
        df_emp = pd.read_sql("SELECT id, nombre FROM empleados ORDER BY nombre", conn)
        if not df_emp.empty:
            empleado_eliminar = st.selectbox("Seleccionar empleado", df_emp['nombre'].tolist())
            if st.button("🗑️ Eliminar Empleado", type="secondary"):
                cursor = conn.cursor()
                # Eliminar turnos primero
                cursor.execute("DELETE FROM turnos WHERE empleado_id = (SELECT id FROM empleados WHERE nombre = ?)",
                              (empleado_eliminar,))
                # Eliminar empleado
                cursor.execute("DELETE FROM empleados WHERE nombre = ?", (empleado_eliminar,))
                conn.commit()
                st.success(f"✅ Empleado eliminado")
                st.rerun()
        else:
            st.info("No hay empleados para eliminar")

elif opcion == "✏️ Editar Turno":
    st.header("✏️ Editar Turno")
    
    df_emp = pd.read_sql("SELECT * FROM empleados ORDER BY nombre", conn)
    
    if not df_emp.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            empleado = st.selectbox("Empleado", df_emp['nombre'].tolist())
        
        with col2:
            fecha = st.date_input("Fecha", 
                                 value=datetime(2026, 2, 1),
                                 min_value=datetime(2026, 2, 1),
                                 max_value=datetime(2026, 2, 28))
        
        with col3:
            codigo = st.selectbox("Código turno", 
                                 options=list(CODIGOS_TURNOS.keys()),
                                 format_func=lambda x: f"{x} - {CODIGOS_TURNOS[x]}")
        
        with col4:
            if st.button("💾 Guardar Turno", type="primary"):
                empleado_id = df_emp[df_emp['nombre'] == empleado]['id'].iloc[0]
                cursor = conn.cursor()
                cursor.execute('''INSERT OR REPLACE INTO turnos 
                                (empleado_id, fecha, codigo_turno)
                                VALUES (?, ?, ?)''',
                                (empleado_id, fecha.strftime('%Y-%m-%d'), codigo))
                conn.commit()
                st.success(f"✅ Turno guardado para {empleado}")
                st.rerun()
        
        # Mostrar turnos existentes del empleado
        st.markdown("---")
        st.subheader("Turnos actuales")
        empleado_id = df_emp[df_emp['nombre'] == empleado]['id'].iloc[0]
        df_turnos_emp = pd.read_sql(f"SELECT fecha, codigo_turno FROM turnos WHERE empleado_id = {empleado_id} ORDER BY fecha", conn)
        if not df_turnos_emp.empty:
            st.dataframe(df_turnos_emp, use_container_width=True)
    else:
        st.warning("Primero debe agregar empleados")

elif opcion == "📊 Reportes":
    st.header("📊 Reportes")
    
    # Cargar datos
    df_emp = pd.read_sql("SELECT * FROM empleados", conn)
    df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
    
    if not df_emp.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Empleados", len(df_emp))
        with col2:
            st.metric("Total Turnos", len(df_turnos))
        with col3:
            st.metric("Días del mes", len(dias_febrero))
        
        if not df_turnos.empty:
            # Turnos por área
            st.subheader("Turnos por Área")
            df_turnos_area = df_turnos.merge(df_emp[['id', 'area']], left_on='empleado_id', right_on='id')
            area_counts = df_turnos_area['area'].value_counts().reset_index()
            area_counts.columns = ['Área', 'Cantidad de Turnos']
            st.dataframe(area_counts, use_container_width=True)
            
            # Códigos más usados
            st.subheader("Códigos más usados")
            codigo_counts = df_turnos['codigo_turno'].value_counts().reset_index().head(10)
            codigo_counts.columns = ['Código', 'Veces usado']
            codigo_counts['Descripción'] = codigo_counts['Código'].map(CODIGOS_TURNOS)
            st.dataframe(codigo_counts, use_container_width=True)
    else:
        st.info("No hay datos suficientes")

conn.close()

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("© 2026 - Sistema de Gestión de Turnos")
with col2:
    st.caption("Febrero 2026")
with col3:
    st.caption("v2.0")