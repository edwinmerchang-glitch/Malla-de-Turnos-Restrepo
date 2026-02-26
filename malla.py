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

# Inicializar sesión de base de datos
session = Session()

# Función para limpiar turnos de un empleado
def limpiar_turnos_empleado(empleado_id, fecha_inicio, fecha_fin, tipo_limpieza="todos"):
    """
    Limpia los turnos de un empleado en un rango de fechas
    tipo_limpieza: "todos" (elimina todos), "vacaciones", "incapacidad", "cumpleaños", etc.
    """
    query = session.query(Asignacion).filter(
        Asignacion.empleado_id == empleado_id,
        Asignacion.fecha.between(fecha_inicio, fecha_fin)
    )
    
    if tipo_limpieza != "todos":
        # Filtrar por tipo de turno
        turnos_especiales = {
            "vacaciones": ["VACACIONES", "VAC", "VACACION"],
            "incapacidad": ["INCAPACIDAD", "INCAP", "INC"],
            "cumpleaños": ["DIA CUMPLEAÑOS", "CUMPLEAÑOS", "DIA CUMPLE"],
            "descanso": ["DESCANSO", "DESC", "—"]
        }
        
        if tipo_limpieza in turnos_especiales:
            turnos_filtro = turnos_especiales[tipo_limpieza]
            # Esto requiere una consulta más compleja, por ahora lo dejamos simple
            pass
    
    count = query.delete(synchronize_session=False)
    session.commit()
    return count

