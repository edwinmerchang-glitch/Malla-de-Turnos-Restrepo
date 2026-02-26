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

# Botones del menú según el rol
st.sidebar.markdown("### 📋 Menú principal")

col1, col2 = st.sidebar.columns(2)

# Botones visibles para TODOS los usuarios
with col1:
    if st.button("📅 Calendario", use_container_width=True):
        cambiar_pagina("Calendario")
    if st.button("👤 Mi perfil", use_container_width=True):  # NUEVO
        cambiar_pagina("Mi perfil")

with col2:
    if st.button("📊 Mis turnos", use_container_width=True):  # NUEVO
        cambiar_pagina("Mis turnos")

# Botones solo para ADMINISTRADORES
if user.rol == "admin":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Administración")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("👥 Empleados", use_container_width=True):
            cambiar_pagina("Empleados")
        if st.button("⏰ Turnos", use_container_width=True):
            cambiar_pagina("Turnos")
        if st.button("📊 Matriz turnos", use_container_width=True):
            cambiar_pagina("Matriz turnos")
    
    with col2:
        if st.button("✏️ Asignar manual", use_container_width=True):
            cambiar_pagina("Asignacion manual")
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
# Al inicio de la sección EMPLEADOS:
if op == "Empleados":
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

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
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

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
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

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

# ========== MATRIZ DE TURNOS (VISTA HORIZONTAL) ==========
elif op == "Matriz turnos":
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

