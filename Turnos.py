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

# -------- VERIFICAR/CREAR ADMIN POR DEFECTO --------
def ensure_admin_exists():
    """Asegura que exista un usuario administrador por defecto"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar estructura de la tabla
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )""")
        conn.commit()
        
        # Verificar si hay algún admin
        c.execute("SELECT * FROM users WHERE role='admin'")
        admin_exists = c.fetchone()
        
        if not admin_exists:
            # Verificar si el usuario admin ya existe
            c.execute("SELECT * FROM users WHERE username='admin'")
            user_admin = c.fetchone()
            
            if not user_admin:
                # Crear nuevo admin
                from auth import create_user
                success, message = create_user("admin", "Admin123*", "admin")
                if success:
                    print("✅ Usuario admin creado exitosamente")
                else:
                    print(f"❌ Error creando admin: {message}")
            else:
                # Actualizar usuario existente a admin
                c.execute("UPDATE users SET role='admin' WHERE username='admin'")
                conn.commit()
                print("✅ Usuario existente actualizado a admin")
        
        # Verificar que se creó correctamente
        c.execute("SELECT username, role FROM users WHERE username='admin'")
        admin_check = c.fetchone()
        if admin_check:
            print(f"✅ Admin verificado: {admin_check[0]} - {admin_check[1]}")
        else:
            print("❌ No se pudo verificar el admin")
            
    except Exception as e:
        print(f"❌ Error en ensure_admin_exists: {str(e)}")
    finally:
        if conn:
            conn.close()

# Ejecutar verificación de admin
ensure_admin_exists()

# Inicializar session state
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.mobile = False
    st.session_state.user = None
    st.session_state.role = None

# Ejecutar la creación del admin
ensure_admin_exists()


if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.mobile = False

# ---------- LOGIN ----------
if not st.session_state.login:
    st.title("🔐 Acceso al Sistema")
    
    # Crear dos columnas para mejor organización
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Iniciar sesión")
        user = st.text_input("Usuario", placeholder="Ingresa tu usuario")
        pwd = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
        
        if st.button("Ingresar", type="primary", use_container_width=True):
            if user and pwd:
                res = login_user(user, pwd)
                if res:
                    st.session_state.login = True
                    st.session_state.user = user
                    st.session_state.role = res[0]
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
            else:
                st.warning("⚠️ Ingresa usuario y contraseña")
    
    with col2:
        st.markdown("### 🔧 Ayuda")
        st.info(
            """
            **Credenciales por defecto:**
            - Usuario: `admin`
            - Contraseña: `Admin123*`
            
            *La contraseña es sensible a mayúsculas*
            """
        )
        
        if st.button("🔄 Resetear admin", use_container_width=True):
            try:
                conn = get_connection()
                c = conn.cursor()
                
                # Eliminar admin existente
                c.execute("DELETE FROM users WHERE username='admin'")
                
                # Crear nuevo admin
                from auth import create_user
                success, message = create_user("admin", "Admin123*", "admin")
                
                if success:
                    st.success("✅ Admin reseteado. Usa: admin / Admin123*")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {message}")
                
                conn.commit()
                conn.close()
            except Exception as e:
                st.error(f"Error: {str(e)}")

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
