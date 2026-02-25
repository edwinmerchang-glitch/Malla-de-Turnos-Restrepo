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
            st.rerun()  # Cambiado de experimental_rerun a rerun
        else:
            st.error("Credenciales incorrectas")

if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state["user"]
session = Session()  # Crear sesión para el resto de la app

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
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Nuevo empleado")
        with st.form("nuevo_emp"):
            n = st.text_input("Nombre")
            r = st.selectbox("Rol", ["admin", "empleado"])
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Crear"):
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
            if st.form_submit_button("Crear"):
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
    st.subheader("🤖 Generación automática")

    inicio = st.date_input("Fecha inicio", date(2026, 2, 1))
    fin = st.date_input("Fecha fin", date(2026, 2, 28))

    if st.button("Generar malla"):
        fechas = [inicio + timedelta(days=i) for i in range((fin-inicio).days+1)]
        empleados = session.query(Empleado).all()
        turnos = session.query(Turno).all()
        
        if not empleados or not turnos:
            st.error("Debe haber empleados y turnos registrados")
        else:
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
            st.success(f"Malla generada para {len(asignaciones)} turnos + Backup creado")

# -------- CALENDARIO --------
elif op == "Calendario":
    st.subheader("📆 Calendario")
    
    mes = st.selectbox("Seleccionar mes", ["Febrero 2026"])
    
    asignaciones = session.query(Asignacion).all()
    
    data = []
    for a in asignaciones:
        data.append({
            "Fecha": a.fecha,
            "Empleado": a.empleado.nombre if a.empleado else "N/A",
            "Turno": a.turno.nombre if a.turno else "N/A"
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay asignaciones registradas")

# -------- REPORTES --------
elif op == "Reportes":
    st.subheader("📊 Reportes")
    
    asignaciones = session.query(Asignacion).all()
    data = []
    for a in asignaciones:
        data.append({
            "ID": a.id,
            "Empleado": a.empleado.nombre if a.empleado else "N/A",
            "Fecha": a.fecha,
            "Turno": a.turno.nombre if a.turno else "N/A"
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        # Convertir a Excel
        output = pd.ExcelWriter('temp.xlsx', engine='xlsxwriter')
        df.to_excel(output, index=False, sheet_name='Reporte')
        output.close()
        
        with open('temp.xlsx', 'rb') as f:
            st.download_button(
                "📥 Descargar Excel",
                f,
                "reporte_turnos.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# -------- BACKUP --------
elif op == "Backup":
    st.subheader("🛡 Seguridad")

    if st.button("Crear backup ahora"):
        backup_sqlite()
        st.success("Backup generado correctamente")
    
    import os
    if os.path.exists("data/backups"):
        backups = os.listdir("data/backups")
        if backups:
            st.markdown("### Backups disponibles")
            for b in sorted(backups, reverse=True):
                st.text(f"📁 {b}")