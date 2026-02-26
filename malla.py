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

# -------- MENÚ CON BOTONES SEGÚN EL ROL --------
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
    if user.rol == "empleado":
        st.session_state.pagina_actual = "Calendario"
    elif user.rol == "supervisor":
        st.session_state.pagina_actual = "Mi area"
    else:  # admin
        st.session_state.pagina_actual = "Empleados"

def cambiar_pagina(pagina):
    st.session_state.pagina_actual = pagina

# -------- MENÚ PARA EMPLEADOS --------
if user.rol == "empleado":
    st.sidebar.markdown("### 📋 Mi espacio")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("📅 Calendario", use_container_width=True):
            cambiar_pagina("Calendario")
        if st.button("👤 Mi perfil", use_container_width=True):
            cambiar_pagina("Mi perfil")
    
    with col2:
        if st.button("📊 Mis turnos", use_container_width=True):
            cambiar_pagina("Mis turnos")

# -------- MENÚ PARA SUPERVISORES --------
elif user.rol == "supervisor":
    st.sidebar.markdown("### 📋 Mi área")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("👥 Mi equipo", use_container_width=True):
            cambiar_pagina("Mi equipo")
        if st.button("📊 Matriz área", use_container_width=True):
            cambiar_pagina("Matriz area")
        if st.button("👤 Mi perfil", use_container_width=True):
            cambiar_pagina("Mi perfil")
    
    with col2:
        if st.button("✏️ Asignar turnos", use_container_width=True):
            cambiar_pagina("Asignar area")
        if st.button("📈 Reportes área", use_container_width=True):
            cambiar_pagina("Reportes area")
        if st.button("📅 Mi calendario", use_container_width=True):
            cambiar_pagina("Calendario")

# -------- MENÚ PARA ADMINISTRADORES --------
elif user.rol == "admin":
    st.sidebar.markdown("### ⚙️ Administración")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("👥 Empleados", use_container_width=True):
            cambiar_pagina("Empleados")
        if st.button("⏰ Turnos", use_container_width=True):
            cambiar_pagina("Turnos")
        if st.button("📊 Matriz general", use_container_width=True):
            cambiar_pagina("Matriz turnos")
        if st.button("👤 Mi perfil", use_container_width=True):
            cambiar_pagina("Mi perfil")
    
    with col2:
        if st.button("✏️ Asignar manual", use_container_width=True):
            cambiar_pagina("Asignacion manual")
        if st.button("🤖 Generar malla", use_container_width=True):
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

# ========== PÁGINAS PARA EMPLEADOS ==========

# ---------- CALENDARIO ----------
if op == "Calendario":
    if user.rol not in ["empleado", "supervisor"]:
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()
    
    st.subheader("📆 Mi calendario de turnos")
    st.info(f"👤 Mostrando turnos de: **{user.nombre}**")
    
    col1, col2 = st.columns(2)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026, key="cal_ano")
    with col2:
        mes = st.selectbox("Mes", meses, index=1, key="cal_mes")
    
    mes_num = meses.index(mes) + 1
    from calendar import monthrange
    dias_mes = monthrange(año, mes_num)[1]
    fecha_inicio_mes = date(año, mes_num, 1)
    fecha_fin_mes = date(año, mes_num, dias_mes)
    
    asignaciones = session.query(Asignacion).filter(
        Asignacion.empleado_id == user.id,
        Asignacion.fecha.between(fecha_inicio_mes, fecha_fin_mes)
    ).all()
    
    if not asignaciones:
        st.info(f"ℹ️ No tienes turnos asignados en {mes} {año}")
        st.stop()
    
    eventos = []
    for a in asignaciones:
        if a.turno:
            fecha_str = a.fecha.strftime("%Y-%m-%d")
            eventos.append({
                "title": a.turno.nombre,
                "start": fecha_str,
                "color": "#4F46E5",
                "textColor": "white",
            })
    
    import json
    eventos_json = json.dumps(eventos)
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet' />
        <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>
        <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/locales-all.min.js'></script>
        <style>
            #calendar {{ max-width: 1100px; margin: 20px auto; }}
        </style>
    </head>
    <body>
        <div id='calendar'></div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {{
                    locale: 'es',
                    initialView: 'dayGridMonth',
                    headerToolbar: {{
                        left: 'today prev,next',
                        center: 'title',
                        right: 'dayGridMonth,timeGridWeek,timeGridDay'
                    }},
                    buttonText: {{
                        today: 'Hoy',
                        month: 'Mes',
                        week: 'Semana',
                        day: 'Día'
                    }},
                    height: 600,
                    events: {eventos_json}
                }});
                calendar.render();
            }});
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=650)
    
    st.metric("Total turnos en el mes", len(eventos))

# ---------- MI PERFIL ----------
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
        st.markdown("### Estadísticas")
        total_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).count()
        st.metric("Total turnos asignados", total_turnos)

