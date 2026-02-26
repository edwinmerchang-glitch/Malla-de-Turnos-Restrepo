import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from database import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite
import os
import shutil
from calendar import monthrange

st.set_page_config("Malla de Turnos", layout="wide")

# ===== OCULTAR EL SIDEBAR DE STREAMLIT =====
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    .main .block-container {
        padding-top: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# -------- LOGIN --------
def login():
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-header h1 {
            color: #2ecc71;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .login-header p {
            color: #666;
        }
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <h1>📅 Malla de Turnos</h1>
                <p>Sistema de Gestión de Horarios</p>
            </div>
        """, unsafe_allow_html=True)
        
        user = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
        pwd = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña")
        
        if st.button("🚀 Ingresar", use_container_width=True):
            if user and pwd:
                session_db = Session()
                emp = session_db.query(Empleado).filter_by(usuario=user, password=pwd).first()
                if emp:
                    st.session_state["user"] = emp
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
            else:
                st.warning("⚠️ Por favor ingresa usuario y contraseña")
        
        st.markdown("</div>", unsafe_allow_html=True)

# Verificar login
if "user" not in st.session_state:
    login()
    st.stop()

# Usuario logueado
user = st.session_state["user"]
session = Session()

# ===== FUNCIONES GLOBALES =====
def cambiar_pagina(pagina):
    st.session_state.pagina_actual = pagina
    st.session_state.menu_open = False

# Inicializar página actual
if "pagina_actual" not in st.session_state:
    if user.rol == "empleado":
        st.session_state.pagina_actual = "Calendario"
    elif user.rol == "supervisor":
        st.session_state.pagina_actual = "Mi equipo"
    else:
        st.session_state.pagina_actual = "Empleados"

# Inicializar menú
if "menu_open" not in st.session_state:
    st.session_state.menu_open = False

# ===== MENÚ HAMBURGUESA =====
st.markdown("""
<style>
    .hamburger-btn {
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 999;
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
        color: white;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4);
        border: none;
    }
    .side-menu {
        position: fixed;
        top: 0;
        left: -320px;
        width: 300px;
        height: 100vh;
        background: white;
        box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        transition: left 0.3s ease;
        z-index: 1000;
        overflow-y: auto;
        padding: 20px;
    }
    .side-menu.open {
        left: 0;
    }
    .menu-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        z-index: 998;
        display: none;
    }
    .menu-overlay.open {
        display: block;
    }
    .menu-header {
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
        color: white;
    }
    .menu-header h2 {
        margin: 0;
    }
    .user-info {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        border-left: 4px solid #2ecc71;
    }
    .user-info-item {
        margin: 0.5rem 0;
    }
    .user-info-label {
        color: #666;
        font-size: 0.8rem;
    }
    .user-info-value {
        color: #333;
        font-weight: bold;
    }
    .menu-buttons .stButton button {
        background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.8rem !important;
        width: 100% !important;
        margin: 0.2rem 0 !important;
    }
    .logout-btn .stButton button {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
    }
    .current-page {
        background: #e8f5e9;
        border-radius: 8px;
        padding: 0.8rem;
        margin-top: 1rem;
        text-align: center;
        color: #2ecc71;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Botón hamburguesa
col1, col2, col3 = st.columns([1, 1, 10])
with col1:
    if st.button("☰", key="hamburger"):
        st.session_state.menu_open = not st.session_state.menu_open
        st.rerun()

# Overlay
if st.session_state.menu_open:
    st.markdown('<div class="menu-overlay open" onclick="document.querySelector(\'button[data-testid=baseButton-header]\').click()"></div>', unsafe_allow_html=True)

# Menú lateral
if st.session_state.menu_open:
    with st.container():
        st.markdown(f"""
        <div class="side-menu open">
            <div class="menu-header">
                <h2>📅 Malla de Turnos</h2>
                <p>Sistema de Gestión de Horarios</p>
            </div>
            <div class="user-info">
                <div class="user-info-item">
                    <div class="user-info-label">Usuario</div>
                    <div class="user-info-value">{user.nombre}</div>
                </div>
                <div class="user-info-item">
                    <div class="user-info-label">Rol</div>
                    <div class="user-info-value">{user.rol.upper()}</div>
                </div>
                <div class="user-info-item">
                    <div class="user-info-label">Área</div>
                    <div class="user-info-value">{user.area if user.area else 'No asignada'}</div>
                </div>
                <div class="user-info-item">
                    <div class="user-info-label">Cargo</div>
                    <div class="user-info-value">{user.cargo if user.cargo else 'No asignado'}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="menu-buttons">', unsafe_allow_html=True)
        
        if user.rol == "empleado":
            if st.button("📅 Calendario", use_container_width=True, key="btn_calendario"):
                cambiar_pagina("Calendario")
            if st.button("📊 Mis turnos", use_container_width=True, key="btn_turnos"):
                cambiar_pagina("Mis turnos")
            if st.button("👤 Mi perfil", use_container_width=True, key="btn_perfil"):
                cambiar_pagina("Mi perfil")
        
        elif user.rol == "supervisor":
            if st.button("👥 Mi equipo", use_container_width=True, key="btn_equipo"):
                cambiar_pagina("Mi equipo")
            if st.button("📊 Matriz área", use_container_width=True, key="btn_matriz_area"):
                cambiar_pagina("Matriz area")
            if st.button("✏️ Asignar turnos", use_container_width=True, key="btn_asignar"):
                cambiar_pagina("Asignar area")
            if st.button("📈 Reportes área", use_container_width=True, key="btn_reportes_area"):
                cambiar_pagina("Reportes area")
            if st.button("👤 Mi perfil", use_container_width=True, key="btn_perfil_sup"):
                cambiar_pagina("Mi perfil")
            if st.button("📅 Mi calendario", use_container_width=True, key="btn_calendario_sup"):
                cambiar_pagina("Calendario")
        
        elif user.rol == "admin":
            if st.button("👥 Empleados", use_container_width=True, key="btn_empleados"):
                cambiar_pagina("Empleados")
            if st.button("⏰ Turnos", use_container_width=True, key="btn_turnos_admin"):
                cambiar_pagina("Turnos")
            if st.button("✏️ Asignar manual", use_container_width=True, key="btn_asignar_admin"):
                cambiar_pagina("Asignacion manual")
            if st.button("🤖 Generar malla", use_container_width=True, key="btn_generar"):
                cambiar_pagina("Generar malla")
            if st.button("📊 Matriz general", use_container_width=True, key="btn_matriz"):
                cambiar_pagina("Matriz turnos")
            if st.button("👤 Mi perfil", use_container_width=True, key="btn_perfil_admin"):
                cambiar_pagina("Mi perfil")
            if st.button("📊 Reportes", use_container_width=True, key="btn_reportes"):
                cambiar_pagina("Reportes")
            if st.button("🛡 Backup", use_container_width=True, key="btn_backup"):
                cambiar_pagina("Backup")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="current-page">📍 Página actual: {st.session_state.pagina_actual}</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("🚪 Cerrar sesión", use_container_width=True, key="btn_logout"):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ===== CONTENIDO DE LA APLICACIÓN =====
op = st.session_state.pagina_actual

# ========== PÁGINA CALENDARIO ==========
if op == "Calendario":
    st.title("📅 Mi Calendario de Turnos")
    st.write(f"Bienvenido {user.nombre}")
    
    col1, col2 = st.columns(2)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes = st.selectbox("Mes", meses)
    with col2:
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
    
    st.info("Aquí se mostrará tu calendario de turnos")

# ========== PÁGINA MI PERFIL ==========
elif op == "Mi perfil":
    st.title("👤 Mi Perfil")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Información Personal")
        st.write(f"**Nombre:** {user.nombre}")
        st.write(f"**Usuario:** {user.usuario}")
        st.write(f"**Rol:** {user.rol}")
    with col2:
        st.subheader("Información Laboral")
        st.write(f"**Área:** {user.area if user.area else 'No asignada'}")
        st.write(f"**Cargo:** {user.cargo if user.cargo else 'No asignado'}")

# ========== PÁGINA MIS TURNOS ==========
elif op == "Mis turnos":
    st.title("📊 Mis Turnos")
    
    col1, col2 = st.columns(2)
    with col1:
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes = st.selectbox("Mes", meses)
    with col2:
        año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
    
    st.info("Aquí se mostrarán tus turnos")

# ========== PÁGINA MI EQUIPO ==========
elif op == "Mi equipo":
    if user.rol != "supervisor":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title(f"👥 Mi equipo - {user.area}")
    st.info("Aquí se mostrarán los empleados de tu área")

# ========== PÁGINA MATRIZ ÁREA ==========
elif op == "Matriz area":
    if user.rol != "supervisor":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title(f"📊 Matriz de turnos - {user.area}")
    st.info("Aquí se mostrará la matriz de turnos de tu área")

# ========== PÁGINA ASIGNAR ÁREA ==========
elif op == "Asignar area":
    if user.rol != "supervisor":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title(f"✏️ Asignar turnos - {user.area}")
    st.info("Aquí podrás asignar turnos a tu equipo")

# ========== PÁGINA REPORTES ÁREA ==========
elif op == "Reportes area":
    if user.rol != "supervisor":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title(f"📈 Reportes - {user.area}")
    st.info("Aquí se mostrarán los reportes de tu área")

# ========== PÁGINA EMPLEADOS ==========
elif op == "Empleados":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("👥 Gestión de Empleados")
    st.info("Aquí podrás gestionar los empleados")

# ========== PÁGINA TURNOS ==========
elif op == "Turnos":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("⏰ Gestión de Turnos")
    st.info("Aquí podrás gestionar los turnos")

# ========== PÁGINA ASIGNACION MANUAL ==========
elif op == "Asignacion manual":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("✏️ Asignación Manual de Turnos")
    st.info("Aquí podrás asignar turnos manualmente")

# ========== PÁGINA GENERAR MALLA ==========
elif op == "Generar malla":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("🤖 Generar Malla Automática")
    st.info("Aquí podrás generar la malla de turnos automáticamente")

# ========== PÁGINA MATRIZ TURNOS ==========
elif op == "Matriz turnos":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("📊 Matriz General de Turnos")
    st.info("Aquí se mostrará la matriz general de turnos")

# ========== PÁGINA REPORTES ==========
elif op == "Reportes":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("📊 Reportes Generales")
    st.info("Aquí se mostrarán los reportes generales")

# ========== PÁGINA BACKUP ==========
elif op == "Backup":
    if user.rol != "admin":
        st.error("No tienes permiso para acceder a esta página")
        st.stop()
    st.title("🛡 Backup y Restauración")
    
    tab1, tab2 = st.tabs(["📤 Exportar Backup", "📥 Importar Backup"])
    
    with tab1:
        st.markdown("### Exportar base de datos")
        if st.button("🔄 Generar backup automático"):
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"backup_{fecha}.db"
            shutil.copy("data.db", nombre_archivo)
            with open(nombre_archivo, "rb") as f:
                st.download_button("📥 Descargar backup", f, nombre_archivo)
            os.remove(nombre_archivo)
    
    with tab2:
        st.markdown("### Importar base de datos")
        st.warning("⚠️ Al importar un backup, se sobrescribirá la base de datos actual")
        archivo = st.file_uploader("Seleccionar archivo de backup", type=['db'])
        if archivo:
            confirmar = st.checkbox("Confirmo que quiero restaurar este backup")
            if st.button("♻️ Restaurar backup", disabled=not confirmar):
                with open("data.db", "wb") as f:
                    f.write(archivo.getbuffer())
                st.success("✅ Base de datos restaurada")
                st.rerun()