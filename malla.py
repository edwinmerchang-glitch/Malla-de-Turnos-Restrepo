import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite

st.set_page_config("Malla de Turnos", layout="wide")

# -------- LOGIN --------
def login():
    st.title("🔐 Ingreso al sistema")
    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        session_db = Session()
        emp = session_db.query(Empleado).filter_by(usuario=user, password=pwd).first()
        if emp:
            st.session_state["user"] = emp
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state["user"]
session = Session()

# -------- MENÚ CON BOTONES --------
st.sidebar.title("📅 Malla de Turnos")
st.sidebar.markdown(f"**Usuario:** {user.nombre}")
st.sidebar.markdown(f"**Rol:** {user.rol}")
st.sidebar.markdown("---")

# Inicializar la página actual si no existe
if "pagina_actual" not in st.session_state:
    st.session_state.pagina_actual = "Calendario"

# Función para cambiar de página
def cambiar_pagina(pagina):
    st.session_state.pagina_actual = pagina

# Crear botones en el sidebar
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("📅 Calendario", use_container_width=True):
        cambiar_pagina("Calendario")
    if st.button("👥 Empleados", use_container_width=True):
        cambiar_pagina("Empleados")
    if st.button("⏰ Turnos", use_container_width=True):
        cambiar_pagina("Turnos")

with col2:
    if st.button("🤖 Generar", use_container_width=True):
        cambiar_pagina("Generar malla")
    if st.button("📊 Reportes", use_container_width=True):
        cambiar_pagina("Reportes")
    if st.button("🛡 Backup", use_container_width=True):
        cambiar_pagina("Backup")

# Mostrar la página actual con un indicador
st.sidebar.markdown("---")
st.sidebar.info(f"📍 Página actual: **{st.session_state.pagina_actual}**")

# Botón de cerrar sesión
if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# -------- CONTENIDO SEGÚN LA PÁGINA SELECCIONADA --------
op = st.session_state.pagina_actual

# -------- EMPLEADOS --------
if op == "Empleados":
    st.subheader("👥 Empleados")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Nuevo empleado")
        with st.form("nuevo_emp"):
            n = st.text_input("Nombre")
            r = st.selectbox("Rol", ["admin", "empleado"])
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Crear", use_container_width=True):
                session.add(Empleado(nombre=n, rol=r, usuario=u, password=p))
                session.commit()
                st.success("Empleado creado")
                st.rerun()
    
    with col2:
        st.markdown("### Lista de empleados")
        empleados = session.query(Empleado).all()
        data = [{"ID": e.id, "Nombre": e.nombre, "Usuario": e.usuario, "Rol": e.rol} for e in empleados]
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

# -------- TURNOS --------
elif op == "Turnos":
    st.subheader("⏰ Turnos")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Nuevo turno")
        with st.form("nuevo_turno"):
            n = st.text_input("Nombre")
            hi = st.text_input("Hora inicio")
            hf = st.text_input("Hora fin")
            if st.form_submit_button("Crear", use_container_width=True):
                session.add(Turno(nombre=n, inicio=hi, fin=hf))
                session.commit()
                st.success("Turno creado")
                st.rerun()
    
    with col2:
        st.markdown("### Lista de turnos")
        turnos = session.query(Turno).all()
        data = [{"ID": t.id, "Nombre": t.nombre, "Inicio": t.inicio, "Fin": t.fin} for t in turnos]
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

# -------- GENERADOR --------
elif op == "Generar malla":
    st.subheader("🤖 Generación automática de malla")

    col1, col2 = st.columns(2)
    
    with col1:
        inicio = st.date_input("Fecha inicio", date(2026, 2, 1))
    with col2:
        fin = st.date_input("Fecha fin", date(2026, 2, 28))

    # Mostrar resumen
    st.markdown("---")
    empleados_count = session.query(Empleado).count()
    turnos_count = session.query(Turno).count()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Empleados", empleados_count)
    col2.metric("Turnos", turnos_count)
    col3.metric("Días", (fin-inicio).days + 1)

    if st.button("🚀 Generar malla", use_container_width=True, type="primary"):
        fechas = [inicio + timedelta(days=i) for i in range((fin-inicio).days+1)]
        empleados = session.query(Empleado).all()
        turnos = session.query(Turno).all()
        
        if not empleados:
            st.error("❌ No hay empleados registrados")
        elif not turnos:
            st.error("❌ No hay turnos registrados")
        else:
            with st.spinner("Generando malla..."):
                asignaciones = generar_malla_inteligente(empleados, turnos, inicio, (fin-inicio).days+1)

                for emp_id, fecha, turno_nombre in asignaciones:
                    turno = session.query(Turno).filter_by(nombre=turno_nombre).first()
                    if turno:
                        session.add(Asignacion(
                            empleado_id=emp_id,
                            fecha=fecha,
                            turno_id=turno.id
                        ))
                session.commit()
                
                backup_sqlite()
                st.success(f"✅ Malla generada para {len(asignaciones)} turnos")
                
                # Mostrar vista previa
                st.markdown("### Vista previa")
                preview = asignaciones[:10]  # Mostrar solo 10
                data_preview = []
                for emp_id, fecha, turno_nom in preview:
                    empleado = next((e for e in empleados if e.id == emp_id), None)
                    data_preview.append({
                        "Fecha": fecha,
                        "Empleado": empleado.nombre if empleado else "N/A",
                        "Turno": turno_nom
                    })
                if data_preview:
                    st.dataframe(pd.DataFrame(data_preview))