# ---------- MIS TURNOS ----------
elif op == "Mis turnos":
    st.subheader("📊 Mis turnos")
    
    col1, col2 = st.columns(2)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes = st.selectbox("Mes", meses, index=1)
    with col2:
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
    
    mes_num = meses.index(mes) + 1
    from calendar import monthrange
    dias_mes = monthrange(año, mes_num)[1]
    fecha_inicio = date(año, mes_num, 1)
    fecha_fin = date(año, mes_num, dias_mes)
    
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
                "Hora": f"{t.turno.inicio} - {t.turno.fin}" if t.turno else "N/A"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        st.metric("Total turnos", len(mis_turnos))
    else:
        st.info(f"ℹ️ No tienes turnos en {mes} {año}")

# ========== PÁGINAS PARA SUPERVISORES ==========

# ---------- MI EQUIPO ----------
elif op == "Mi equipo":
    if user.rol != "supervisor":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()
    
    st.subheader(f"👥 Mi equipo - {user.area}")
    
    empleados_area = session.query(Empleado).filter_by(area=user.area).all()
    
    if empleados_area:
        data = []
        for e in empleados_area:
            data.append({
                "Nombre": e.nombre,
                "Cargo": e.cargo if e.cargo else "No asignado",
                "Usuario": e.usuario,
                "Rol": e.rol
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        st.metric("Total en mi equipo", len(empleados_area))
    else:
        st.info(f"No hay empleados en tu área")

# ---------- MATRIZ ÁREA ----------
elif op == "Matriz area":
    if user.rol != "supervisor":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()
    
    st.subheader(f"📊 Matriz de turnos - {user.area}")
    
    col1, col2 = st.columns(2)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes = st.selectbox("Mes", meses, index=1)
    with col2:
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
    
    mes_num = meses.index(mes) + 1
    from calendar import monthrange
    dias_mes = monthrange(año, mes_num)[1]
    
    empleados = session.query(Empleado).filter_by(area=user.area).all()
    
    if not empleados:
        st.warning("No hay empleados en tu área")
        st.stop()
    
    turnos = session.query(Turno).all()
    turnos_dict = {t.id: t.nombre for t in turnos}
    
    fecha_inicio = date(año, mes_num, 1)
    fecha_fin = date(año, mes_num, dias_mes)
    
    asignaciones = session.query(Asignacion).filter(
        Asignacion.fecha.between(fecha_inicio, fecha_fin)
    ).all()
    
    matriz = {}
    for a in asignaciones:
        if a.empleado_id not in matriz:
            matriz[a.empleado_id] = {}
        matriz[a.empleado_id][a.fecha.day] = a.turno_id
    
    data = []
    for emp in empleados:
        fila = {"Empleado": emp.nombre}
        for dia in range(1, dias_mes + 1):
            turno_id = matriz.get(emp.id, {}).get(dia)
            fila[str(dia)] = turnos_dict.get(turno_id, "—") if turno_id else "—"
        data.append(fila)
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=500)
        
        total = sum(1 for emp in matriz for dia in matriz[emp])
        st.metric("Total turnos en el área", total)

# ---------- ASIGNAR TURNOS ÁREA ----------
elif op == "Asignar area":
    if user.rol != "supervisor":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()
    
    st.subheader(f"✏️ Asignar turnos - {user.area}")
    
    empleados = session.query(Empleado).filter_by(area=user.area).all()
    
    if not empleados:
        st.warning("No hay empleados en tu área")
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        empleado_sel = st.selectbox("Empleado", [e.nombre for e in empleados])
        empleado = next(e for e in empleados if e.nombre == empleado_sel)
    
    with col2:
        turnos = session.query(Turno).all()
        turno_sel = st.selectbox("Turno", [t.nombre for t in turnos])
        turno = next(t for t in turnos if t.nombre == turno_sel)
    
    fecha = st.date_input("Fecha", date.today())
    
    if st.button("✅ Asignar turno", use_container_width=True):
        existe = session.query(Asignacion).filter_by(
            empleado_id=empleado.id,
            fecha=fecha
        ).first()
        
        if existe:
            existe.turno_id = turno.id
            msg = "actualizado"
        else:
            nueva = Asignacion(
                empleado_id=empleado.id,
                fecha=fecha,
                turno_id=turno.id
            )
            session.add(nueva)
            msg = "asignado"
        
        session.commit()
        st.success(f"✅ Turno {msg} correctamente")
        st.rerun()

# ---------- REPORTES ÁREA ----------
elif op == "Reportes area":
    if user.rol != "supervisor":
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()
    
    st.subheader(f"📈 Reportes - {user.area}")
    
    empleados_ids = [e.id for e in session.query(Empleado).filter_by(area=user.area).all()]
    
    if not empleados_ids:
        st.info("No hay empleados en tu área")
        st.stop()
    
    asignaciones = session.query(Asignacion).filter(
        Asignacion.empleado_id.in_(empleados_ids)
    ).all()
    
    if not asignaciones:
        st.info("No hay asignaciones en tu área")
        st.stop()
    
    data = []
    for a in asignaciones:
        data.append({
            "Empleado": a.empleado.nombre,
            "Turno": a.turno.nombre if a.turno else "N/A",
            "Fecha": a.fecha
        })
    
    df = pd.DataFrame(data)
    
    st.subheader("Turnos por empleado")
    reporte = df.groupby("Empleado").size().reset_index(name="Total")
    reporte = reporte.sort_values("Total", ascending=False)
    st.dataframe(reporte, use_container_width=True)
    st.bar_chart(reporte.set_index("Empleado"))

# ========== PÁGINAS PARA ADMINISTRADORES (resumidas) ==========

# ---------- EMPLEADOS (solo admin) ----------
elif op == "Empleados":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("👥 Gestión de Empleados")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista", "➕ Nuevo", "✏️ Editar"])
    
    with tab1:
        empleados = session.query(Empleado).all()
        data = []
        for e in empleados:
            data.append({
                "ID": e.id,
                "Nombre": e.nombre,
                "Área": e.area or "N/A",
                "Cargo": e.cargo or "N/A",
                "Usuario": e.usuario,
                "Rol": e.rol
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    
    with tab2:
        with st.form("nuevo_emp"):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("Nombre *")
                u = st.text_input("Usuario *")
                r = st.selectbox("Rol *", ["empleado", "supervisor", "admin"])
            with col2:
                area = st.text_input("Área")
                cargo = st.text_input("Cargo")
                p = st.text_input("Contraseña *", type="password")
            
            if st.form_submit_button("✅ Crear"):
                if n and u and p:
                    session.add(Empleado(
                        nombre=n, rol=r, usuario=u, password=p,
                        area=area or None, cargo=cargo or None
                    ))
                    session.commit()
                    st.success("✅ Creado")
                    st.rerun()
    
    with tab3:
        empleados = session.query(Empleado).all()
        if empleados:
            opciones = {f"{e.nombre} ({e.usuario})": e.id for e in empleados}
            seleccion = st.selectbox("Seleccionar", list(opciones.keys()))
            emp = session.get(Empleado, opciones[seleccion])
            
            if emp:
                with st.form("editar"):
                    nombre = st.text_input("Nombre", emp.nombre)
                    area = st.text_input("Área", emp.area or "")
                    cargo = st.text_input("Cargo", emp.cargo or "")
                    rol = st.selectbox("Rol", ["empleado", "supervisor", "admin"], 
                                     index=["empleado", "supervisor", "admin"].index(emp.rol))
                    
                    if st.form_submit_button("💾 Guardar"):
                        emp.nombre = nombre
                        emp.area = area or None
                        emp.cargo = cargo or None
                        emp.rol = rol
                        session.commit()
                        st.success("✅ Guardado")
                        st.rerun()

# ---------- TURNOS (solo admin) ----------
elif op == "Turnos":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("⏰ Turnos")
    
    tab1, tab2 = st.tabs(["📋 Lista", "➕ Nuevo"])
    
    with tab1:
        turnos = session.query(Turno).all()
        data = [{"ID": t.id, "Nombre": t.nombre, "Inicio": t.inicio, "Fin": t.fin} for t in turnos]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    
    with tab2:
        with st.form("nuevo_turno"):
            n = st.text_input("Nombre")
            hi = st.text_input("Hora inicio")
            hf = st.text_input("Hora fin")
            if st.form_submit_button("Crear"):
                session.add(Turno(nombre=n, inicio=hi, fin=hf))
                session.commit()
                st.success("✅ Creado")
                st.rerun()

# ---------- MATRIZ TURNOS (admin) ----------
elif op == "Matriz turnos":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("📊 Matriz general")
    # (código de matriz para admin - lo tienes en tu archivo)

# ---------- ASIGNACION MANUAL (admin) ----------
elif op == "Asignacion manual":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("✏️ Asignación manual")
    # (código de asignación manual - lo tienes en tu archivo)

# ---------- GENERAR MALLA (admin) ----------
elif op == "Generar malla":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("🤖 Generar malla")
    # (código de generar malla - lo tienes en tu archivo)

# ---------- REPORTES (admin) ----------
elif op == "Reportes":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("📊 Reportes")
    # (código de reportes - lo tienes en tu archivo)

# ---------- BACKUP (admin) ----------
elif op == "Backup":
    if user.rol != "admin":
        st.error("❌ No tienes permiso")
        st.stop()
    
    st.subheader("🛡 Backup")
    # (código de backup - lo tienes en tu archivo)