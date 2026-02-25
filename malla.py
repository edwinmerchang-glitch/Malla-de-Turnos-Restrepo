import streamlit as st
from database import Session, Empleado, Turno, Asignacion
from auth import login
from scheduler import generar_malla_inteligente
from reports import resumen_mensual, exportar_excel, exportar_pdf
from ui import header
from streamlit_calendar import calendar
from datetime import date

st.set_page_config("Malla Turnos Corporativa", layout="wide")

if not login():
    st.stop()

session = Session()
rol = st.session_state.rol

header("📆 Sistema Corporativo de Malla de Turnos")

menu = st.sidebar.radio("Menú", ["📅 Calendario", "👥 Empleados", "⏰ Turnos",
                                 "🤖 Auto-Asignación", "📊 Reportes"]
                        if rol == "admin" else ["📅 Mis Turnos"])

# ---------------- EMPLEADOS ----------------
if menu == "👥 Empleados":
    header("Gestión de Empleados")

    with st.form("nuevo_emp"):
        nombre = st.text_input("Nombre")
        usuario = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        rol_emp = st.selectbox("Rol", ["empleado", "admin"])
        if st.form_submit_button("Crear"):
            session.add(Empleado(nombre=nombre, usuario=usuario, password=pwd, rol=rol_emp))
            session.commit()
            st.success("Empleado creado")

    data = session.query(Empleado).all()
    st.dataframe([(e.id, e.nombre, e.usuario, e.rol) for e in data],
                 columns=["ID", "Nombre", "Usuario", "Rol"], use_container_width=True)

# ---------------- TURNOS ----------------
if menu == "⏰ Turnos":
    header("Gestión de Turnos")

    with st.form("nuevo_turno"):
        nombre = st.text_input("Nombre")
        inicio = st.text_input("Inicio (07:00)")
        fin = st.text_input("Fin (15:00)")
        if st.form_submit_button("Crear"):
            session.add(Turno(nombre=nombre, inicio=inicio, fin=fin))
            session.commit()
            st.success("Turno creado")

    data = session.query(Turno).all()
    st.dataframe([(t.nombre, t.inicio, t.fin) for t in data],
                 columns=["Turno", "Inicio", "Fin"], use_container_width=True)

# ---------------- AUTO-ASIGNACIÓN ----------------
if menu == "🤖 Auto-Asignación":
    header("Asignación Inteligente")

    empleados = session.query(Empleado).filter_by(rol="empleado").all()
    turnos = session.query(Turno).all()

    fecha = st.date_input("Fecha inicio")
    dias = st.slider("Días", 7, 90, 30)

    if st.button("Generar Malla"):
        datos = generar_malla_inteligente(empleados, turnos, fecha, dias)
        for emp_id, f, turno in datos:
            session.add(Asignacion(empleado_id=emp_id, fecha=f, turno=turno))
        session.commit()
        st.success("Malla generada automáticamente")

# ---------------- CALENDARIO ----------------
if menu == "📅 Calendario":
    header("Calendario Visual")

    asignaciones = session.query(Asignacion).all()
    empleados = session.query(Empleado).all()
    mapa = {e.id: e.nombre for e in empleados}

    eventos = [{
        "title": f"{mapa[a.empleado_id]} - {a.turno}",
        "start": str(a.fecha),
        "allDay": True
    } for a in asignaciones]

    calendar(events=eventos, options={
        "initialView": "dayGridMonth",
        "locale": "es",
        "height": 720
    })

# ---------------- MODO EMPLEADO ----------------
if menu == "📅 Mis Turnos":
    header("Mis Turnos")

    emp = session.query(Empleado).filter_by(usuario=st.session_state.user).first()
    asignaciones = session.query(Asignacion).filter_by(empleado_id=emp.id).all()

    eventos = [{
        "title": a.turno,
        "start": str(a.fecha),
        "allDay": True
    } for a in asignaciones]

    calendar(events=eventos, options={
        "initialView": "dayGridMonth",
        "locale": "es",
        "height": 720
    })

# ---------------- REPORTES ----------------
if menu == "📊 Reportes":
    header("Reportes Gerenciales")

    df = resumen_mensual(session)
    st.dataframe(df, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 Descargar Excel",
                           exportar_excel(df),
                           "reporte_turnos.xlsx",
                           use_container_width=True)
    with c2:
        st.download_button("📄 Descargar PDF",
                           exportar_pdf(df),
                           "reporte_turnos.pdf",
                           use_container_width=True)