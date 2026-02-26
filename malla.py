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
    if st.button("✏️ Asignar manual", use_container_width=True):  # NUEVO BOTÓN
        cambiar_pagina("Asignacion manual")

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

# ========== ASIGNACIÓN MANUAL DE TURNOS ==========
elif op == "Asignacion manual":
    st.subheader("✏️ Asignación manual de turnos")
    
    # Crear pestañas para diferentes vistas
    tab1, tab2, tab3 = st.tabs(["📅 Asignar turnos", "📋 Ver asignaciones", "🗑️ Eliminar asignaciones"])
    
    with tab1:  # PESTAÑA DE ASIGNACIÓN
        st.markdown("### Asignar turno a empleado")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Seleccionar empleado
            empleados = session.query(Empleado).all()
            if empleados:
                empleado_opciones = {f"{e.nombre} ({e.area if e.area else 'Sin área'})": e.id for e in empleados}
                empleado_sel = st.selectbox("Seleccionar empleado", list(empleado_opciones.keys()))
                empleado_id = empleado_opciones[empleado_sel]
                empleado = session.query(Empleado).get(empleado_id)
                
                # Mostrar info del empleado
                if empleado:
                    st.info(f"**Área:** {empleado.area if empleado.area else 'No asignada'} | **Cargo:** {empleado.cargo if empleado.cargo else 'No asignado'}")
            else:
                st.warning("⚠️ No hay empleados registrados. Crea empleados primero.")
                empleado = None
        
        with col2:
            # Seleccionar turno
            turnos = session.query(Turno).all()
            if turnos:
                turno_opciones = {f"{t.nombre} ({t.inicio} - {t.fin})": t.id for t in turnos}
                turno_sel = st.selectbox("Seleccionar turno", list(turno_opciones.keys()))
                turno_id = turno_opciones[turno_sel]
            else:
                st.warning("⚠️ No hay turnos registrados. Crea turnos primero.")
                turno_id = None
        
        # Seleccionar fecha
        fecha_asignacion = st.date_input("Fecha del turno", date.today())
        
        # Botón para asignar
        if st.button("✅ Asignar turno", use_container_width=True, type="primary"):
            if not empleado:
                st.error("❌ No hay empleado seleccionado")
            elif not turno_id:
                st.error("❌ No hay turno seleccionado")
            else:
                # Verificar si ya existe una asignación para ese empleado en esa fecha
                existe = session.query(Asignacion).filter_by(
                    empleado_id=empleado_id, 
                    fecha=fecha_asignacion
                ).first()
                
                if existe:
                    st.warning(f"⚠️ El empleado ya tiene un turno asignado para esa fecha")
                    
                    # Opción para reemplazar
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Reemplazar turno"):
                            existe.turno_id = turno_id
                            session.commit()
                            st.success("✅ Turno reemplazado correctamente")
                            st.rerun()
                    with col2:
                        if st.button("❌ Cancelar"):
                            st.rerun()
                else:
                    # Crear nueva asignación
                    nueva_asignacion = Asignacion(
                        empleado_id=empleado_id,
                        fecha=fecha_asignacion,
                        turno_id=turno_id
                    )
                    session.add(nueva_asignacion)
                    session.commit()
                    st.success(f"✅ Turno asignado correctamente a {empleado.nombre}")
                    st.balloons()
                    st.rerun()
        
        # Mostrar asignaciones del día
        st.markdown("---")
        st.markdown(f"### 📅 Asignaciones para {fecha_asignacion.strftime('%d/%m/%Y')}")
        
        asignaciones_dia = session.query(Asignacion).filter_by(fecha=fecha_asignacion).all()
        if asignaciones_dia:
            data_dia = []
            for a in asignaciones_dia:
                data_dia.append({
                    "Empleado": a.empleado.nombre if a.empleado else "N/A",
                    "Área": a.empleado.area if a.empleado and a.empleado.area else "N/A",
                    "Turno": a.turno.nombre if a.turno else "N/A",
                    "Hora": f"{a.turno.inicio} - {a.turno.fin}" if a.turno else "N/A"
                })
            st.dataframe(pd.DataFrame(data_dia), use_container_width=True)
        else:
            st.info("ℹ️ No hay asignaciones para esta fecha")
    
    with tab2:  # PESTAÑA DE VER ASIGNACIONES
        st.markdown("### Ver asignaciones por período")
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio", date.today(), key="ver_inicio")
        with col2:
            fecha_fin = st.date_input("Fecha fin", date.today() + timedelta(days=7), key="ver_fin")
        
        # Filtro por empleado
        empleados = session.query(Empleado).all()
        empleado_opciones = {"Todos los empleados": None}
        empleado_opciones.update({f"{e.nombre}": e.id for e in empleados})
        empleado_filtro = st.selectbox("Filtrar por empleado", list(empleado_opciones.keys()))
        
        if st.button("🔍 Buscar asignaciones"):
            query = session.query(Asignacion).filter(
                Asignacion.fecha.between(fecha_inicio, fecha_fin)
            )
            
            if empleado_filtro != "Todos los empleados" and empleado_opciones[empleado_filtro]:
                query = query.filter_by(empleado_id=empleado_opciones[empleado_filtro])
            
            asignaciones = query.all()
            
            if asignaciones:
                data = []
                for a in asignaciones:
                    data.append({
                        "Fecha": a.fecha.strftime("%d/%m/%Y"),
                        "Empleado": a.empleado.nombre if a.empleado else "N/A",
                        "Área": a.empleado.area if a.empleado and a.empleado.area else "N/A",
                        "Turno": a.turno.nombre if a.turno else "N/A",
                        "Hora inicio": a.turno.inicio if a.turno else "N/A",
                        "Hora fin": a.turno.fin if a.turno else "N/A"
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                st.metric("Total asignaciones", len(df))
            else:
                st.info("ℹ️ No hay asignaciones en el período seleccionado")
    
    with tab3:  # PESTAÑA DE ELIMINAR
        st.markdown("### Eliminar asignaciones")
        
        # Seleccionar asignación a eliminar
        asignaciones = session.query(Asignacion).order_by(Asignacion.fecha.desc()).limit(50).all()
        
        if asignaciones:
            opciones_asignaciones = {}
            for a in asignaciones:
                empleado_nombre = a.empleado.nombre if a.empleado else "N/A"
                turno_nombre = a.turno.nombre if a.turno else "N/A"
                fecha_str = a.fecha.strftime("%d/%m/%Y")
                opciones_asignaciones[f"{fecha_str} - {empleado_nombre} - {turno_nombre}"] = a.id
            
            asignacion_sel = st.selectbox("Seleccionar asignación a eliminar", list(opciones_asignaciones.keys()))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Eliminar seleccionada", use_container_width=True):
                    asignacion_id = opciones_asignaciones[asignacion_sel]
                    asignacion = session.query(Asignacion).get(asignacion_id)
                    if asignacion:
                        session.delete(asignacion)
                        session.commit()
                        st.success("✅ Asignación eliminada correctamente")
                        st.rerun()
            
            with col2:
                if st.button("🗑️ Eliminar todas del período", use_container_width=True):
                    st.warning("⚠️ Esta acción eliminará todas las asignaciones")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        fecha_eliminar = st.date_input("Fecha límite", date.today())
                        if st.button("Confirmar eliminación masiva"):
                            session.query(Asignacion).filter(Asignacion.fecha <= fecha_eliminar).delete()
                            session.commit()
                            st.success("✅ Asignaciones eliminadas")
                            st.rerun()
        else:
            st.info("ℹ️ No hay asignaciones para eliminar")

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

# ========== CALENDARIO TIPO GOOGLE CALENDAR ==========
elif op == "Calendario":
    st.subheader("📆 Calendario de turnos")
    
    # Intentar importar streamlit-calendar
    try:
        from streamlit_calendar import calendar
    except ImportError:
        st.error("❌ Necesitas instalar streamlit-calendar: pip install streamlit-calendar")
        st.stop()
    
    # Obtener todas las áreas únicas
    empleados = session.query(Empleado).all()
    areas = list(set([e.area for e in empleados if e.area]))
    areas.sort()
    areas_opciones = ["Todas las áreas"] + areas
    
    # Filtros en el sidebar del calendario
    with st.sidebar:
        st.markdown("### 🎯 Filtros del calendario")
        
        if not areas:
            st.info("ℹ️ No hay áreas registradas")
            area_filtro = "Todas las áreas"
        else:
            area_filtro = st.selectbox("Filtrar por área", areas_opciones, key="cal_area")
        
        # Selector de mes
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026, key="cal_año")
        mes = st.selectbox("Mes", meses, index=1, key="cal_mes")  # Febrero por defecto
    
    # Calcular fechas del mes
    mes_num = meses.index(mes) + 1
    from calendar import monthrange
    dias_mes = monthrange(año, mes_num)[1]
    fecha_inicio_mes = date(año, mes_num, 1)
    fecha_fin_mes = date(año, mes_num, dias_mes)
    
    # Obtener asignaciones del mes
    asignaciones = session.query(Asignacion).filter(
        Asignacion.fecha.between(fecha_inicio_mes, fecha_fin_mes)
    ).all()
    
    # Preparar eventos para el calendario
    eventos = []
    
    # Colores para diferentes áreas
    colores_area = {
        "Administración": "#FF6B6B",  # Rojo claro
        "Producción": "#4ECDC4",       # Turquesa
        "Calidad": "#45B7D1",          # Azul claro
        "Mantenimiento": "#96CEB4",    # Verde menta
        "Logística": "#FFEAA7",         # Amarillo claro
        "Ventas": "#D4A5A5",            # Rosa
        "RRHH": "#9B59B6",              # Púrpura
        "Sistemas": "#3498DB",          # Azul
        "Pasillos": "#F39C12",          # Naranja
        "Cajas": "#27AE60",             # Verde
        "Equipos médicos": "#E74C3C",   # Rojo
    }
    
    for a in asignaciones:
        if a.empleado and a.turno:
            # Aplicar filtro de área
            if area_filtro == "Todas las áreas" or (a.empleado.area == area_filtro):
                # Determinar color basado en el área
                area = a.empleado.area if a.empleado.area else "Sin área"
                color = colores_area.get(area, "#3788d8")  # Color por defecto azul
                
                # Formatear fecha
                fecha_str = a.fecha.strftime("%Y-%m-%d")
                
                # Crear título del evento
                titulo = f"{a.empleado.nombre} - {a.turno.nombre}"
                
                # Crear descripción detallada
                descripcion = f"""
                **Empleado:** {a.empleado.nombre}
                **Área:** {a.empleado.area if a.empleado.area else 'No asignada'}
                **Cargo:** {a.empleado.cargo if a.empleado.cargo else 'No asignado'}
                **Turno:** {a.turno.nombre}
                **Horario:** {a.turno.inicio} - {a.turno.fin}
                """
                
                # Crear evento
                evento = {
                    "title": titulo,
                    "start": fecha_str,
                    "end": fecha_str,
                    "color": color,
                    "backgroundColor": color,
                    "borderColor": "darken",
                    "textColor": "white",
                    "extendedProps": {
                        "empleado": a.empleado.nombre,
                        "area": a.empleado.area,
                        "cargo": a.empleado.cargo,
                        "turno": a.turno.nombre,
                        "hora_inicio": a.turno.inicio,
                        "hora_fin": a.turno.fin,
                        "descripcion": descripcion
                    }
                }
                eventos.append(evento)
    
    # Configuración del calendario
    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "initialView": "dayGridMonth",
        "navLinks": True,
        "height": "auto",
        "contentHeight": 600,
        "slotMinTime": "06:00:00",
        "slotMaxTime": "22:00:00",
        "expandRows": True,
        "stickyHeaderScroll": False,
        "nowIndicator": True,
        "selectMirror": True,
        "eventDisplay": "block",
        "displayEventTime": False,  # No mostrar hora en el evento (ya está en el turno)
        "eventTimeFormat": {
            "hour": "2-digit",
            "minute": "2-digit",
            "hour12": True
        }
    }
    
    # Mostrar calendario
    if eventos:
        calendar_widget = calendar(
            events=eventos,
            options=calendar_options,
            custom_css="""
                .fc-event {
                    cursor: pointer;
                    border-radius: 4px;
                    margin: 2px 0;
                    padding: 2px 4px;
                    font-size: 0.85em;
                    border: none !important;
                }
                .fc-event:hover {
                    opacity: 0.9;
                    transform: scale(1.02);
                    transition: all 0.2s;
                }
                .fc-day-today {
                    background-color: rgba(52, 152, 219, 0.1) !important;
                }
                .fc-toolbar-title {
                    font-size: 1.5em !important;
                    font-weight: bold;
                }
                .fc-button-primary {
                    background-color: #4F46E5 !important;
                    border-color: #4F46E5 !important;
                }
                .fc-button-primary:hover {
                    background-color: #6366F1 !important;
                    border-color: #6366F1 !important;
                }
            """
        )
        
        st.markdown("### 📅 Vista de calendario")
        st.write(calendar_widget)
        
        # Mostrar estadísticas
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        # Filtrar eventos para estadísticas
        eventos_filtrados = [e for e in eventos if area_filtro == "Todas las áreas" or e["extendedProps"]["area"] == area_filtro]
        
        col1.metric("Total turnos", len(eventos_filtrados))
        
        empleados_unicos = len(set([e["extendedProps"]["empleado"] for e in eventos_filtrados]))
        col2.metric("Empleados", empleados_unicos)
        
        areas_unicas = len(set([e["extendedProps"]["area"] for e in eventos_filtrados if e["extendedProps"]["area"]]))
        col3.metric("Áreas", areas_unicas)
        
        turnos_unicos = len(set([e["extendedProps"]["turno"] for e in eventos_filtrados]))
        col4.metric("Turnos", turnos_unicos)
        
    else:
        st.info(f"ℹ️ No hay turnos asignados para {mes} {año}")
        
        # Botón para ir a asignación manual
        if st.button("➕ Asignar turnos manualmente", use_container_width=True):
            cambiar_pagina("Asignacion manual")
            st.rerun()
    
    # Leyenda de colores por área
    st.markdown("### 🎨 Leyenda de colores por área")
    
    # Obtener áreas únicas de los eventos
    areas_en_eventos = set()
    for e in eventos:
        area = e["extendedProps"]["area"]
        if area and area != "No asignada":
            areas_en_eventos.add(area)
    
    if areas_en_eventos:
        cols = st.columns(4)
        for i, area in enumerate(sorted(areas_en_eventos)):
            color = colores_area.get(area, "#3788d8")
            with cols[i % 4]:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; margin: 5px 0;">
                        <div style="width: 20px; height: 20px; background-color: {color}; border-radius: 4px; margin-right: 8px;"></div>
                        <span>{area}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("No hay áreas con turnos asignados")
    
    # Botón para volver a la tabla (opcional)
    with st.expander("📋 Ver vista de tabla"):
        # Mostrar tabla tradicional
        data_tabla = []
        for e in eventos:
            data_tabla.append({
                "Fecha": e["start"],
                "Empleado": e["extendedProps"]["empleado"],
                "Área": e["extendedProps"]["area"],
                "Turno": e["extendedProps"]["turno"],
                "Horario": f"{e['extendedProps']['hora_inicio']} - {e['extendedProps']['hora_fin']}"
            })
        
        if data_tabla:
            df_tabla = pd.DataFrame(data_tabla)
            st.dataframe(df_tabla, use_container_width=True)

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