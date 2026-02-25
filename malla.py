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

def cargar_datos_iniciales():
    """Carga datos iniciales si la BD está vacía"""
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
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    return dias[fecha.weekday()]

# Inicializar base de datos
init_db()
cargar_datos_iniciales()

# Título
st.title("📅 Gestión de Malla de Turnos - Febrero 2026")
st.markdown("---")

# Sidebar para navegación
st.sidebar.title("📋 Menú Principal")
opcion = st.sidebar.radio(
    "Seleccionar vista",
    ["📊 Vista de Turnos", "👥 Gestión de Empleados", "📊 Reportes", "⚙️ Configuración"]
)

# Obtener días de febrero
dias_febrero = get_febrero_dias()
dias_str = [d.strftime("%d/%m") for d in dias_febrero]
dias_semana = [get_dia_semana(d) for d in dias_febrero]

# Conectar a BD
conn = sqlite3.connect('data/turnos.db')

if opcion == "📊 Vista de Turnos":
    st.header("📊 Malla de Turnos - Febrero 2026")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        areas = pd.read_sql("SELECT DISTINCT area FROM empleados", conn)['area'].tolist()
        areas = ['TODAS'] + areas
        area_filter = st.selectbox("Filtrar por área", areas)
    
    # Cargar empleados
    if area_filter == 'TODAS':
        df_empleados = pd.read_sql("SELECT * FROM empleados ORDER BY area, nombre", conn)
    else:
        df_empleados = pd.read_sql(f"SELECT * FROM empleados WHERE area = '{area_filter}' ORDER BY nombre", conn)
    
    # Cargar turnos existentes
    df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
    
    # Crear matriz de turnos
    turnos_data = []
    for _, emp in df_empleados.iterrows():
        fila = {
            'Cargo': emp['cargo'],
            'Nombre': emp['nombre'],
            'Área': emp['area']
        }
        
        for i, fecha in enumerate(dias_febrero):
            turno = df_turnos[(df_turnos['empleado_id'] == emp['id']) & 
                            (df_turnos['fecha'] == fecha.strftime('%Y-%m-%d'))]
            codigo = turno['codigo_turno'].iloc[0] if not turno.empty else ''
            fila[fecha.strftime('%d/%m')] = codigo
        
        turnos_data.append(fila)
    
    if turnos_data:
        df_vista = pd.DataFrame(turnos_data)
        
        # Mostrar tabla
        st.dataframe(
            df_vista,
            use_container_width=True,
            height=500,
            column_config={
                "Cargo": st.column_config.TextColumn("Cargo", width="medium"),
                "Nombre": st.column_config.TextColumn("Nombre", width="medium"),
                "Área": st.column_config.TextColumn("Área", width="small"),
                **{fecha: st.column_config.TextColumn(f"{fecha}\n{dia}", width="small") 
                   for fecha, dia in zip(dias_str[:10], dias_semana[:10])}  # Mostrar solo primeros 10 días para mejor visualización
            }
        )
        
        # Opción para ver más días
        if st.checkbox("Mostrar todos los días del mes"):
            st.dataframe(
                df_vista,
                use_container_width=True,
                height=600
            )
    else:
        st.info("No hay empleados registrados")
    
    # Editor de turnos
    st.markdown("---")
    st.subheader("✏️ Editar Turno")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        empleado = st.selectbox("Seleccionar empleado", 
                                df_empleados['nombre'].tolist() if not df_empleados.empty else ["No hay empleados"])
    with col2:
        fecha_edit = st.date_input("Fecha", 
                                   value=datetime(2026,2,1),
                                   min_value=datetime(2026,2,1),
                                   max_value=datetime(2026,2,28))
    with col3:
        codigo_turno = st.selectbox("Código de turno",
                                    options=list(CODIGOS_TURNOS.keys()),
                                    format_func=lambda x: f"{x} - {CODIGOS_TURNOS[x]}")
    with col4:
        if st.button("💾 Guardar Turno", type="primary") and not df_empleados.empty:
            empleado_id = df_empleados[df_empleados['nombre'] == empleado]['id'].iloc[0]
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO turnos 
                            (empleado_id, fecha, codigo_turno)
                            VALUES (?, ?, ?)''',
                            (empleado_id, fecha_edit.strftime('%Y-%m-%d'), codigo_turno))
            conn.commit()
            st.success(f"Turno guardado correctamente para {empleado} el {fecha_edit.strftime('%d/%m/%Y')}")
            st.rerun()

elif opcion == "👥 Gestión de Empleados":
    st.header("👥 Gestión de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Empleados", "➕ Agregar Empleado", "🗑️ Eliminar Empleado"])
    
    with tab1:
        df_emp = pd.read_sql("SELECT * FROM empleados ORDER BY area, nombre", conn)
        if not df_emp.empty:
            st.dataframe(df_emp, use_container_width=True)
        else:
            st.info("No hay empleados registrados")
    
    with tab2:
        st.subheader("Agregar Nuevo Empleado")
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
            
            submitted = st.form_submit_button("✅ Agregar Empleado")
            if submitted:
                if nombre and cargo and documento:
                    cursor = conn.cursor()
                    try:
                        cursor.execute('''INSERT INTO empleados 
                                        (nombre, cargo, documento, area, horario_entrada, horario_salida)
                                        VALUES (?, ?, ?, ?, ?, ?)''',
                                        (nombre, cargo, documento, area, horario_entrada, horario_salida))
                        conn.commit()
                        st.success("Empleado agregado correctamente!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe un empleado con ese documento")
                else:
                    st.error("Por favor complete todos los campos obligatorios (*)")
    
    with tab3:
        st.subheader("Eliminar Empleado")
        df_emp = pd.read_sql("SELECT nombre FROM empleados ORDER BY nombre", conn)
        if not df_emp.empty:
            empleado_eliminar = st.selectbox("Seleccionar empleado a eliminar",
                                           df_emp['nombre'].tolist())
            if st.button("🗑️ Eliminar Empleado", type="secondary"):
                cursor = conn.cursor()
                # Primero eliminar turnos del empleado
                cursor.execute("DELETE FROM turnos WHERE empleado_id = (SELECT id FROM empleados WHERE nombre = ?)",
                              (empleado_eliminar,))
                # Luego eliminar el empleado
                cursor.execute("DELETE FROM empleados WHERE nombre = ?", (empleado_eliminar,))
                conn.commit()
                st.success(f"Empleado {empleado_eliminar} eliminado correctamente!")
                st.rerun()
        else:
            st.info("No hay empleados para eliminar")

elif opcion == "📊 Reportes":
    st.header("📊 Reportes y Estadísticas")
    
    # Cargar datos
    df_emp = pd.read_sql("SELECT * FROM empleados", conn)
    df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
    
    if not df_turnos.empty and not df_emp.empty:
        # Merge con empleados
        df_report = df_turnos.merge(df_emp[['id', 'nombre', 'area']], 
                                    left_on='empleado_id', right_on='id')
        
        # Estadísticas generales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Empleados", len(df_emp))
        with col2:
            st.metric("Total Turnos Asignados", len(df_turnos))
        with col3:
            st.metric("Días del mes", len(dias_febrero))
        
        # Resumen por área
        st.subheader("Resumen por Área")
        df_area = df_emp.groupby('area').size().reset_index(name='cantidad')
        st.dataframe(df_area, use_container_width=True)
        
        # Top turnos más usados
        st.subheader("Códigos de Turno más usados")
        top_turnos = df_report['codigo_turno'].value_counts().reset_index()
        top_turnos.columns = ['Código', 'Cantidad']
        top_turnos['Descripción'] = top_turnos['Código'].map(CODIGOS_TURNOS)
        st.dataframe(top_turnos, use_container_width=True)
        
        # Resumen por empleado
        st.subheader("Resumen de Turnos por Empleado")
        resumen = df_report.groupby('nombre').agg({
            'codigo_turno': 'count',
            'area': 'first'
        }).reset_index()
        resumen.columns = ['Empleado', 'Total Turnos', 'Área']
        resumen = resumen.sort_values('Total Turnos', ascending=False)
        st.dataframe(resumen, use_container_width=True)
    else:
        st.info("No hay suficientes datos para generar reportes")

elif opcion == "⚙️ Configuración":
    st.header("⚙️ Configuración")
    
    st.subheader("📋 Códigos de Turnos")
    df_codigos = pd.DataFrame([
        {"Código": k, "Descripción": v, "Tipo": "Especial" if k in ['VC', 'CP', 'PA', 'inc', 'cap', ''] else "Turno Normal"} 
        for k, v in CODIGOS_TURNOS.items()
    ])
    st.dataframe(df_codigos, use_container_width=True)
    
    st.subheader("📥 Importar/Exportar Datos")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Exportar datos**")
        if st.button("📥 Preparar exportación"):
            # Exportar empleados y turnos
            df_emp = pd.read_sql("SELECT * FROM empleados", conn)
            df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
            
            # Crear archivo Excel en memoria
            output = pd.ExcelWriter('turnos_export.xlsx', engine='openpyxl')
            df_emp.to_excel(output, sheet_name='Empleados', index=False)
            df_turnos.to_excel(output, sheet_name='Turnos', index=False)
            output.close()
            
            with open('turnos_export.xlsx', 'rb') as f:
                st.download_button(
                    label="📥 Descargar Excel",
                    data=f,
                    file_name=f'turnos_febrero_2026_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
    
    with col2:
        st.write("**Importar datos**")
        st.info("Funcionalidad en desarrollo - Próximamente podrás importar desde Excel")

# Cerrar conexión
conn.close()

# Footer
st.markdown("---")
st.markdown("© 2026 - Sistema de Gestión de Turnos v2.0")