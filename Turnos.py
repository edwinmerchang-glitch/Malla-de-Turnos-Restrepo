import streamlit as st
import pandas as pd
import qrcode
import io

from database import create_tables, get_connection
from auth import create_user, login_user, user_exists
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

# Crear tablas si no existen
create_tables()

# -------- VERIFICAR/CREAR ADMIN POR DEFECTO --------
def ensure_admin_exists():
    """Asegura que exista un usuario administrador por defecto"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Verificar si hay algún admin
        c.execute("SELECT * FROM users WHERE role='admin'")
        admin_exists = c.fetchone()
        
        if not admin_exists:
            # Verificar si el usuario admin ya existe
            c.execute("SELECT * FROM users WHERE username='admin'")
            user_admin = c.fetchone()
            
            if not user_admin:
                # Crear nuevo admin
                success, message = create_user("admin", "Admin123*", "admin")
                if success:
                    st.sidebar.success("✅ Usuario admin creado")
                else:
                    st.sidebar.error(f"❌ Error creando admin: {message}")
            else:
                # Actualizar usuario existente a admin
                c.execute("UPDATE users SET role='admin' WHERE username='admin'")
                conn.commit()
                st.sidebar.success("✅ Usuario existente actualizado a admin")
        
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

# Ejecutar verificación de admin (solo una vez)
ensure_admin_exists()

# Inicializar session state (solo una vez)
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.mobile = False
    st.session_state.user = None
    st.session_state.role = None

# ---------- LOGIN ----------
if not st.session_state.login:
    st.title("🔐 Acceso al Sistema")
    
    # Crear dos columnas para mejor organización
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Iniciar sesión")
        user = st.text_input("Usuario", placeholder="Ingresa tu usuario", key="login_user")
        pwd = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña", key="login_pwd")
        
        if st.button("Ingresar", type="primary", use_container_width=True):
            if user and pwd:
                with st.spinner("Verificando credenciales..."):
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
                conn.commit()
                
                # Crear nuevo admin
                success, message = create_user("admin", "Admin123*", "admin")
                conn.close()
                
                if success:
                    st.success("✅ Admin reseteado. Usa: admin / Admin123*")
                    st.rerun()
                else:
                    st.error(f"❌ Error: {message}")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- PANEL PRINCIPAL ----------
else:
    conn = get_connection()

    # -------- VISTA EMPLEADO ----------
    if st.session_state.role == "empleado":
        st.title(f"👋 Bienvenido {st.session_state.user}")
        
        # Obtener turnos del empleado
        df = pd.read_sql(f"""
            SELECT fecha, turno FROM turnos
            WHERE empleado='{st.session_state.user}'
            ORDER BY fecha
        """, conn)

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("📱 Vista móvil"):
                st.session_state.mobile = not st.session_state.mobile
                st.rerun()

        if st.session_state.mobile:
            st.title("📅 Mis Turnos")
            if len(df) > 0:
                for _, row in df.iterrows():
                    with st.container():
                        st.markdown(f"""
                        ### 📆 {row['fecha']}
                        **Turno:** {row['turno']}
                        ---
                        """)
            else:
                st.info("No tienes turnos asignados")
        else:
            st.subheader("📅 Mis Turnos")
            if len(df) > 0:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No tienes turnos asignados")

    # -------- VISTA ADMIN ----------
    else:
        st.sidebar.title(f"👑 Admin: {st.session_state.user}")
        menu = st.sidebar.radio("Menú", ["Usuarios", "Empleados", "Turnos", "Reportes"])

        if menu == "Usuarios":
            st.header("👤 Crear Usuario")
            
            with st.form("crear_usuario"):
                u = st.text_input("Usuario", key="new_user")
                p = st.text_input("Contraseña", type="password", key="new_pass")
                r = st.selectbox("Rol", ["empleado", "admin"], key="new_role")
                
                if st.form_submit_button("Crear Usuario"):
                    if u and p:
                        success, message = create_user(u, p, r)
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ Complete todos los campos")

        elif menu == "Empleados":
            st.header("🧑‍🤝‍🧑 Registrar Empleado")
            
            with st.form("registrar_empleado"):
                n = st.text_input("Nombre completo")
                cargo = st.text_input("Cargo")
                u = st.text_input("Usuario (debe coincidir con usuario del sistema)")
                e = st.text_input("Correo electrónico")
                
                if st.form_submit_button("Registrar Empleado"):
                    if n and cargo and u and e:
                        try:
                            conn.execute(
                                "INSERT INTO empleados (nombre, cargo, usuario, correo) VALUES (?,?,?,?)",
                                (n, cargo, u, e)
                            )
                            conn.commit()
                            st.success("✅ Empleado registrado exitosamente")
                        except Exception as ex:
                            st.error(f"❌ Error: {str(ex)}")
                    else:
                        st.warning("⚠️ Complete todos los campos")
            
            # Mostrar empleados registrados
            st.subheader("📋 Empleados Registrados")
            empleados_df = pd.read_sql("SELECT * FROM empleados", conn)
            if len(empleados_df) > 0:
                st.dataframe(empleados_df, use_container_width=True)
            else:
                st.info("No hay empleados registrados")

        elif menu == "Turnos":
            st.header("📅 Programación de Turnos")
            
            # Obtener empleados
            empleados = pd.read_sql("SELECT usuario, correo FROM empleados", conn)
            
            if len(empleados) > 0:
                with st.form("asignar_turno"):
                    emp = st.selectbox("Seleccionar Empleado", empleados["usuario"].tolist())
                    fecha = st.date_input("Fecha del turno")
                    turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche", "Descanso"])
                    
                    if st.form_submit_button("Asignar Turno"):
                        try:
                            conn.execute(
                                "INSERT INTO turnos (empleado, fecha, turno) VALUES (?,?,?)",
                                (emp, str(fecha), turno)
                            )
                            conn.commit()
                            
                            # Enviar notificación por correo
                            correo = empleados[empleados["usuario"] == emp]["correo"].values[0]
                            try:
                                enviar_correo(
                                    correo,
                                    "Nuevo turno asignado",
                                    f"Fecha: {fecha}\nTurno: {turno}"
                                )
                                st.success("✅ Turno asignado y notificado por correo")
                            except:
                                st.success("✅ Turno asignado (sin notificación de correo)")
                            
                        except Exception as ex:
                            st.error(f"❌ Error al asignar turno: {str(ex)}")
            else:
                st.warning("⚠️ Primero debe registrar empleados")
            
            # Mostrar todos los turnos
            st.subheader("📋 Todos los Turnos")
            df_all = pd.read_sql("SELECT * FROM turnos ORDER BY fecha DESC", conn)
            
            if len(df_all) > 0:
                # Mostrar calendario
                with st.expander("📆 Ver Calendario", expanded=False):
                    mostrar_calendario(df_all)
                
                # Mostrar tabla
                st.dataframe(df_all, use_container_width=True)
                
                # Exportar a Excel
                st.subheader("📥 Exportar Datos")
                
                # Convertir a Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_all.to_excel(writer, index=False, sheet_name='Turnos')
                
                st.download_button(
                    label="📥 Descargar Excel",
                    data=output.getvalue(),
                    file_name="turnos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No hay turnos registrados")

        elif menu == "Reportes":
            st.header("📊 Reportes")
            
            df_all = pd.read_sql("SELECT * FROM turnos", conn)
            
            if len(df_all) > 0:
                rep = generar_reporte(df_all)
                st.subheader("📈 Reporte Semanal")
                st.dataframe(rep, use_container_width=True)
                
                # Estadísticas adicionales
                st.subheader("📊 Estadísticas")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Turnos", len(df_all))
                with col2:
                    st.metric("Empleados con Turnos", df_all['empleado'].nunique())
                with col3:
                    st.metric("Turnos por Tipo", dict(df_all['turno'].value_counts().to_dict()))
            else:
                st.info("No hay datos para generar reportes")

    # Sidebar común para todos los roles
    st.sidebar.divider()
    
    # QR Code
    try:
        qr = qrcode.make("https://TU_APP.streamlit.app")
        img_bytes = io.BytesIO()
        qr.save(img_bytes, format='PNG')
        st.sidebar.image(img_bytes.getvalue(), caption="📱 Escanear para instalar app", width=150)
    except:
        st.sidebar.info("📱 App móvil disponible")
    
    # Botón de cierre de sesión
    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    conn.close()