# -------- CALENDARIO --------
elif op == "Calendario":
    st.subheader("📆 Calendario de turnos")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox("Mes", ["Febrero 2026", "Marzo 2026", "Abril 2026"])
    with col2:
        empleado_filtro = st.selectbox("Empleado", ["Todos"] + [e.nombre for e in session.query(Empleado).all()])
    
    asignaciones = session.query(Asignacion).all()
    
    data = []
    for a in asignaciones:
        if empleado_filtro == "Todos" or (a.empleado and a.empleado.nombre == empleado_filtro):
            data.append({
                "Fecha": a.fecha,
                "Empleado": a.empleado.nombre if a.empleado else "N/A",
                "Turno": a.turno.nombre if a.turno else "N/A",
                "Hora inicio": a.turno.inicio if a.turno else "N/A",
                "Hora fin": a.turno.fin if a.turno else "N/A"
            })
    
    df = pd.DataFrame(data)
    if not df.empty:
        # Ordenar por fecha
        df = df.sort_values("Fecha")
        st.dataframe(df, use_container_width=True)
        
        # Estadísticas
        st.markdown("### 📊 Resumen")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total turnos", len(df))
        col2.metric("Empleados", df["Empleado"].nunique())
        col3.metric("Turnos únicos", df["Turno"].nunique())
    else:
        st.info("ℹ️ No hay asignaciones registradas")

# -------- REPORTES --------
elif op == "Reportes":
    st.subheader("📊 Reportes")
    
    tipo_reporte = st.radio("Tipo de reporte", ["Por empleado", "Por turno", "General"], horizontal=True)
    
    asignaciones = session.query(Asignacion).all()
    data = []
    for a in asignaciones:
        data.append({
            "ID": a.id,
            "Empleado": a.empleado.nombre if a.empleado else "N/A",
            "Fecha": a.fecha,
            "Turno": a.turno.nombre if a.turno else "N/A",
            "Hora inicio": a.turno.inicio if a.turno else "N/A",
            "Hora fin": a.turno.fin if a.turno else "N/A"
        })
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        if tipo_reporte == "Por empleado":
            reporte = df.groupby("Empleado").size().reset_index(name="Total turnos")
            reporte = reporte.sort_values("Total turnos", ascending=False)
            st.dataframe(reporte, use_container_width=True)
            
            # Gráfico de barras
            st.bar_chart(reporte.set_index("Empleado"))
            
        elif tipo_reporte == "Por turno":
            reporte = df.groupby("Turno").size().reset_index(name="Cantidad")
            reporte = reporte.sort_values("Cantidad", ascending=False)
            st.dataframe(reporte, use_container_width=True)
            
            # Gráfico de barras
            st.bar_chart(reporte.set_index("Turno"))
            
        else:  # General
            st.dataframe(df, use_container_width=True)

        # Botón de descarga
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("📥 Descargar Excel", use_container_width=True):
                output = pd.ExcelWriter('temp.xlsx', engine='xlsxwriter')
                df.to_excel(output, index=False, sheet_name='Reporte')
                output.close()
                
                with open('temp.xlsx', 'rb') as f:
                    st.download_button(
                        "📥 Confirmar descarga",
                        f,
                        "reporte_turnos.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    else:
        st.info("ℹ️ No hay datos para generar reportes")

# -------- BACKUP --------
elif op == "Backup":
    st.subheader("🛡 Seguridad - Backups")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Crear backup")
        if st.button("🔄 Crear backup ahora", use_container_width=True, type="primary"):
            if backup_sqlite():
                st.success("✅ Backup generado correctamente")
            else:
                st.error("❌ Error al generar backup")
    
    with col2:
        st.markdown("### Restaurar backup")
        import os
        if os.path.exists("data/backups"):
            backups = os.listdir("data/backups")
            if backups:
                backup_seleccionado = st.selectbox("Seleccionar backup", backups)
                if st.button("♻️ Restaurar", use_container_width=True):
                    st.warning("⚠️ Función de restauración no implementada por seguridad")
            else:
                st.info("No hay backups disponibles")
    
    # Mostrar backups existentes
    st.markdown("---")
    st.markdown("### 📁 Backups disponibles")
    if os.path.exists("data/backups"):
        backups = os.listdir("data/backups")
        if backups:
            for i, b in enumerate(sorted(backups, reverse=True)[:10]):  # Mostrar últimos 10
                st.text(f"{i+1}. {b}")
        else:
            st.info("No hay backups aún")