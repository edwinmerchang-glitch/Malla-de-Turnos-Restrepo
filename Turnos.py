import streamlit as st
import pandas as pd
import qrcode
import io

from database import create_tables, get_connection
from auth import create_user, login_user
from calendar_view import mostrar_calendario
from reportes import generar_reporte
from notificaciones import enviar_correo

st.set_page_config(
    page_title="Gestión Empresarial de Turnos",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#0E1117">
""", unsafe_allow_html=True)

create_tables()

if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.mobile = False

# ---------- LOGIN ----------
if not st.session_state.login:

    st.title("🔐 Acceso al Sistema")

    user = st.text_input("Usuario")
    pwd = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        res = login_user(user, pwd)
        if res:
            st.session_state.login = True
            st.session_state.user = user
            st.session_state.role = res[0]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

# ---------- PANEL ----------
else:
    conn = get_connection()

    if st.session_state.role == "empleado":

        df = pd.read_sql(f"""
            SELECT fecha, turno FROM turnos
            WHERE empleado='{st.session_state.user}'
            ORDER BY fecha
        """, conn)

        if st.button("📱 Vista móvil"):
            st.session_state.mobile = True

        if st.session_state.mobile:
            st.title("📅 Mis Turnos")
            for _, row in df.iterrows():
                st.markdown(f"""
                ### 📆 {row['fecha']}
                **Turno:** {row['turno']}
                ---
                """)
        else:
            st.dataframe(df, use_container_width=True)

    # -------- ADMIN ----------
    else:
        menu = st.sidebar.radio("Menú", ["Usuarios","Empleados","Turnos","Reportes"])

        if menu == "Usuarios":
            st.header("👤 Crear Usuario")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            r = st.selectbox("Rol", ["empleado","admin"])
            if st.button("Crear"):
                create_user(u,p,r)
                st.success("Usuario creado")

        elif menu == "Empleados":
            st.header("🧑‍🤝‍🧑 Registrar Empleado")
            n = st.text_input("Nombre")
            c = st.text_input("Cargo")
            u = st.text_input("Usuario")
            e = st.text_input("Correo")
            if st.button("Registrar"):
                conn.execute("INSERT INTO empleados VALUES (NULL,?,?,?,?)",
                             (n,c,u,e))
                conn.commit()
                st.success("Empleado registrado")

        elif menu == "Turnos":
            st.header("📅 Programación")
            empleados = pd.read_sql("SELECT usuario,correo FROM empleados", conn)

            emp = st.selectbox("Empleado", empleados["usuario"])
            fecha = st.date_input("Fecha")
            turno = st.selectbox("Turno", ["Mañana","Tarde","Noche","Descanso"])

            if st.button("Asignar"):
                conn.execute("INSERT INTO turnos VALUES (NULL,?,?,?)",
                             (emp,str(fecha),turno))
                conn.commit()

                correo = empleados[empleados["usuario"]==emp]["correo"].values[0]

                enviar_correo(
                    correo,
                    "Nuevo turno asignado",
                    f"Fecha: {fecha}\nTurno: {turno}"
                )

                st.success("Turno asignado y notificado")

            df_all = pd.read_sql("SELECT * FROM turnos ORDER BY fecha", conn)

            st.subheader("📆 Calendario General")
            mostrar_calendario(df_all)

            st.subheader("📥 Exportar Excel")
            st.download_button(
                "Descargar",
                df_all.to_excel(index=False),
                file_name="turnos.xlsx"
            )

        elif menu == "Reportes":
            df_all = pd.read_sql("SELECT * FROM turnos", conn)
            rep = generar_reporte(df_all)
            st.subheader("📊 Reporte semanal")
            st.dataframe(rep, use_container_width=True)

    st.sidebar.divider()

    qr = qrcode.make("https://TU_APP.streamlit.app")
    st.sidebar.image(qr, caption="📱 Escanear para instalar app")

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()
