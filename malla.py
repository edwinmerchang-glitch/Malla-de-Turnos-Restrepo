import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
from utils import *

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Turnos - Febrero 2026",
    page_icon="📅",
    layout="wide"
)

# Inicializar base de datos
init_db()
cargar_datos_ejemplo()

# Título
st.title("📅 Gestión de Malla de Turnos - Febrero 2026")
st.markdown("---")

# Sidebar para navegación
st.sidebar.title("📋 Menú Principal")
opcion = st.sidebar.selectbox(
    "Seleccionar vista",
    ["📊 Vista de Turnos", "👥 Gestión de Empleados", "📈 Reportes", "⚙️ Configuración"]
)

# Obtener días de febrero
dias_febrero = get_febrero_dias()
dias_str = [d.strftime("%d/%m") for d in dias_febrero]
dias_semana = [get_dia_semana(d) for d in dias_febrero]

# Conectar a BD
conn = sqlite3.connect('data/turnos.db')

if opcion == "📊 Vista de Turnos":
    st.header("📊 Malla de Turnos")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
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
    
    df_vista = pd.DataFrame(turnos_data)
    
    # Mostrar tabla con estilo
    st.dataframe(
        df_vista,
        use_container_width=True,
        height=600,
        column_config={
            "Cargo": st.column_config.TextColumn("Cargo", width="medium"),
            "Nombre": st.column_config.TextColumn("Nombre", width="medium"),
            "Área": st.column_config.TextColumn("Área", width="small"),
            **{fecha: st.column_config.TextColumn(f"{fecha}\n{dia}", width="small") 
               for fecha, dia in zip(dias_str, dias_semana)}
        }
    )
    
    # Editor de turnos
    st.markdown("---")
    st.subheader("✏️ Editar Turno")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        empleado = st.selectbox("Seleccionar empleado", 
                                df_empleados['nombre'].tolist())
    with col2:
        fecha_edit = st.date_input("Fecha", 
                                   min_value=datetime(2026,2,1),
                                   max_value=datetime(2026,2,28))
    with col3:
        codigo_turno = st.selectbox("Código de turno",
                                    options=[''] + list(CODIGOS_TURNOS.keys()),
                                    format_func=lambda x: f"{x} - {CODIGOS_TURNOS.get(x, '')}")
    with col4:
        if st.button("💾 Guardar Turno", type="primary"):
            empleado_id = df_empleados[df_empleados['nombre'] == empleado]['id'].iloc[0]
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO turnos 
                            (empleado_id, fecha, codigo_turno)
                            VALUES (?, ?, ?)''',
                            (empleado_id, fecha_edit.strftime('%Y-%m-%d'), codigo_turno))
            conn.commit()
            st.success("Turno guardado correctamente!")
            st.rerun()

elif opcion == "👥 Gestión de Empleados":
    st.header("👥 Gestión de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Empleados", "➕ Agregar Empleado", "🗑️ Eliminar Empleado"])
    
    with tab1:
        df_emp = pd.read_sql("SELECT * FROM empleados ORDER BY area, nombre", conn)
        st.dataframe(df_emp, use_container_width=True)
    
    with tab2:
        st.subheader("Agregar Nuevo Empleado")
        with st.form("form_empleado"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre completo")
                cargo = st.text_input("Cargo")
                documento = st.text_input("Documento")
            with col2:
                area = st.selectbox("Área", ["TIENDA", "DOMI"])
                horario_entrada = st.time_input("Horario entrada", value=datetime.strptime("08:00", "%H:%M").time())
                horario_salida = st.time_input("Horario salida", value=datetime.strptime("17:00", "%H:%M").time())
            
            submitted = st.form_submit_button("✅ Agregar Empleado")
            if submitted:
                cursor = conn.cursor()
                try:
                    cursor.execute('''INSERT INTO empleados 
                                    (nombre, cargo, documento, area, horario_entrada, horario_salida)
                                    VALUES (?, ?, ?, ?, ?, ?)''',
                                    (nombre, cargo, documento, area, 
                                     horario_entrada.strftime("%H:%M"), 
                                     horario_salida.strftime("%H:%M")))
                    conn.commit()
                    st.success("Empleado agregado correctamente!")
                except sqlite3.IntegrityError:
                    st.error("Ya existe un empleado con ese documento")
    
    with tab3:
        st.subheader("Eliminar Empleado")
        empleado_eliminar = st.selectbox("Seleccionar empleado a eliminar",
                                        pd.read_sql("SELECT nombre FROM empleados ORDER BY nombre", conn)['nombre'].tolist())
        if st.button("🗑️ Eliminar Empleado", type="secondary"):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM turnos WHERE empleado_id = (SELECT id FROM empleados WHERE nombre = ?)",
                          (empleado_eliminar,))
            cursor.execute("DELETE FROM empleados WHERE nombre = ?", (empleado_eliminar,))
            conn.commit()
            st.success("Empleado eliminado correctamente!")
            st.rerun()

elif opcion == "📈 Reportes":
    st.header("📈 Reportes y Estadísticas")
    
    # Cargar datos
    df_emp = pd.read_sql("SELECT * FROM empleados", conn)
    df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
    
    if not df_turnos.empty:
        # Merge con empleados
        df_report = df_turnos.merge(df_emp[['id', 'nombre', 'area']], 
                                    left_on='empleado_id', right_on='id')
        
        # Estadísticas por área
        st.subheader("Distribución de Turnos por Área")
        df_area = df_report.groupby('area').size().reset_index(name='cantidad')
        fig = px.pie(df_area, values='cantidad', names='area', title="Turnos por Área")
        st.plotly_chart(fig, use_container_width=True)
        
        # Top turnos más usados
        st.subheader("Top 10 Códigos de Turno más usados")
        top_turnos = df_report['codigo_turno'].value_counts().head(10).reset_index()
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
        st.dataframe(resumen, use_container_width=True)
    else:
        st.info("No hay datos de turnos para mostrar")

elif opcion == "⚙️ Configuración":
    st.header("⚙️ Configuración")
    
    st.subheader("Códigos de Turnos")
    df_codigos = pd.DataFrame([
        {"Código": k, "Descripción": v} for k, v in CODIGOS_TURNOS.items()
    ])
    st.dataframe(df_codigos, use_container_width=True)
    
    st.subheader("Importar/Exportar Datos")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Exportar datos")
        if st.button("📥 Exportar a Excel"):
            # Exportar empleados
            df_emp = pd.read_sql("SELECT * FROM empleados", conn)
            df_turnos = pd.read_sql("SELECT * FROM turnos", conn)
            
            with pd.ExcelWriter('exportacion_turnos.xlsx') as writer:
                df_emp.to_excel(writer, sheet_name='Empleados', index=False)
                df_turnos.to_excel(writer, sheet_name='Turnos', index=False)
            
            with open('exportacion_turnos.xlsx', 'rb') as f:
                st.download_button('Descargar Excel', f, file_name='turnos_febrero_2026.xlsx')
    
    with col2:
        st.write("Importar datos")
        archivo = st.file_uploader("Seleccionar archivo Excel", type=['xlsx'])
        if archivo and st.button("Importar"):
            # Aquí iría la lógica de importación
            st.info("Funcionalidad en desarrollo")

# Cerrar conexión
conn.close()

# Footer
st.markdown("---")
st.markdown("© 2026 - Sistema de Gestión de Turnos v1.0")