elif op == "Matriz turnos":
    st.subheader("📊 Matriz de turnos - Vista horizontal")
    
    # Solo administradores pueden acceder
    if user.rol != "admin":
        st.error("❌ Solo los administradores pueden acceder a esta vista")
        st.stop()
    
    # Selección de mes y año
    col1, col2, col3 = st.columns(3)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes = st.selectbox("Mes", meses, index=1)  # Febrero por defecto
    with col2:
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
    with col3:
        areas = list(set([e.area for e in session.query(Empleado).all() if e.area]))
        areas.sort()
        area_filtro = st.selectbox("Filtrar por área", ["Todas"] + areas)
    
    # Calcular días del mes
    mes_num = meses.index(mes) + 1
    from calendar import monthrange
    dias_mes = monthrange(año, mes_num)[1]
    
    # Obtener empleados
    empleados = session.query(Empleado).all()
    if area_filtro != "Todas":
        empleados = [e for e in empleados if e.area == area_filtro]
    
    # Obtener turnos disponibles
    turnos = session.query(Turno).all()
    turnos_dict = {t.id: t.nombre for t in turnos}
    
    # Obtener asignaciones existentes
    fecha_inicio = date(año, mes_num, 1)
    fecha_fin = date(año, mes_num, dias_mes)
    
    asignaciones = session.query(Asignacion).filter(
        Asignacion.fecha.between(fecha_inicio, fecha_fin)
    ).all()
    
    # Crear matriz de asignaciones
    matriz = {}
    for a in asignaciones:
        if a.empleado_id not in matriz:
            matriz[a.empleado_id] = {}
        dia = a.fecha.day
        matriz[a.empleado_id][dia] = a.turno_id
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3 = st.tabs(["📋 Vista matriz", "✏️ Edición rápida", "📥 Carga masiva"])
    
    with tab1:  # VISTA MATRIZ
        st.markdown("### Vista de matriz de turnos")
        
        # Preparar datos
        data = []
        for emp in empleados:
            fila = {
                "Empleado": emp.nombre,
                "Área": emp.area if emp.area else "N/A",
                "Cargo": emp.cargo if emp.cargo else "N/A",
            }
            for dia in range(1, dias_mes + 1):
                turno_id = matriz.get(emp.id, {}).get(dia)
                if turno_id:
                    fila[f"D{dia}"] = turnos_dict.get(turno_id, "?")
                else:
                    fila[f"D{dia}"] = "—"
            data.append(fila)
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=600)
        
        # Leyenda de turnos
        with st.expander("📖 Leyenda de turnos"):
            cols = st.columns(4)
            for i, turno in enumerate(turnos):
                with cols[i % 4]:
                    st.markdown(f"**{turno.nombre}**: {turno.inicio} - {turno.fin}")
    
    with tab2:  # EDICIÓN RÁPIDA
        st.markdown("### Edición rápida de turnos")
        st.info("Selecciona un empleado y rango de fechas para asignar turnos masivamente")
        
        if not empleados:
            st.warning("No hay empleados disponibles")
        else:
            col1, col2 = st.columns(2)
            with col1:
                empleado_sel = st.selectbox("Empleado", [e.nombre for e in empleados])
                empleado = next(e for e in empleados if e.nombre == empleado_sel)
            
            with col2:
                turno_opciones = ["Descanso"] + [t.nombre for t in turnos]
                turno_sel = st.selectbox("Turno a asignar", turno_opciones)
            
            col1, col2 = st.columns(2)
            with col1:
                dia_inicio = st.number_input("Día inicio", min_value=1, max_value=dias_mes, value=1)
            with col2:
                dia_fin = st.number_input("Día fin", min_value=dia_inicio, max_value=dias_mes, value=dia_inicio)
            
            if st.button("🔄 Aplicar asignación masiva", use_container_width=True):
                # Mapear nombre de turno a ID
                turno_id = None
                if turno_sel != "Descanso":
                    turno = session.query(Turno).filter_by(nombre=turno_sel).first()
                    if turno:
                        turno_id = turno.id
                
                count = 0
                for dia in range(dia_inicio, dia_fin + 1):
                    fecha = date(año, mes_num, dia)
                    
                    # Buscar si ya existe asignación
                    existe = session.query(Asignacion).filter_by(
                        empleado_id=empleado.id,
                        fecha=fecha
                    ).first()
                    
                    if turno_id is None:  # Descanso - eliminar asignación
                        if existe:
                            session.delete(existe)
                            count += 1
                    else:  # Asignar turno
                        if existe:
                            existe.turno_id = turno_id
                        else:
                            nueva = Asignacion(
                                empleado_id=empleado.id,
                                fecha=fecha,
                                turno_id=turno_id
                            )
                            session.add(nueva)
                        count += 1
                
                session.commit()
                st.success(f"✅ {count} turnos actualizados correctamente")
                st.rerun()
    
    with tab3:  # CARGA MASIVA
        st.markdown("### Carga masiva desde Excel")
        st.markdown("""
        **Formato del archivo Excel:**
        - Columna A: Empleado
        - Columna B: Área  
        - Columnas C en adelante: Días del mes (D1, D2, D3...)
        
        Los valores deben ser los nombres de los turnos (ej: 151, 155, 70) o dejar vacío para descanso.
        """)
        
        archivo = st.file_uploader("Seleccionar archivo Excel", type=['xlsx', 'xls'])
        
        if archivo:
            try:
                df_carga = pd.read_excel(archivo)
                st.dataframe(df_carga.head())
                
                if st.button("📤 Procesar carga masiva"):
                    count = 0
                    for _, row in df_carga.iterrows():
                        nombre_emp = row['Empleado']
                        empleado = session.query(Empleado).filter_by(nombre=nombre_emp).first()
                        
                        if empleado:
                            for col in df_carga.columns:
                                if col.startswith('D') and col[1:].isdigit():
                                    dia = int(col[1:])
                                    if 1 <= dia <= dias_mes:
                                        turno_nombre = row[col]
                                        fecha = date(año, mes_num, dia)
                                        
                                        if pd.notna(turno_nombre) and str(turno_nombre).strip():
                                            turno = session.query(Turno).filter_by(nombre=str(turno_nombre)).first()
                                            if turno:
                                                existe = session.query(Asignacion).filter_by(
                                                    empleado_id=empleado.id,
                                                    fecha=fecha
                                                ).first()
                                                
                                                if existe:
                                                    existe.turno_id = turno.id
                                                else:
                                                    nueva = Asignacion(
                                                        empleado_id=empleado.id,
                                                        fecha=fecha,
                                                        turno_id=turno.id
                                                    )
                                                    session.add(nueva)
                                                count += 1
                    
                    session.commit()
                    st.success(f"✅ {count} turnos cargados/actualizados")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error al procesar archivo: {str(e)}")
    
    # Botón de exportar
    st.markdown("---")
    if st.button("📥 Exportar matriz actual a Excel"):
        # Preparar datos para exportar
        data_export = []
        for emp in empleados:
            fila = {
                "Empleado": emp.nombre,
                "Área": emp.area if emp.area else "N/A",
                "Cargo": emp.cargo if emp.cargo else "N/A",
            }
            for dia in range(1, dias_mes + 1):
                turno_id = matriz.get(emp.id, {}).get(dia)
                fila[f"D{dia}"] = turnos_dict.get(turno_id, "") if turno_id else ""
            data_export.append(fila)
        
        df_export = pd.DataFrame(data_export)
        output = pd.ExcelWriter('matriz_turnos.xlsx', engine='xlsxwriter')
        df_export.to_excel(output, index=False, sheet_name=f'Turnos_{mes}_{año}')
        output.close()
        
        with open('matriz_turnos.xlsx', 'rb') as f:
            st.download_button(
                "📥 Confirmar descarga",
                f,
                f"matriz_turnos_{mes}_{año}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ========== GENERAR MALLA ==========
elif op == "Generar malla":
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

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

# ========== CALENDARIO CON FULLCALENDAR (HTML/JS) ==========
elif op == "Calendario":
    st.subheader("📆 Calendario de turnos")
    
    # Si es empleado, solo ve sus turnos
    if user.rol == "empleado":
        st.info(f"👤 Mostrando solo tus turnos: **{user.nombre}**")
        
        # Filtros básicos para empleados
        col1, col2 = st.columns(2)
        with col1:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
        with col2:
            mes = st.selectbox("Mes", meses, index=1)
        
        # Calcular fechas del mes
        mes_num = meses.index(mes) + 1
        from calendar import monthrange
        dias_mes = monthrange(año, mes_num)[1]
        fecha_inicio_mes = date(año, mes_num, 1)
        fecha_fin_mes = date(año, mes_num, dias_mes)
        
        # Obtener SOLO las asignaciones del usuario actual
        asignaciones = session.query(Asignacion).filter(
            Asignacion.empleado_id == user.id,
            Asignacion.fecha.between(fecha_inicio_mes, fecha_fin_mes)
        ).all()
        
        # Si no hay asignaciones, mostrar mensaje
        if not asignaciones:
            st.info(f"ℹ️ No tienes turnos asignados en {mes} {año}")
            st.stop()
    
    else:  # ADMIN - ve todos los turnos
        # Obtener todas las áreas únicas
        empleados = session.query(Empleado).all()
        areas = list(set([e.area for e in empleados if e.area]))
        areas.sort()
        areas_opciones = ["Todas las áreas"] + areas
        
        # Filtros para admin
        col1, col2 = st.columns(2)
        with col1:
            if not areas:
                st.info("ℹ️ No hay áreas registradas")
                area_filtro = "Todas las áreas"
            else:
                area_filtro = st.selectbox("Filtrar por área", areas_opciones)
        
        with col2:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
            mes = st.selectbox("Mes", meses, index=1)
        
        # Calcular fechas del mes
        mes_num = meses.index(mes) + 1
        from calendar import monthrange
        dias_mes = monthrange(año, mes_num)[1]
        fecha_inicio_mes = date(año, mes_num, 1)
        fecha_fin_mes = date(año, mes_num, dias_mes)
        
        # Obtener TODAS las asignaciones del mes
        asignaciones = session.query(Asignacion).filter(
            Asignacion.fecha.between(fecha_inicio_mes, fecha_fin_mes)
        ).all()
    
    # Preparar eventos para el calendario
    eventos = []
    colores_area = {
        "Administración": "#FF6B6B",
        "Producción": "#4ECDC4",
        "Calidad": "#45B7D1",
        "Mantenimiento": "#96CEB4",
        "Logística": "#FFEAA7",
        "Ventas": "#D4A5A5",
        "RRHH": "#9B59B6",
        "Sistemas": "#3498DB",
        "PASILLOS": "#F39C12",
        "CAJAS": "#27AE60",
        "EQUIPOS MÉDICOS": "#E74C3C",
    }
    
    for a in asignaciones:
        if a.empleado and a.turno:
            # Para admin: aplicar filtro de área
            if user.rol == "admin":
                if area_filtro != "Todas las áreas" and a.empleado.area != area_filtro:
                    continue
            
            area = a.empleado.area if a.empleado.area else "Sin área"
            color = colores_area.get(area.upper(), "#3788d8")
            
            fecha_str = a.fecha.strftime("%Y-%m-%d")
            
            # Para empleado: mostrar solo "Mi turno" para privacidad
            if user.rol == "empleado":
                titulo = f"Mi turno: {a.turno.nombre}"
            else:
                titulo = f"{a.empleado.nombre} - {a.turno.nombre}"
            
            eventos.append({
                "title": titulo,
                "start": fecha_str,
                "color": color,
                "textColor": "white",
                "empleado": a.empleado.nombre,
                "area": area,
                "turno": a.turno.nombre,
                "hora_inicio": a.turno.inicio,
                "hora_fin": a.turno.fin
            })
    
    # Crear HTML con FullCalendar
    import json
    eventos_json = json.dumps(eventos)
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet' />
        <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>
        <style>
            body {{ margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; }}
            #calendar {{ max-width: 1100px; margin: 20px auto; padding: 0 10px; }}
            .fc-event {{ cursor: pointer; border-radius: 4px; padding: 2px 4px; font-size: 0.85em; }}
            .fc-event:hover {{ opacity: 0.9; }}
            .fc-day-today {{ background-color: rgba(52, 152, 219, 0.1) !important; }}
        </style>
    </head>
    <body>
        <div id='calendar'></div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var calendarEl = document.getElementById('calendar');
                var calendar = new FullCalendar.Calendar(calendarEl, {{
                    initialView: 'dayGridMonth',
                    headerToolbar: {{
                        left: 'today prev,next',
                        center: 'title',
                        right: 'dayGridMonth,timeGridWeek,timeGridDay'
                    }},
                    height: 600,
                    events: {eventos_json},
                    eventClick: function(info) {{
                        alert(
                            'Empleado: ' + info.event.extendedProps.empleado + '\\n' +
                            'Área: ' + info.event.extendedProps.area + '\\n' +
                            'Turno: ' + info.event.extendedProps.turno + '\\n' +
                            'Horario: ' + info.event.extendedProps.hora_inicio + ' - ' + info.event.extendedProps.hora_fin
                        );
                    }}
                }});
                calendar.render();
            }});
        </script>
    </body>
    </html>
    """
    
    # Mostrar el calendario HTML
    st.components.v1.html(html_code, height=650)
    
    # Estadísticas (adaptadas por rol)
    if eventos:
        st.markdown("---")
        if user.rol == "admin":
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total turnos", len(eventos))
            col2.metric("Empleados", len(set([e["empleado"] for e in eventos])))
            col3.metric("Áreas", len(set([e["area"] for e in eventos if e["area"]])))
            col4.metric("Turnos", len(set([e["turno"] for e in eventos])))
        else:
            col1, col2 = st.columns(2)
            col1.metric("Tus turnos", len(eventos))
            col2.metric("Días trabajados", len(set([e["start"] for e in eventos])))
    
    # Leyenda de colores
    if eventos:
        st.markdown("### 🎨 Leyenda de colores por área")
        
        areas_en_eventos = set()
        for e in eventos:
            if e["area"] and e["area"] != "Sin área":
                areas_en_eventos.add(e["area"])
        
        if areas_en_eventos:
            cols = st.columns(4)
            for i, area in enumerate(sorted(areas_en_eventos)):
                color = colores_area.get(area.upper(), "#3788d8")
                with cols[i % 4]:
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; margin: 5px 0;">
                            <div style="width: 20px; height: 20px; background-color: {color}; border-radius: 4px; margin-right: 8px;"></div>
                            <span style="font-size: 0.9em;">{area}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    
    # Botón para ver tabla
    with st.expander("📋 Ver vista de tabla detallada"):
        if eventos:
            data_tabla = []
            for e in eventos:
                data_tabla.append({
                    "Fecha": e["start"],
                    "Empleado": e["empleado"],
                    "Área": e["area"],
                    "Turno": e["turno"],
                    "Horario": f"{e['hora_inicio']} - {e['hora_fin']}"
                })
            
            if data_tabla:
                df_tabla = pd.DataFrame(data_tabla)
                st.dataframe(df_tabla, use_container_width=True)

# ========== MI PERFIL (SOLO EMPLEADOS) ==========
elif op == "Mi perfil":
    st.subheader("👤 Mi perfil")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Información personal")
        st.markdown(f"**Nombre:** {user.nombre}")
        st.markdown(f"**Usuario:** {user.usuario}")
        st.markdown(f"**Rol:** {user.rol}")
        st.markdown(f"**Área:** {user.area if user.area else 'No asignada'}")
        st.markdown(f"**Cargo:** {user.cargo if user.cargo else 'No asignado'}")
    
    with col2:
        st.markdown("### Estadísticas personales")
        
        # Total turnos
        total_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).count()
        st.metric("Total turnos asignados", total_turnos)
        
        # Turnos este mes
        from datetime import date
        hoy = date.today()
        turnos_mes = session.query(Asignacion).filter(
            Asignacion.empleado_id == user.id,
            Asignacion.fecha >= date(hoy.year, hoy.month, 1)
        ).count()
        st.metric("Turnos este mes", turnos_mes)

# ========== MIS TURNOS (SOLO EMPLEADOS) ==========
elif op == "Mis turnos":
    st.subheader("📊 Mis turnos")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes = st.selectbox("Mes", meses, index=1)
    with col2:
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
    
    # Calcular fechas
    mes_num = meses.index(mes) + 1
    from calendar import monthrange
    dias_mes = monthrange(año, mes_num)[1]
    fecha_inicio = date(año, mes_num, 1)
    fecha_fin = date(año, mes_num, dias_mes)
    
    # Obtener turnos del empleado
    mis_turnos = session.query(Asignacion).filter(
        Asignacion.empleado_id == user.id,
        Asignacion.fecha.between(fecha_inicio, fecha_fin)
    ).order_by(Asignacion.fecha).all()
    
    if mis_turnos:
        data = []
        for t in mis_turnos:
            data.append({
                "Fecha": t.fecha.strftime("%d/%m/%Y"),
                "Día": t.fecha.strftime("%A"),
                "Turno": t.turno.nombre if t.turno else "N/A",
                "Hora inicio": t.turno.inicio if t.turno else "N/A",
                "Hora fin": t.turno.fin if t.turno else "N/A"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Estadísticas
        col1, col2, col3 = st.columns(3)
        col1.metric("Total turnos", len(mis_turnos))
        
        # Turnos por tipo
        tipos_turno = {}
        for t in mis_turnos:
            if t.turno:
                tipos_turno[t.turno.nombre] = tipos_turno.get(t.turno.nombre, 0) + 1
        
        if tipos_turno:
            st.subheader("Distribución de turnos")
            st.bar_chart(pd.DataFrame(list(tipos_turno.items()), columns=["Turno", "Cantidad"]).set_index("Turno"))
    else:
        st.info(f"ℹ️ No tienes turnos asignados en {mes} {año}")

# ========== REPORTES ==========
elif op == "Reportes":
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

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
    if user.rol != "admin":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()

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