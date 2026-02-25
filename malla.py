import streamlit as st
import pandas as pd
from datetime import date, timedelta
from db import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite

st.set_page_config("Malla de Turnos", layout="wide")

session = Session()

# -------- LOGIN --------
def login():
    st.title("🔐 Ingreso al sistema")
    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        emp = session.query(Empleado).filter_by(usuario=user, password=pwd).first()
        if emp:
            st.session_state["user"] = emp
            st.experimental_rerun()
        else:
            st.error("Credenciales incorrectas")

if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state["user"]

# -------- MENÚ --------
st.sidebar.title("📅 Malla de Turnos")
op = st.sidebar.radio("Menú", [
    "Calendario",
    "Empleados",
    "Turnos",
    "Generar malla",
    "Reportes",
    "Backup"
])

# -------- EMPLEADOS --------
if op == "Empleados":
    st.subheader("👥 Empleados")

    with st.form("nuevo_emp"):
        n = st.text_input("Nombre")
        r = st.text_input("Rol")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña")
        if st.form_submit_button("Crear"):
            session.add(Empleado(nombre=n, rol=r, usuario=u, password=p))
            session.commit()
            st.success("Empleado creado")

    df = pd.read_sql(session.query(Empleado).statement, session.bind)
    st.dataframe(df, use_container_width=True)

# -------- TURNOS --------
elif op == "Turnos":
    st.subheader("⏰ Turnos")

    with st.form("nuevo_turno"):
        n = st.text_input("Nombre")
        hi = st.text_input("Hora inicio")
        hf = st.text_input("Hora fin")
        if st.form_submit_button("Crear"):
            session.add(Turno(nombre=n, hora_inicio=hi, hora_fin=hf))
            session.commit()
            st.success("Turno creado")

    df = pd.read_sql(session.query(Turno).statement, session.bind)
    st.dataframe(df, use_container_width=True)

# -------- GENERADOR --------
elif op == "Generar malla":
    st.subheader("🤖 Generación automática")

    inicio = st.date_input("Fecha inicio")
    fin = st.date_input("Fecha fin")

    if st.button("Generar"):
        fechas = [inicio + timedelta(days=i) for i in range((fin-inicio).days+1)]
        empleados = session.query(Empleado).all()
        turnos = session.query(Turno).all()

        asignaciones = generar_malla_inteligente(fechas, empleados, turnos)

        for f, e, t in asignaciones:
            session.add(Asignacion(fecha=f, empleado_id=e, turno_id=t))
        session.commit()

        backup_sqlite()
        st.success("Malla generada + Backup creado")

# -------- CALENDARIO --------
elif op == "Calendario":
    st.subheader("📆 Calendario")

    q = session.query(Asignacion).all()

    data = []
    for a in q:
        data.append({
            "Fecha": a.fecha,
            "Empleado": a.empleado.nombre,
            "Turno": a.turno.nombre
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

# -------- REPORTES --------
elif op == "Reportes":
    st.subheader("📊 Reportes")

    df = pd.read_sql(session.query(Asignacion).statement, session.bind)
    st.dataframe(df, use_container_width=True)

    st.download_button("📥 Descargar Excel",
        df.to_excel(index=False),
        "reporte_turnos.xlsx"
    )

# -------- BACKUP --------
elif op == "Backup":
    st.subheader("🛡 Seguridad")

    if st.button("Crear backup ahora"):
        backup_sqlite()
        st.success("Backup generado")