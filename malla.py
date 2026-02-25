import streamlit as st
import pandas as pd
from db import init_db, get_conn
from auth import proteger_app
from utils import get_febrero_2026, CODIGOS_TURNOS, dia_semana

st.set_page_config("Gestión Profesional de Turnos", layout="wide")

proteger_app()
init_db()

conn = get_conn()
rol = st.session_state["rol"]

st.title("📆 Sistema Profesional de Turnos")

# ============================
# MENÚ SEGÚN ROL
# ============================

if rol == "admin":
    menu = st.sidebar.radio("Menú", ["Empleados", "Programar", "Calendario", "Reportes"])
else:
    menu = st.sidebar.radio("Menú", ["Mi Turno"])

# ============================
# EMPLEADOS
# ============================

if menu == "Empleados":
    st.header("👥 Empleados")

    with st.form("form_emp"):
        c1,c2,c3 = st.columns(3)
        nombre = c1.text_input("Nombre")
        cargo = c2.text_input("Cargo")
        doc = c3.text_input("Documento")
        area = c1.text_input("Área")
        he = c2.time_input("Entrada")
        hs = c3.time_input("Salida")

        if st.form_submit_button("Guardar"):
            conn.execute("""
                INSERT OR IGNORE INTO empleados
                (nombre,cargo,documento,area,horario_entrada,horario_salida)
                VALUES (?,?,?,?,?,?)
            """,(nombre,cargo,doc,area,str(he),str(hs)))
            conn.commit()
            st.success("Empleado guardado")

    df = pd.read_sql("SELECT * FROM empleados", conn)
    st.dataframe(df, use_container_width=True)

# ============================
# PROGRAMAR
# ============================

elif menu == "Programar":
    st.header("🗓️ Programar Turnos")

    emp = pd.read_sql("SELECT id,nombre FROM empleados", conn)
    nombre = st.selectbox("Empleado", emp['nombre'])
    emp_id = emp[emp['nombre']==nombre]['id'].values[0]

    fecha = st.date_input("Fecha")
    turno = st.selectbox("Turno", list(CODIGOS_TURNOS.keys()))

    if st.button("Guardar"):
        conn.execute("""
            INSERT OR REPLACE INTO turnos
            (empleado_id,fecha,codigo_turno)
            VALUES (?,?,?)
        """,(emp_id,fecha,turno))
        conn.commit()
        st.success("Turno asignado")

# ============================
# CALENDARIO
# ============================

elif menu == "Calendario":
    st.header("📅 Calendario Febrero 2026")

    emp = pd.read_sql("SELECT id,nombre FROM empleados", conn)
    dias = get_febrero_2026()

    tabla = []

    for _, e in emp.iterrows():
        fila = [e['nombre']]
        for d in dias:
            r = conn.execute("""
                SELECT codigo_turno FROM turnos
                WHERE empleado_id=? AND fecha=?
            """,(e['id'],d.date())).fetchone()

            fila.append(r[0] if r else "")
        tabla.append(fila)

    columnas = ["Empleado"] + [f"{d.day}\n{dia_semana(d)}" for d in dias]
    df = pd.DataFrame(tabla, columns=columnas)

    st.dataframe(df, height=650, use_container_width=True)

# ============================
# REPORTES
# ============================

elif menu == "Reportes":
    st.header("📊 Reportes")

    df = pd.read_sql("""
        SELECT e.nombre, t.fecha, t.codigo_turno
        FROM turnos t
        JOIN empleados e ON e.id = t.empleado_id
    """, conn)

    st.dataframe(df, use_container_width=True)

    st.download_button("📥 Exportar Excel", df.to_excel(index=False), "turnos.xlsx")

# ============================
# EMPLEADO
# ============================

elif menu == "Mi Turno":
    st.header("📱 Mi Turno")

    nombre = st.text_input("Digite su nombre")

    if nombre:
        df = pd.read_sql("""
            SELECT t.fecha, t.codigo_turno
            FROM turnos t
            JOIN empleados e ON e.id = t.empleado_id
            WHERE e.nombre LIKE ?
        """, conn, params=(f"%{nombre}%",))

        st.dataframe(df, use_container_width=True)