import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite
import os

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
if user.area:
    st.sidebar.markdown(f"**Área:** {user.area}")
if user.cargo:
    st.sidebar.markdown(f"**Cargo:** {user.cargo}")
st.sidebar.markdown("---")

# Inicializar la página actual
if "pagina_actual" not in st.session_state:
    st.session_state.pagina_actual = "Calendario"

def cambiar_pagina(pagina):
    st.session_state.pagina_actual = pagina

# Botones del menú
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

st.sidebar.markdown("---")
st.sidebar.info(f"📍 Página actual: **{st.session_state.pagina_actual}**")

if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# -------- CONTENIDO --------
op = st.session_state.pagina_actual

# ========== EMPLEADOS ==========
if op == "Empleados":
    st.subheader("👥 Gestión de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de empleados", "➕ Nuevo empleado", "✏️ Editar/Eliminar"])
    
    # TAB 1: LISTA DE EMPLEADOS
    with tab1:
        st.markdown("### Lista completa de empleados")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_area = st.text_input("🔍 Filtrar por área")
        with col2:
            filtro_cargo = st.text_input("🔍 Filtrar por cargo")
        with col3:
            filtro_nombre = st.text_input("🔍 Filtrar por nombre")
        
        empleados = session.query(Empleado).all()
        
        # Aplicar filtros
        if filtro_area:
            empleados = [e for e in empleados if e.area and filtro_area.lower() in e.area.lower()]
        if filtro_cargo:
            empleados = [e for e in empleados if e.cargo and filtro_cargo.lower() in e.cargo.lower()]
        if filtro_nombre:
            empleados = [e for e in empleados if filtro_nombre.lower() in e.nombre.lower()]
        
        if empleados:
            data = []
            for e in empleados:
                data.append({
                    "ID": e.id,
                    "Nombre": e.nombre,
                    "Área": e.area if e.area else "No asignada",
                    "Cargo": e.cargo if e.cargo else "No asignado",
                    "Usuario": e.usuario,
                    "Rol": e.rol
                })
            df = pd.DataFrame(data)
            
            # Estadísticas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total empleados", len(empleados))
            col2.metric("Áreas distintas", df["Área"].nunique())
            col3.metric("Cargos distintos", df["Cargo"].nunique())
            
            st.dataframe(df, use_container_width=True)
    
    # TAB 2: NUEVO EMPLEADO
    with tab2:
        st.markdown("### Crear nuevo empleado")
        
        with st.form("nuevo_emp"):
            col1, col2 = st.columns(2)
            
            with col1:
                n = st.text_input("Nombre completo *")
                u = st.text_input("Usuario *")
                r = st.selectbox("Rol *", ["empleado", "admin"])
                
            with col2:
                area = st.text_input("Área")
                cargo = st.text_input("Cargo")
                p = st.text_input("Contraseña *", type="password")
            
            submitted = st.form_submit_button("✅ Crear empleado", use_container_width=True)
            
            if submitted:
                if not n or not u or not p:
                    st.error("❌ Los campos marcados con * son obligatorios")
                else:
                    existe = session.query(Empleado).filter_by(usuario=u).first()
                    if existe:
                        st.error(f"❌ El usuario '{u}' ya existe")
                    else:
                        session.add(Empleado(
                            nombre=n, 
                            rol=r, 
                            usuario=u, 
                            password=p,
                            area=area if area else None,
                            cargo=cargo if cargo else None
                        ))
                        session.commit()
                        st.success(f"✅ Empleado '{n}' creado correctamente")
                        st.rerun()
    
    # TAB 3: EDITAR/ELIMINAR
    with tab3:
        st.markdown("### Editar o eliminar empleados")
        
        empleados = session.query(Empleado).all()
        if empleados:
            opciones = {f"{e.nombre} ({e.usuario})": e.id for e in empleados}
            seleccion = st.selectbox("Seleccionar empleado", list(opciones.keys()))
            emp_id = opciones[seleccion]
            emp = session.query(Empleado).get(emp_id)
            
            if emp:
                with st.form("editar_emp"):
                    st.markdown(f"**Editando: {emp.nombre}**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nombre_edit = st.text_input("Nombre", value=emp.nombre)
                        usuario_edit = st.text_input("Usuario", value=emp.usuario)
                        rol_edit = st.selectbox("Rol", ["empleado", "admin"], 
                                               index=0 if emp.rol == "empleado" else 1)
                        
                    with col2:
                        area_edit = st.text_input("Área", value=emp.area if emp.area else "")
                        cargo_edit = st.text_input("Cargo", value=emp.cargo if emp.cargo else "")
                        password_edit = st.text_input("Nueva contraseña (dejar vacío para no cambiar)", 
                                                     type="password")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
                    with col2:
                        eliminar = st.form_submit_button("🗑️ Eliminar", use_container_width=True)
                    
                    if guardar:
                        emp.nombre = nombre_edit
                        emp.usuario = usuario_edit
                        emp.rol = rol_edit
                        emp.area = area_edit if area_edit else None
                        emp.cargo = cargo_edit if cargo_edit else None
                        if password_edit:
                            emp.password = password_edit
                        session.commit()
                        st.success("✅ Cambios guardados")
                        st.rerun()
                    
                    if eliminar:
                        if emp.id == user.id:
                            st.error("❌ No puedes eliminarte a ti mismo")
                        else:
                            session.delete(emp)
                            session.commit()
                            st.success("✅ Empleado eliminado")
                            st.rerun()

# ========== TURNOS ==========
elif op == "Turnos":
    st.subheader("⏰ Gestión de Turnos")
    
    tab1, tab2 = st.tabs(["📋 Lista de turnos", "➕ Nuevo turno"])
    
    with tab1:
        turnos = session.query(Turno).all()
        data = [{"ID": t.id, "Nombre": t.nombre, "Inicio": t.inicio, "Fin": t.fin} for t in turnos]
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        with st.form("nuevo_turno"):
            n = st.text_input("Nombre del turno")
            hi = st.text_input("Hora inicio (HH:MM)")
            hf = st.text_input("Hora fin (HH:MM)")
            if st.form_submit_button("Crear turno"):
                if n and hi and hf:
                    session.add(Turno(nombre=n, inicio=hi, fin=hf))
                    session.commit()
                    st.success("✅ Turno creado")
                    st.rerun()
                else:
                    st.error("❌ Todos los campos son obligatorios")

# ========== GENERAR MALLA ==========
elif op == "Generar malla":
    st.subheader("🤖 Generación automática de malla")

    col1, col2 = st.columns(2)
    with col1:
        inicio = st.date_input("Fecha inicio", date(2026, 2, 1))
    with col2:
        fin = st.date_input("Fecha fin", date(2026, 2, 28))

    empleados_count = session.query(Empleado).count()
    turnos_count = session.query(Turno).count()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Empleados", empleados_count)
    col2.metric("Turnos", turnos_count)
    col3.metric("Días", (fin-inicio).days + 1)

    if st.button("🚀 Generar malla", use_container_width=True):
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

# ========== CALENDARIO ==========
elif op == "Calendario":
    st.subheader("📆 Calendario de turnos")
    
    # Obtener todas las áreas únicas
    empleados = session.query(Empleado).all()
    areas = list(set([e.area for e in empleados if e.area]))  # Áreas que no son None
    areas.sort()  # Ordenar alfabéticamente
    areas_opciones = ["Todas las áreas"] + areas
    
    # Si no hay áreas, mostrar mensaje
    if not areas:
        st.info("ℹ️ No hay áreas registradas. Agrega áreas a los empleados primero.")
        area_filtro = "Todas las áreas"
    else:
        area_filtro = st.selectbox("Filtrar por área", areas_opciones)
    
    asignaciones = session.query(Asignacion).all()
    
    data = []
    for a in asignaciones:
        # Aplicar filtro por área
        if area_filtro == "Todas las áreas" or (a.empleado and a.empleado.area == area_filtro):
            data.append({
                "Fecha": a.fecha,
                "Empleado": a.empleado.nombre if a.empleado else "N/A",
                "Área": a.empleado.area if a.empleado and a.empleado.area else "N/A",
                "Cargo": a.empleado.cargo if a.empleado and a.empleado.cargo else "N/A",
                "Turno": a.turno.nombre if a.turno else "N/A",
                "Hora inicio": a.turno.inicio if a.turno else "N/A",
                "Hora fin": a.turno.fin if a.turno else "N/A"
            })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("Fecha")
        st.dataframe(df, use_container_width=True)
        
        # Estadísticas por área
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total turnos", len(df))
        col2.metric("Empleados", df["Empleado"].nunique())
        col3.metric("Áreas", df["Área"].nunique())
        col4.metric("Turnos únicos", df["Turno"].nunique())
        
        # Mostrar resumen por área
        if area_filtro == "Todas las áreas":
            st.markdown("### 📊 Resumen por área")
            resumen_area = df.groupby("Área").agg({
                "Empleado": "nunique",
                "Turno": "count"
            }).rename(columns={"Empleado": "Empleados", "Turno": "Total turnos"})
            st.dataframe(resumen_area, use_container_width=True)
    else:
        st.info("ℹ️ No hay asignaciones registradas para el área seleccionada")

# ========== REPORTES ==========
elif op == "Reportes":
    st.subheader("📊 Reportes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_reporte = st.radio("Tipo de reporte", 
                               ["General", "Por empleado", "Por área"], 
                               horizontal=True)
    
    with col2:
        # Filtro de área para reportes
        empleados = session.query(Empleado).all()
        areas = list(set([e.area for e in empleados if e.area]))
        areas.sort()
        areas_opciones = ["Todas las áreas"] + areas
        area_reporte = st.selectbox("Filtrar por área", areas_opciones)
    
    asignaciones = session.query(Asignacion).all()
    data = []
    for a in asignaciones:
        # Aplicar filtro de área
        if area_reporte == "Todas las áreas" or (a.empleado and a.empleado.area == area_reporte):
            data.append({
                "Fecha": a.fecha,
                "Empleado": a.empleado.nombre if a.empleado else "N/A",
                "Área": a.empleado.area if a.empleado and a.empleado.area else "N/A",
                "Cargo": a.empleado.cargo if a.empleado and a.empleado.cargo else "N/A",
                "Turno": a.turno.nombre if a.turno else "N/A"
            })
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        if tipo_reporte == "Por empleado":
            reporte = df.groupby(["Empleado", "Área", "Cargo"]).size().reset_index(name="Total turnos")
            reporte = reporte.sort_values("Total turnos", ascending=False)
            st.dataframe(reporte, use_container_width=True)
            
            # Gráfico de turnos por empleado
            st.bar_chart(reporte.set_index("Empleado")["Total turnos"])
            
        elif tipo_reporte == "Por área":
            reporte = df.groupby("Área").agg({
                "Empleado": "nunique",
                "Turno": "count"
            }).rename(columns={"Empleado": "Empleados", "Turno": "Total turnos"})
            reporte = reporte.sort_values("Total turnos", ascending=False)
            st.dataframe(reporte, use_container_width=True)
            
            # Gráfico de turnos por área
            st.bar_chart(reporte["Total turnos"])
            
        else:  # General
            st.dataframe(df, use_container_width=True)

        # Botón de descarga
        if st.button("📥 Descargar Excel"):
            output = pd.ExcelWriter('reporte.xlsx', engine='xlsxwriter')
            df.to_excel(output, index=False, sheet_name='Reporte')
            output.close()
            
            with open('reporte.xlsx', 'rb') as f:
                st.download_button(
                    "📥 Confirmar descarga",
                    f,
                    "reporte_turnos.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("ℹ️ No hay datos para generar reportes")

# ========== BACKUP ==========
elif op == "Backup":
    st.subheader("🛡 Seguridad - Backups")
    
    if st.button("🔄 Crear backup ahora", use_container_width=True):
        if backup_sqlite():
            st.success("✅ Backup generado correctamente")
        else:
            st.error("❌ Error al generar backup")
    
    st.markdown("---")
    st.markdown("### 📁 Backups disponibles")
    
    if os.path.exists("data/backups"):
        backups = os.listdir("data/backups")
        if backups:
            for i, b in enumerate(sorted(backups, reverse=True)[:10]):
                st.text(f"{i+1}. {b}")
        else:
            st.info("No hay backups aún")