# -------- LOGIN MODERNO --------
def login():
    # Estilos CSS para el login
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            animation: slideUp 0.5s ease;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .login-header h1 {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        
        .login-header p {
            color: #666;
            font-size: 1rem;
        }
        
        .login-icon {
            font-size: 4rem;
            text-align: center;
            margin-bottom: 1rem;
            animation: bounce 2s infinite;
        }
        
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .input-field {
            margin-bottom: 1.5rem;
        }
        
        .input-field label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .stTextInput input {
            border: 2px solid #e0e0e0 !important;
            border-radius: 12px !important;
            padding: 0.8rem 1rem !important;
            font-size: 1rem !important;
            transition: all 0.3s !important;
        }
        
        .stTextInput input:focus {
            border-color: #2ecc71 !important;
            box-shadow: 0 0 0 3px rgba(46, 204, 113, 0.1) !important;
        }
        
        .login-button {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.8rem !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            width: 100% !important;
            transition: all 0.3s !important;
            margin-top: 1rem !important;
        }
        
        .login-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 20px rgba(46, 204, 113, 0.4) !important;
        }
        
        .login-footer {
            text-align: center;
            margin-top: 2rem;
            color: #999;
            font-size: 0.9rem;
        }
        
        .login-footer a {
            color: #2ecc71;
            text-decoration: none;
            font-weight: 500;
        }
        
        .login-footer a:hover {
            text-decoration: underline;
        }
        
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        .main > div {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <div class="login-icon">📅</div>
                <h1>Malla de Turnos</h1>
                <p>Sistema de Gestión de Horarios</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="input-field">', unsafe_allow_html=True)
        user_input = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario", key="login_user")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-field">', unsafe_allow_html=True)
        pwd_input = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña", key="login_pwd")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Ingresar", use_container_width=True, key="login_btn"):
            if user_input and pwd_input:
                session_db = Session()
                emp = session_db.query(Empleado).filter_by(usuario=user_input, password=pwd_input).first()
                if emp:
                    st.session_state["user"] = emp
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
            else:
                st.warning("⚠️ Por favor ingresa usuario y contraseña")
        
        st.markdown("""
            <div class="login-footer">
                <p>¿Olvidaste tu contraseña? Contacta al administrador</p>
                <p>© 2026 Malla de Turnos - Versión 2.0</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# -------- CONTENIDO PRINCIPAL --------
if "user" in st.session_state:
    user = st.session_state["user"]
    
    # -------- MENÚ MODERNO CON BOTONES SEGÚN EL ROL --------
    st.sidebar.markdown("""
    <style>
        .sidebar-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem 1rem;
            border-radius: 0 0 20px 20px;
            margin-bottom: 1.5rem;
            text-align: center;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .sidebar-header h1 {
            font-size: 1.8rem;
            margin: 0;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .sidebar-header p {
            margin: 0.5rem 0 0;
            opacity: 0.9;
            font-size: 0.9rem;
        }
        .user-info-card {
            background: white;
            border-radius: 15px;
            padding: 1.2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border: 1px solid #f0f0f0;
        }
        .user-info-item {
            display: flex;
            align-items: center;
            padding: 0.5rem;
            margin: 0.3rem 0;
            background: #f8f9fa;
            border-radius: 10px;
            transition: all 0.3s;
        }
        .user-info-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .user-info-icon {
            font-size: 1.2rem;
            margin-right: 0.8rem;
            min-width: 30px;
            text-align: center;
        }
        .user-info-label {
            color: #666;
            font-size: 0.8rem;
            margin-bottom: 0.1rem;
        }
        .user-info-value {
            color: #333;
            font-weight: bold;
            font-size: 0.95rem;
        }
        .menu-section {
            background: white;
            border-radius: 15px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .menu-title {
            font-size: 1.1rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .current-page {
            background: linear-gradient(135deg, #f6f9fc 0%, #e6f0f7 100%);
            border-radius: 10px;
            padding: 0.8rem;
            margin-top: 1rem;
            border: 1px solid #667eea;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .current-page-icon {
            font-size: 1.2rem;
        }
        .current-page-text {
            color: #667eea;
            font-weight: bold;
            font-size: 0.95rem;
        }
        .footer {
            text-align: center;
            margin-top: 2rem;
            padding: 1rem;
            color: #999;
            font-size: 0.8rem;
            border-top: 1px solid #f0f0f0;
        }
        .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.8rem !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            transition: all 0.3s !important;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
        }
        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 15px rgba(102, 126, 234, 0.4) !important;
        }
        .stButton button:active {
            transform: translateY(0) !important;
        }
        .stButton button[kind="secondary"] {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5253 100%) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Cabecera del sidebar
    st.sidebar.markdown("""
    <div class="sidebar-header">
        <h1>📅 Malla de Turnos</h1>
        <p>Sistema de Gestión de Horarios</p>
    </div>
    """, unsafe_allow_html=True)

    # Tarjeta de información del usuario
    st.sidebar.markdown(f"""
    <div class="user-info-card">
        <div class="user-info-item">
            <div class="user-info-icon">👤</div>
            <div>
                <div class="user-info-label">Usuario</div>
                <div class="user-info-value">{user.nombre}</div>
            </div>
        </div>
        <div class="user-info-item">
            <div class="user-info-icon">🔑</div>
            <div>
                <div class="user-info-label">Rol</div>
                <div class="user-info-value">{user.rol.upper()}</div>
            </div>
        </div>
        <div class="user-info-item">
            <div class="user-info-icon">🏢</div>
            <div>
                <div class="user-info-label">Área</div>
                <div class="user-info-value">{user.area if user.area else 'No asignada'}</div>
            </div>
        </div>
        <div class="user-info-item">
            <div class="user-info-icon">📌</div>
            <div>
                <div class="user-info-label">Cargo</div>
                <div class="user-info-value">{user.cargo if user.cargo else 'No asignado'}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Inicializar la página actual
    if "pagina_actual" not in st.session_state:
        if user.rol == "empleado":
            st.session_state.pagina_actual = "Calendario"
        elif user.rol == "supervisor":
            st.session_state.pagina_actual = "Mi equipo"
        else:  # admin
            st.session_state.pagina_actual = "Empleados"

    def cambiar_pagina(pagina):
        st.session_state.pagina_actual = pagina

    # -------- MENÚ PARA EMPLEADOS --------
    if user.rol == "empleado":
        st.sidebar.markdown("""
        <div class="menu-section">
            <div class="menu-title">
                <span>📋</span> Mi Espacio
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("📅 Calendario", use_container_width=True, key="btn_calendario"):
                cambiar_pagina("Calendario")
            if st.button("👤 Mi perfil", use_container_width=True, key="btn_perfil"):
                cambiar_pagina("Mi perfil")
        
        with col2:
            if st.button("📊 Mis turnos", use_container_width=True, key="btn_turnos"):
                cambiar_pagina("Mis turnos")
        
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    # -------- MENÚ PARA SUPERVISORES --------
    elif user.rol == "supervisor":
        st.sidebar.markdown("""
        <div class="menu-section">
            <div class="menu-title">
                <span>👥</span> Mi Área
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("👥 Mi equipo", use_container_width=True, key="btn_equipo"):
                cambiar_pagina("Mi equipo")
            if st.button("📊 Matriz área", use_container_width=True, key="btn_matriz_area"):
                cambiar_pagina("Matriz area")
            if st.button("👤 Mi perfil", use_container_width=True, key="btn_perfil_sup"):
                cambiar_pagina("Mi perfil")
        
        with col2:
            if st.button("✏️ Asignar turnos", use_container_width=True, key="btn_asignar"):
                cambiar_pagina("Asignar area")
            if st.button("📈 Reportes área", use_container_width=True, key="btn_reportes_area"):
                cambiar_pagina("Reportes area")
            if st.button("📅 Mi calendario", use_container_width=True, key="btn_calendario_sup"):
                cambiar_pagina("Calendario")
        
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    # -------- MENÚ PARA ADMINISTRADORES --------
    elif user.rol == "admin":
        st.sidebar.markdown("""
        <div class="menu-section">
            <div class="menu-title">
                <span>⚙️</span> Administración
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("👥 Empleados", use_container_width=True, key="btn_empleados"):
                cambiar_pagina("Empleados")
            if st.button("⏰ Turnos", use_container_width=True, key="btn_turnos_admin"):
                cambiar_pagina("Turnos")
            if st.button("📊 Matriz general", use_container_width=True, key="btn_matriz"):
                cambiar_pagina("Matriz turnos")
            if st.button("👤 Mi perfil", use_container_width=True, key="btn_perfil_admin"):
                cambiar_pagina("Mi perfil")
        
        with col2:
            if st.button("✏️ Asignar manual", use_container_width=True, key="btn_asignar_admin"):
                cambiar_pagina("Asignacion manual")
            if st.button("🤖 Generar malla", use_container_width=True, key="btn_generar"):
                cambiar_pagina("Generar malla")
            if st.button("📊 Reportes", use_container_width=True, key="btn_reportes"):
                cambiar_pagina("Reportes")
            if st.button("🛡 Backup", use_container_width=True, key="btn_backup"):
                cambiar_pagina("Backup")
        
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    # Indicador de página actual
    st.sidebar.markdown(f"""
    <div class="current-page">
        <span class="current-page-icon">📍</span>
        <span class="current-page-text">Página actual: {st.session_state.pagina_actual}</span>
    </div>
    """, unsafe_allow_html=True)

    # Botón de cerrar sesión
    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True, key="btn_logout"):
        st.session_state.clear()
        st.rerun()

    # Footer
    st.sidebar.markdown("""
    <div class="footer">
        © 2026 Malla de Turnos<br>
        Versión 2.0
    </div>
    """, unsafe_allow_html=True)

    # -------- CONTENIDO --------
    op = st.session_state.pagina_actual

    # ========== PÁGINAS PARA EMPLEADOS ==========
    
    # ---------- CALENDARIO MODERNO ----------
    if op == "Calendario":
        if user.rol not in ["empleado", "supervisor"]:
            st.error("❌ No tienes permiso para acceder a esta sección")
            st.stop()
        
        st.markdown("""
        <style>
        .calendario-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .calendario-titulo {
            color: white;
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .calendario-subtitulo {
            color: rgba(255,255,255,0.9);
            font-size: 1.2rem;
            text-align: center;
            margin-bottom: 2rem;
        }
        .filtros-container {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .stats-card {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }
        .stats-card:hover {
            transform: translateY(-5px);
        }
        .stats-numero {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            margin: 0.5rem 0;
        }
        .stats-label {
            color: #666;
            font-size: 1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .evento-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.8rem;
            border-radius: 10px;
            margin: 0.3rem 0;
            font-size: 0.9rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: all 0.3s;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .evento-card:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .evento-hora {
            font-size: 0.8rem;
            opacity: 0.9;
            margin-top: 0.2rem;
            text-align: center;
        }
        .dia-card {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            min-height: 120px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
            transition: all 0.3s;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }
        .dia-card:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        .dia-numero {
            font-size: 1.2rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.5rem;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.3rem;
            width: 100%;
            text-align: center;
        }
        .dia-semana {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        .descanso-texto {
            color: #28a745;
            font-weight: bold;
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="calendario-container">
            <div class="calendario-titulo">📅 Mi Calendario de Turnos</div>
            <div class="calendario-subtitulo">Visualiza y gestiona tus horarios de trabajo</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="stats-card">
                    <div style="font-size: 2rem;">👤</div>
                    <div class="stats-numero">{user.nombre}</div>
                    <div class="stats-label">Empleado</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stats-card">
                    <div style="font-size: 2rem;">🏢</div>
                    <div class="stats-numero">{user.area if user.area else 'General'}</div>
                    <div class="stats-label">Área</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stats-card">
                    <div style="font-size: 2rem;">📌</div>
                    <div class="stats-numero">{user.cargo if user.cargo else 'Colaborador'}</div>
                    <div class="stats-label">Cargo</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes = st.selectbox("📆 Selecciona el mes", meses, index=1, key="cal_mes_moderno")
            with col2:
                año = st.number_input("📅 Año", min_value=2024, max_value=2030, value=2026, key="cal_ano_moderno")
            st.markdown('</div>', unsafe_allow_html=True)
        
        mes_num = meses.index(mes) + 1
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
        
        total_turnos = len(asignaciones)
        turnos_por_tipo = {}
        for a in asignaciones:
            if a.turno:
                turnos_por_tipo[a.turno.nombre] = turnos_por_tipo.get(a.turno.nombre, 0) + 1
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-numero">{total_turnos}</div>
                <div class="stats-label">Turnos en el mes</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-numero">{len(turnos_por_tipo)}</div>
                <div class="stats-label">Tipos de turno</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            dias_trabajados = len(set([a.fecha.day for a in asignaciones]))
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-numero">{dias_trabajados}</div>
                <div class="stats-label">Días trabajados</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-numero">{dias_mes - dias_trabajados}</div>
                <div class="stats-label">Días de descanso</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        turnos_por_dia = {}
        for a in asignaciones:
            dia = a.fecha.day
            turnos_por_dia[dia] = a
        
        dias_semana = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
        primer_dia = date(año, mes_num, 1).weekday()
        
        st.markdown(f"### 📅 {mes} {año}")
        
        cols = st.columns(7)
        for i, dia in enumerate(dias_semana):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align: center; font-weight: bold; color: #667eea; padding: 10px;">
                    {dia}
                </div>
                """, unsafe_allow_html=True)
        
        dia_actual = 1
        semanas = []
        
        for semana in range(6):
            fila = []
            for dia_semana in range(7):
                if semana == 0 and dia_semana < primer_dia:
                    fila.append(None)
                elif dia_actual <= dias_mes:
                    fila.append(dia_actual)
                    dia_actual += 1
                else:
                    fila.append(None)
            semanas.append(fila)
        
        for semana in semanas:
            cols = st.columns(7)
            for i, dia in enumerate(semana):
                with cols[i]:
                    if dia is not None:
                        if dia in turnos_por_dia:
                            turno = turnos_por_dia[dia].turno
                            st.markdown(f"""
                            <div class="dia-card">
                                <div class="dia-numero">{dia}</div>
                                <div class="evento-card">
                                    <div style="font-weight: bold;">{turno.nombre}</div>
                                    <div class="evento-hora">{turno.inicio} - {turno.fin}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="dia-card">
                                <div class="dia-numero">{dia}</div>
                                <div style="color: #999; text-align: center; padding: 10px;">
                                    🟢 Descanso
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="dia-card" style="background: #f9f9f9; opacity: 0.5;">
                            <div style="text-align: center; color: #ccc;">-</div>
                        </div>
                        """, unsafe_allow_html=True)

    # ---------- MI PERFIL MODERNO ----------
    elif op == "Mi perfil":
        # Aquí iría el código de Mi perfil...
        st.subheader("👤 Mi Perfil")
        
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

    # ========== PÁGINAS PARA ADMINISTRADORES ==========
    
    # ---------- EMPLEADOS ----------
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

    # ---------- TURNOS ----------
    elif op == "Turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("⏰ Gestión de Turnos")
        
        tab1, tab2, tab3 = st.tabs(["📋 Lista de turnos", "➕ Nuevo turno", "✏️ Editar/Eliminar"])
        
        with tab1:
            turnos = session.query(Turno).all()
            if turnos:
                data = []
                for t in turnos:
                    data.append({
                        "ID": t.id,
                        "Nombre": t.nombre,
                        "Inicio": t.inicio,
                        "Fin": t.fin
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                st.metric("Total turnos", len(turnos))
            else:
                st.info("No hay turnos registrados")
        
        with tab2:
            st.markdown("### Crear nuevo turno")
            
            with st.form("nuevo_turno"):
                col1, col2 = st.columns(2)
                with col1:
                    n = st.text_input("Nombre del turno *", placeholder="Ej: 151, 155, 70...")
                with col2:
                    pass
                
                col1, col2 = st.columns(2)
                with col1:
                    hi = st.text_input("Hora inicio *", placeholder="Ej: 08:00")
                with col2:
                    hf = st.text_input("Hora fin *", placeholder="Ej: 16:00")
                
                submitted = st.form_submit_button("✅ Crear turno", use_container_width=True)
                
                if submitted:
                    if n and hi and hf:
                        existe = session.query(Turno).filter_by(nombre=n).first()
                        if existe:
                            st.error(f"❌ El turno '{n}' ya existe")
                        else:
                            session.add(Turno(nombre=n, inicio=hi, fin=hf))
                            session.commit()
                            st.success(f"✅ Turno '{n}' creado correctamente")
                            st.rerun()
                    else:
                        st.error("❌ Todos los campos son obligatorios")
        
        with tab3:
            st.markdown("### Editar o eliminar turnos")
            
            turnos = session.query(Turno).all()
            
            if not turnos:
                st.info("No hay turnos para editar")
            else:
                opciones = {f"{t.nombre} ({t.inicio} - {t.fin})": t.id for t in turnos}
                seleccion = st.selectbox("Seleccionar turno", list(opciones.keys()))
                turno_id = opciones[seleccion]
                turno = session.get(Turno, turno_id)
                
                if turno:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        with st.form("editar_turno"):
                            st.markdown("#### Editar turno")
                            
                            nombre_edit = st.text_input("Nombre", value=turno.nombre)
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                inicio_edit = st.text_input("Hora inicio", value=turno.inicio)
                            with col_b:
                                fin_edit = st.text_input("Hora fin", value=turno.fin)
                            
                            col_guardar, col_eliminar = st.columns(2)
                            with col_guardar:
                                guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
                            with col_eliminar:
                                eliminar = st.form_submit_button("🗑️ Eliminar", use_container_width=True)
                            
                            if guardar:
                                existe = session.query(Turno).filter(
                                    Turno.nombre == nombre_edit,
                                    Turno.id != turno.id
                                ).first()
                                
                                if existe:
                                    st.error(f"❌ Ya existe un turno con el nombre '{nombre_edit}'")
                                else:
                                    turno.nombre = nombre_edit
                                    turno.inicio = inicio_edit
                                    turno.fin = fin_edit
                                    session.commit()
                                    st.success("✅ Turno actualizado correctamente")
                                    st.rerun()
                            
                            if eliminar:
                                asignaciones = session.query(Asignacion).filter_by(turno_id=turno.id).first()
                                if asignaciones:
                                    st.warning("⚠️ Este turno tiene asignaciones. No se puede eliminar.")
                                    st.info("Primero elimina las asignaciones de este turno.")
                                else:
                                    session.delete(turno)
                                    session.commit()
                                    st.success("✅ Turno eliminado correctamente")
                                    st.rerun()
                    
                    with col2:
                        st.markdown("#### 📊 Estadísticas")
                        
                        total_asignaciones = session.query(Asignacion).filter_by(turno_id=turno.id).count()
                        st.metric("Asignaciones", total_asignaciones)
                        
                        ultima_asignacion = session.query(Asignacion).filter_by(turno_id=turno.id).order_by(Asignacion.fecha.desc()).first()
                        if ultima_asignacion:
                            st.caption(f"Último uso: {ultima_asignacion.fecha.strftime('%d/%m/%Y')}")

    # ---------- MATRIZ TURNOS (ADMIN) ----------
    elif op == "Matriz turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("📊 Matriz general de turnos")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes = st.selectbox("Mes", meses, index=1)
        with col2:
            año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
        with col3:
            areas = list(set([e.area for e in session.query(Empleado).all() if e.area]))
            areas.sort()
            area_filtro = st.selectbox("Filtrar por área", ["Todas"] + areas)
        
        mes_num = meses.index(mes) + 1
        from calendar import monthrange
        dias_mes = monthrange(año, mes_num)[1]
        
        empleados = session.query(Empleado).all()
        if area_filtro != "Todas":
            empleados = [e for e in empleados if e.area == area_filtro]
        
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
        
        if not empleados:
            st.warning("⚠️ No hay empleados registrados")
            st.stop()
        
        if not turnos:
            st.warning("⚠️ No hay turnos registrados")
            st.stop()
        
        tab1, tab2, tab3 = st.tabs(["📋 Vista matriz", "✏️ Edición rápida", "📥 Carga masiva"])
        
        with tab1:
            st.markdown("### Vista de matriz de turnos")
            
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
                        fila[str(dia)] = turnos_dict.get(turno_id, "?")
                    else:
                        fila[str(dia)] = "—"
                data.append(fila)
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, height=600)
                
                total = sum(1 for emp in matriz for dia in matriz[emp])
                st.metric("Total turnos asignados", total)
        
        with tab2:
            st.markdown("### Edición rápida")
            st.info("Selecciona empleado y rango de fechas")
            
            if empleados:
                col1, col2 = st.columns(2)
                with col1:
                    emp_sel = st.selectbox("Empleado", [e.nombre for e in empleados])
                    empleado = next(e for e in empleados if e.nombre == emp_sel)
                
                with col2:
                    turno_opciones = ["Descanso"] + [t.nombre for t in turnos]
                    turno_sel = st.selectbox("Turno", turno_opciones)
                
                col1, col2 = st.columns(2)
                with col1:
                    dia_inicio = st.number_input("Día inicio", 1, dias_mes, 1)
                with col2:
                    dia_fin = st.number_input("Día fin", dia_inicio, dias_mes, dia_inicio)
                
                if st.button("🔄 Aplicar asignación masiva", use_container_width=True):
                    turno_id = None
                    if turno_sel != "Descanso":
                        turno = session.query(Turno).filter_by(nombre=turno_sel).first()
                        if turno:
                            turno_id = turno.id
                    
                    count = 0
                    for dia in range(dia_inicio, dia_fin + 1):
                        fecha = date(año, mes_num, dia)
                        existe = session.query(Asignacion).filter_by(
                            empleado_id=empleado.id, fecha=fecha
                        ).first()
                        
                        if turno_id is None:
                            if existe:
                                session.delete(existe)
                                count += 1
                        else:
                            if existe:
                                existe.turno_id = turno_id
                            else:
                                session.add(Asignacion(
                                    empleado_id=empleado.id,
                                    fecha=fecha,
                                    turno_id=turno_id
                                ))
                            count += 1
                    
                    session.commit()
                    st.success(f"✅ {count} turnos actualizados")
                    st.rerun()
        
        with tab3:
            st.markdown("### Carga masiva desde Excel")
            st.markdown("""
            **Formato del archivo:**
            - **Columna A:** Empleado (nombre exacto)
            - **Columna B:** Área (opcional)
            - **Columna C en adelante:** Números de día (1, 2, 3, ... 31)
            
            **Valores:** Nombre del turno (ej: 151, 155, 70) o dejar vacío para descanso
            """)
            
            # Aquí iría el código de carga masiva...

    # ---------- ASIGNACION MANUAL ----------
    elif op == "Asignacion manual":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("✏️ Asignación manual de turnos")
        st.info("Función en desarrollo - Usa la matriz para asignaciones masivas")

    # ---------- GENERAR MALLA ----------
    elif op == "Generar malla":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("🤖 Generar malla automática")
        st.info("Función en desarrollo")

    # ---------- REPORTES ----------
    elif op == "Reportes":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("📊 Reportes generales")
        st.info("Función en desarrollo")

    # ---------- BACKUP ----------
    elif op == "Backup":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("🛡 Backup y Restauración")
        
        tab1, tab2 = st.tabs(["📤 Exportar Backup", "📥 Importar Backup"])
        
        with tab1:
            st.markdown("### Exportar base de datos")
            st.markdown("Guarda una copia de seguridad en la ubicación que elijas")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Backup simple**")
                if st.button("🔄 Generar backup automático", use_container_width=True):
                    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"backup_{fecha}.db"
                    
                    shutil.copy("data.db", nombre_archivo)
                    
                    with open(nombre_archivo, "rb") as f:
                        st.download_button(
                            "📥 Descargar backup",
                            f,
                            nombre_archivo,
                            "application/octet-stream",
                            use_container_width=True
                        )
                    
                    os.remove(nombre_archivo)
            
            with col2:
                st.markdown("**Backup con nombre**")
                nombre_personalizado = st.text_input("Nombre del archivo", placeholder="ej: backup_enero")
                
                if st.button("📝 Generar backup personalizado", use_container_width=True):
                    if nombre_personalizado:
                        nombre_limpio = "".join(c for c in nombre_personalizado if c.isalnum() or c in [' ', '-', '_']).strip()
                        nombre_limpio = nombre_limpio.replace(' ', '_')
                        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_archivo = f"{nombre_limpio}_{fecha}.db"
                        
                        shutil.copy("data.db", nombre_archivo)
                        
                        with open(nombre_archivo, "rb") as f:
                            st.download_button(
                                "📥 Descargar backup personalizado",
                                f,
                                nombre_archivo,
                                "application/octet-stream",
                                use_container_width=True
                            )
                        
                        os.remove(nombre_archivo)
                    else:
                        st.warning("⚠️ Ingresa un nombre para el archivo")
            
            st.markdown("---")
            st.markdown("### 📁 Backups recientes")
            
            if os.path.exists("data/backups"):
                backups = os.listdir("data/backups")
                if backups:
                    backups.sort(reverse=True)
                    
                    for i, b in enumerate(backups[:5]):
                        ruta_completa = f"data/backups/{b}"
                        tamaño = os.path.getsize(ruta_completa)
                        
                        if tamaño < 1024:
                            tamaño_str = f"{tamaño} B"
                        elif tamaño < 1024 * 1024:
                            tamaño_str = f"{tamaño/1024:.1f} KB"
                        else:
                            tamaño_str = f"{tamaño/(1024*1024):.1f} MB"
                        
                        fecha_mod = os.path.getmtime(ruta_completa)
                        fecha_str = datetime.fromtimestamp(fecha_mod).strftime("%d/%m/%Y %H:%M")
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"{i+1}. {b} ({tamaño_str}) - {fecha_str}")
                        with col2:
                            with open(ruta_completa, "rb") as f:
                                st.download_button(
                                    "📥",
                                    f,
                                    b,
                                    "application/octet-stream",
                                    key=f"download_{b}"
                                )
                else:
                    st.info("No hay backups en la carpeta local")
        
        with tab2:
            st.markdown("### Importar base de datos")
            st.warning("⚠️ **Importante:** Al importar un backup, se sobrescribirá la base de datos actual")
            
            archivo_subido = st.file_uploader(
                "Seleccionar archivo de backup",
                type=['db'],
                help="Selecciona un archivo .db para restaurar"
            )
            
            if archivo_subido is not None:
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Archivo:** {archivo_subido.name}")
                with col2:
                    tamaño_kb = len(archivo_subido.getvalue()) / 1024
                    st.info(f"**Tamaño:** {tamaño_kb:.1f} KB")
                
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col2:
                    confirmar = st.checkbox("Confirmo que quiero restaurar este backup")
                    
                    if st.button("♻️ Restaurar backup", use_container_width=True, type="primary", disabled=not confirmar):
                        try:
                            fecha_ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
                            backup_seguridad = f"data/backups/ANTES_RESTAURAR_{fecha_ahora}.db"
                            
                            if os.path.exists("data.db"):
                                # Crear directorio si no existe
                                os.makedirs("data/backups", exist_ok=True)
                                shutil.copy("data.db", backup_seguridad)
                                st.info(f"✅ Backup de seguridad creado: {os.path.basename(backup_seguridad)}")
                            
                            with open("data.db", "wb") as f:
                                f.write(archivo_subido.getbuffer())
                            
                            st.success("✅ Base de datos restaurada correctamente")
                            st.balloons()
                            st.warning("🔄 La aplicación se recargará para aplicar los cambios")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error al restaurar: {str(e)}")

else:
    login()