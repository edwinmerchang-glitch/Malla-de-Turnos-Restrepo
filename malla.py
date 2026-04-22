import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from database import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite
import os
import shutil
from calendar import monthrange
from io import BytesIO
import xlsxwriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from sqlalchemy import create_engine, text

# ============ FUNCIONES AUXILIARES ============

def get_mes_actual():
    """Retorna el índice del mes actual (0-11) y el año actual"""
    hoy = datetime.now()
    return hoy.month - 1, hoy.year

def inicializar_tabla_comentarios():
    """Crear tabla de comentarios si no existe"""
    try:
        engine = create_engine("sqlite:///data.db")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS comentarios_area (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area TEXT NOT NULL,
                    fecha DATE NOT NULL,
                    usuario TEXT NOT NULL,
                    comentario TEXT NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    except Exception as e:
        pass

def guardar_comentario(area, fecha, usuario, comentario):
    """Guardar un comentario en la base de datos"""
    try:
        engine = create_engine("sqlite:///data.db")
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO comentarios_area (area, fecha, usuario, comentario)
                VALUES (:area, :fecha, :usuario, :comentario)
            """), {"area": area, "fecha": fecha, "usuario": usuario, "comentario": comentario})
            conn.commit()
        return True
    except Exception as e:
        return False

def obtener_comentarios(area, fecha):
    """Obtener comentarios de un área en una fecha específica"""
    try:
        engine = create_engine("sqlite:///data.db")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT usuario, comentario, fecha_creacion 
                FROM comentarios_area 
                WHERE area = :area AND fecha = :fecha
                ORDER BY fecha_creacion DESC
            """), {"area": area, "fecha": fecha})
            return result.fetchall()
    except Exception as e:
        return []

def verificar_notificaciones_area(area):
    """Verifica si hay nuevas notificaciones en el área"""
    try:
        engine = create_engine("sqlite:///data.db")
        with engine.connect() as conn:
            ayer = datetime.now() - timedelta(days=1)
            comentarios = conn.execute(text("""
                SELECT COUNT(*) FROM comentarios_area 
                WHERE area = :area AND fecha_creacion > :ayer
            """), {"area": area, "ayer": ayer}).scalar()
            return comentarios if comentarios else 0
    except:
        return 0

def exportar_calendario_area_excel(empleados, asignaciones, turnos_dict, mes, año, area):
    """Exportar calendario del área a Excel"""
    meses_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
        "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
        "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
    }
    mes_num = meses_dict[mes]
    dias_mes = monthrange(año, mes_num)[1]
    
    data = []
    header = ["Empleado", "Cargo"]
    for dia in range(1, dias_mes + 1):
        fecha = date(año, mes_num, dia)
        header.append(f"{dia}\n{fecha.strftime('%a')}")
    data.append(header)
    
    for emp in empleados:
        row = [emp.nombre, emp.cargo or ""]
        for dia in range(1, dias_mes + 1):
            turno_encontrado = None
            for a in asignaciones:
                if a.empleado_id == emp.id and a.fecha.day == dia:
                    turno_encontrado = turnos_dict.get(a.turno_id, "?")
                    break
            row.append(turno_encontrado or "Descanso")
        data.append(row)
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(f"Calendario {mes} {año}")
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#667eea',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    
    descanso_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#f0f0f0'
    })
    
    turno_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#e8f5e9'
    })
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    for row_num, row_data in enumerate(data):
        for col_num, value in enumerate(row_data):
            if row_num == 0:
                worksheet.write(row_num, col_num, value, header_format)
            else:
                if col_num >= 2:
                    if value == "Descanso":
                        worksheet.write(row_num, col_num, value, descanso_format)
                    else:
                        worksheet.write(row_num, col_num, value, turno_format)
                else:
                    worksheet.write(row_num, col_num, value, cell_format)
    
    worksheet.set_column(0, 1, 20)
    worksheet.set_column(2, dias_mes + 1, 12)
    
    workbook.close()
    output.seek(0)
    return output

def exportar_calendario_area_pdf(empleados, asignaciones, turnos_dict, mes, año, area):
    """Exportar calendario del área a PDF"""
    meses_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
        "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
        "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
    }
    mes_num = meses_dict[mes]
    dias_mes = monthrange(año, mes_num)[1]
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           rightMargin=1*cm, leftMargin=1*cm, 
                           topMargin=2*cm, bottomMargin=1*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#667eea'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    elements = []
    title = Paragraph(f"Calendario de Turnos - {area}<br/>{mes} {año}", title_style)
    elements.append(title)
    
    table_data = []
    header = ["Empleado"]
    for dia in range(1, min(dias_mes + 1, 16)):
        fecha = date(año, mes_num, dia)
        header.append(f"{dia}\n{fecha.strftime('%a')}")
    table_data.append(header)
    
    for emp in empleados[:15]:
        row = [emp.nombre[:12] + "..." if len(emp.nombre) > 12 else emp.nombre]
        for dia in range(1, min(dias_mes + 1, 16)):
            turno_encontrado = None
            for a in asignaciones:
                if a.empleado_id == emp.id and a.fecha.day == dia:
                    turno_encontrado = turnos_dict.get(a.turno_id, "?")
                    break
            row.append(turno_encontrado or "D")
        table_data.append(row)
    
    table = Table(table_data, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ])
    table.setStyle(style)
    elements.append(table)
    
    elements.append(Spacer(1, 20))
    total_turnos = len([a for a in asignaciones if a.turno_id])
    stats_text = f"""
    <b>Estadísticas:</b> Total empleados: {len(empleados)} | Turnos asignados: {total_turnos}
    """
    stats_para = Paragraph(stats_text, styles['Normal'])
    elements.append(stats_para)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============ CONFIGURACIÓN DE PÁGINA ============
st.set_page_config("Malla de Turnos", layout="wide")

# Inicializar sesión de base de datos
session = Session()

# Inicializar tabla de comentarios
inicializar_tabla_comentarios()

# ============ LOGIN ============
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
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem;
            font-weight: bold;
        }
        .login-icon {
            font-size: 4rem;
            text-align: center;
            margin-bottom: 1rem;
        }
        .stButton button {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.8rem !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            width: 100% !important;
        }
        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 20px rgba(46, 204, 113, 0.4) !important;
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
                <div class="login-icon">📅</div>
                <h1>Malla de Turnos</h1>
                <p>Gestión de Horarios Locatel Restrepo</p>
            </div>
        """, unsafe_allow_html=True)
        
        user_input = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario", key="login_user")
        pwd_input = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña", key="login_pwd")
        
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
            <div style="text-align: center; margin-top: 2rem; color: #999; font-size: 0.9rem;">
                <p>© 2026 Edwin Merchán - Versión 3.0</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============ CONTENIDO PRINCIPAL ============
if "user" in st.session_state:
    user = st.session_state["user"]
    
    notificaciones = 0
    if user.area:
        notificaciones = verificar_notificaciones_area(user.area)
    
    st.markdown("""
    <style>
        .stButton button {
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.8rem !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            transition: all 0.3s !important;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3) !important;
        }
        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 15px rgba(76, 175, 80, 0.4) !important;
            background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%) !important;
        }
        .empleado-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .empleado-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
        }
        .comentario-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #667eea;
        }
        .stats-card {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; text-align: center;">
            <h2 style="color: white; margin: 0;">📅 Malla de Turnos</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0;">Locatel Restrepo</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background: white; border-radius: 15px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 1.5rem; margin-right: 10px;">👤</span>
                <div>
                    <div style="font-weight: bold;">{user.nombre}</div>
                    <div style="color: #666; font-size: 0.85rem;">{user.rol.upper()}</div>
                </div>
            </div>
            <hr style="margin: 10px 0;">
            <div style="font-size: 0.9rem;">
                <div>🏢 {user.area if user.area else 'Sin área'}</div>
                <div>📌 {user.cargo if user.cargo else 'Sin cargo'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if notificaciones > 0:
            st.markdown(f"""
            <div style="background: #ff6b6b; color: white; padding: 10px; 
                        border-radius: 10px; margin: 10px 0; text-align: center;">
                🔔 {notificaciones} notificaciones nuevas en tu área
            </div>
            """, unsafe_allow_html=True)
        
        if "pagina_actual" not in st.session_state:
            if user.rol == "empleado":
                st.session_state.pagina_actual = "Mi area"
            elif user.rol == "supervisor":
                st.session_state.pagina_actual = "Mi equipo"
            else:
                st.session_state.pagina_actual = "Empleados"
        
        def cambiar_pagina(pagina):
            st.session_state.pagina_actual = pagina
        
        st.markdown("### 📋 Menú")
        
        if user.rol == "empleado":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("👥 Mi área", use_container_width=True):
                    cambiar_pagina("Mi area")
                if st.button("📅 Calendario", use_container_width=True):
                    cambiar_pagina("Calendario")
            with col2:
                if st.button("📊 Mis turnos", use_container_width=True):
                    cambiar_pagina("Mis turnos")
                if st.button("👤 Mi perfil", use_container_width=True):
                    cambiar_pagina("Mi perfil")
        
        elif user.rol == "supervisor":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("👥 Mi equipo", use_container_width=True):
                    cambiar_pagina("Mi equipo")
                if st.button("📊 Matriz área", use_container_width=True):
                    cambiar_pagina("Matriz area")
                if st.button("👤 Mi perfil", use_container_width=True):
                    cambiar_pagina("Mi perfil")
            with col2:
                if st.button("✏️ Asignar", use_container_width=True):
                    cambiar_pagina("Asignar area")
                if st.button("📈 Reportes", use_container_width=True):
                    cambiar_pagina("Reportes area")
                if st.button("🌐 Otras áreas", use_container_width=True):
                    cambiar_pagina("Otras areas")
        
        elif user.rol == "admin":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("👥 Empleados", use_container_width=True):
                    cambiar_pagina("Empleados")
                if st.button("⏰ Turnos", use_container_width=True):
                    cambiar_pagina("Turnos")
                if st.button("📊 Matriz", use_container_width=True):
                    cambiar_pagina("Matriz turnos")
                if st.button("👤 Mi perfil", use_container_width=True):
                    cambiar_pagina("Mi perfil")
            with col2:
                if st.button("✏️ Asignar", use_container_width=True):
                    cambiar_pagina("Asignacion manual")
                if st.button("🤖 Generar", use_container_width=True):
                    cambiar_pagina("Generar malla")
                if st.button("📈 Reportes", use_container_width=True):
                    cambiar_pagina("Reportes")
                if st.button("🛡 Backup", use_container_width=True):
                    cambiar_pagina("Backup")
        
        st.markdown("---")
        st.markdown(f"📍 **Página actual:** {st.session_state.pagina_actual}")
        
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #999; font-size: 0.8rem;">
            © 2026 Edwin Merchán<br>Versión 3.0
        </div>
        """, unsafe_allow_html=True)
    
    op = st.session_state.pagina_actual
    
    # ============ PÁGINA: MI ÁREA ============
    if op == "Mi area":
        if user.rol not in ["empleado", "supervisor"]:
            st.error("❌ No tienes permiso para acceder a esta sección")
            st.stop()
        
        area_usuario = user.area if user.area else "Sin área asignada"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 20px; margin-bottom: 2rem;">
            <h1 style="color: white; text-align: center; margin: 0;">👥 Mi Área de Trabajo</h1>
            <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 10px 0 0 0;">{area_usuario}</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Calendario", "💬 Comentarios", "📊 Estadísticas", "📤 Exportar"])
        
        empleados_area = session.query(Empleado).filter_by(area=user.area).all()
        turnos = session.query(Turno).all()
        turnos_dict = {t.id: t for t in turnos}
        turnos_nombres = {t.id: t.nombre for t in turnos}
        
        if not empleados_area:
            st.warning(f"⚠️ No hay empleados registrados en el área '{user.area}'")
            st.stop()
        
        # TAB 1: CALENDARIO
        with tab1:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes_index, año_actual = get_mes_actual()
                mes_sel = st.selectbox("Mes", meses, index=mes_index, key="area_mes")
            with col2:
                año_sel = st.number_input("Año", min_value=2024, max_value=2030, value=año_actual, key="area_ano")
            with col3:
                vista = st.radio("Vista", ["📅 Grupal", "👤 Individual"], horizontal=True, key="vista_area")
            
            mes_num = meses.index(mes_sel) + 1
            dias_mes = monthrange(año_sel, mes_num)[1]
            fecha_inicio = date(año_sel, mes_num, 1)
            fecha_fin = date(año_sel, mes_num, dias_mes)
            
            empleados_ids = [e.id for e in empleados_area]
            asignaciones = session.query(Asignacion).filter(
                Asignacion.empleado_id.in_(empleados_ids),
                Asignacion.fecha.between(fecha_inicio, fecha_fin)
            ).all()
            
            turnos_por_empleado_dia = {}
            for a in asignaciones:
                if a.empleado_id not in turnos_por_empleado_dia:
                    turnos_por_empleado_dia[a.empleado_id] = {}
                turnos_por_empleado_dia[a.empleado_id][a.fecha.day] = a.turno
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 Empleados", len(empleados_area))
            with col2:
                st.metric("📊 Total turnos", len(asignaciones))
            with col3:
                emp_con_turnos = len(set([a.empleado_id for a in asignaciones]))
                st.metric("✅ Con turnos", emp_con_turnos)
            with col4:
                prom = round(len(asignaciones) / len(empleados_area), 1) if empleados_area else 0
                st.metric("📈 Promedio", prom)
            
            if vista == "📅 Grupal":
                st.markdown(f"### 📅 Calendario Grupal - {mes_sel} {año_sel}")
                
                st.markdown("""
                <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin: 10px 0;">
                    <span style="margin-right: 20px;">🟢 <strong>Con turno</strong></span>
                    <span style="margin-right: 20px;">⚪ <strong>Descanso</strong></span>
                    <span>📌 <strong>Tú</strong></span>
                </div>
                """, unsafe_allow_html=True)
                
                dias_semana_corto = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
                primer_dia = date(año_sel, mes_num, 1).weekday()
                
                cols = st.columns(7)
                for i, dia in enumerate(dias_semana_corto):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="text-align: center; font-weight: bold; color: #667eea; padding: 10px; 
                                    background: #f0f4ff; border-radius: 8px; margin: 2px;">
                            {dia}
                        </div>
                        """, unsafe_allow_html=True)
                
                dia_actual = 1
                for semana in range(6):
                    cols = st.columns(7)
                    for dia_semana in range(7):
                        with cols[dia_semana]:
                            if semana == 0 and dia_semana < primer_dia:
                                st.markdown("""
                                <div style="padding: 10px; min-height: 120px; background: #f5f5f5; 
                                            border-radius: 10px; opacity: 0.5; text-align: center;
                                            display: flex; align-items: center; justify-content: center;">
                                    <div style="color: #999;">-</div>
                                </div>
                                """, unsafe_allow_html=True)
                            elif dia_actual <= dias_mes:
                                fecha_actual = date(año_sel, mes_num, dia_actual)
                                dias_semana_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                                dia_semana_nombre = dias_semana_nombres[fecha_actual.weekday()]
                                
                                empleados_con_turno = []
                                for emp in empleados_area:
                                    if emp.id in turnos_por_empleado_dia and dia_actual in turnos_por_empleado_dia[emp.id]:
                                        turno = turnos_por_empleado_dia[emp.id][dia_actual]
                                        empleados_con_turno.append((emp, turno))
                                
                                comentarios = obtener_comentarios(user.area, fecha_actual)
                                tiene_comentarios = len(comentarios) > 0
                                
                                if fecha_actual.weekday() >= 5:
                                    bg_color = "#fff3e0"
                                else:
                                    bg_color = "white"
                                
                                html_dia = f"""
                                <div style="background: {bg_color}; border-radius: 10px; padding: 8px; 
                                            min-height: 120px; border: 1px solid #e0e0e0;
                                            {'border: 2px solid #ff6b6b;' if tiene_comentarios else ''}">
                                    <div style="font-weight: bold; text-align: center; 
                                                padding-bottom: 5px; border-bottom: 2px solid #667eea;
                                                display: flex; justify-content: space-between; align-items: center;">
                                        <span>
                                            <span style="font-size: 1.1rem;">{dia_actual}</span>
                                            <span style="color: #999; font-size: 0.7rem; margin-left: 5px;">{dia_semana_nombre[:3]}</span>
                                        </span>
                                        {'<span style="font-size: 1rem;">💬</span>' if tiene_comentarios else ''}
                                    </div>
                                    <div style="margin-top: 5px; max-height: 85px; overflow-y: auto;">
                                """
                                
                                if empleados_con_turno:
                                    for emp, turno in empleados_con_turno[:4]:
                                        es_usuario = emp.id == user.id
                                        bg_color_item = "#e8f5e9" if es_usuario else "#f0f8ff"
                                        border_color = "#4CAF50" if es_usuario else "#667eea"
                                        icono = "📌 " if es_usuario else "👤 "
                                        
                                        html_dia += f"""
                                        <div style="background: {bg_color_item}; padding: 3px 5px; margin: 2px 0; 
                                                    border-radius: 5px; font-size: 0.7rem; 
                                                    border-left: 3px solid {border_color};">
                                            <strong>{icono}{emp.nombre[:10]}{'...' if len(emp.nombre) > 10 else ''}</strong>
                                            <span style="color: #666; margin-left: 3px;">{turno.nombre}</span>
                                        </div>
                                        """
                                    if len(empleados_con_turno) > 4:
                                        html_dia += f"""
                                        <div style="font-size: 0.65rem; color: #999; text-align: center; padding: 2px;">
                                            +{len(empleados_con_turno) - 4} más
                                        </div>
                                        """
                                else:
                                    html_dia += """
                                    <div style="color: #999; text-align: center; padding: 10px; font-size: 0.7rem;">
                                        🟢 Sin turnos
                                    </div>
                                    """
                                
                                html_dia += """
                                    </div>
                                </div>
                                """
                                
                                st.markdown(html_dia, unsafe_allow_html=True)
                                dia_actual += 1
                            else:
                                st.markdown("""
                                <div style="padding: 10px; min-height: 120px; background: #f5f5f5; 
                                            border-radius: 10px; opacity: 0.5; text-align: center;
                                            display: flex; align-items: center; justify-content: center;">
                                    <div style="color: #999;">-</div>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    if dia_actual > dias_mes:
                        break
            
            else:
                empleados_dict = {e.nombre: e for e in empleados_area}
                empleado_sel = st.selectbox("Selecciona un empleado", list(empleados_dict.keys()))
                
                if empleado_sel:
                    emp = empleados_dict[empleado_sel]
                    es_usuario = emp.id == user.id
                    turnos_emp = turnos_por_empleado_dia.get(emp.id, {})
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total turnos", len(turnos_emp))
                    with col2:
                        st.metric("Cargo", emp.cargo or "No asignado")
                    with col3:
                        st.metric("Días trabajados", len(set(turnos_emp.keys())))
                    
                    st.markdown(f"#### 📅 Turnos de {emp.nombre}" + (" (Tú)" if es_usuario else ""))
                    
                    if turnos_emp:
                        data_turnos = []
                        for dia, turno in sorted(turnos_emp.items()):
                            fecha = date(año_sel, mes_num, dia)
                            dias_semana_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                            data_turnos.append({
                                "Fecha": fecha.strftime("%d/%m/%Y"),
                                "Día": dias_semana_nombres[fecha.weekday()],
                                "Turno": turno.nombre,
                                "Horario": f"{turno.inicio} - {turno.fin}"
                            })
                        df_turnos = pd.DataFrame(data_turnos)
                        st.dataframe(df_turnos, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"{emp.nombre} no tiene turnos asignados en {mes_sel} {año_sel}")
        
        # TAB 2: COMENTARIOS
        with tab2:
            st.markdown("### 💬 Chat del Área")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fecha_comentario = st.date_input("Selecciona la fecha", date.today(), key="fecha_comentario")
                comentarios = obtener_comentarios(user.area, fecha_comentario)
                
                st.markdown(f"#### Comentarios para {fecha_comentario.strftime('%d/%m/%Y')}")
                
                if comentarios:
                    for usuario, comentario, fecha_creacion in comentarios:
                        es_mio = usuario == user.nombre
                        bg_color = "#e8f5e9" if es_mio else "#f0f8ff"
                        border_color = "#4CAF50" if es_mio else "#667eea"
                        
                        st.markdown(f"""
                        <div class="comentario-card" style="background: {bg_color}; border-left-color: {border_color};">
                            <div style="display: flex; justify-content: space-between;">
                                <strong style="color: {border_color};">{usuario}</strong>
                                <span style="color: #999; font-size: 0.75rem;">{fecha_creacion}</span>
                            </div>
                            <div style="margin-top: 5px;">{comentario}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No hay comentarios para esta fecha")
                
                st.markdown("---")
                st.markdown("#### ✏️ Nuevo comentario")
                
                with st.form("nuevo_comentario"):
                    nuevo = st.text_area("Escribe tu mensaje", placeholder="Ej: Recordatorio de reunión...", height=100)
                    if st.form_submit_button("📤 Enviar", use_container_width=True):
                        if nuevo:
                            if guardar_comentario(user.area, fecha_comentario, user.nombre, nuevo):
                                st.success("✅ Comentario guardado")
                                st.rerun()
                        else:
                            st.warning("⚠️ Escribe un mensaje")
            
            with col2:
                st.markdown("#### 📌 Sugerencias")
                st.info("""
                **Usa el chat para:**
                - 📅 Coordinar cambios
                - 📝 Dejar notas
                - 🎉 Anunciar eventos
                - ⚠️ Reportar novedades
                """)
        
        # TAB 3: ESTADÍSTICAS
        with tab3:
            st.markdown("### 📊 Estadísticas del Área")
            
            col1, col2 = st.columns(2)
            with col1:
                fecha_ini = st.date_input("Fecha inicio", date.today().replace(day=1), key="stats_ini")
            with col2:
                fecha_fin = st.date_input("Fecha fin", date.today(), key="stats_fin")
            
            asignaciones_stats = session.query(Asignacion).filter(
                Asignacion.empleado_id.in_(empleados_ids),
                Asignacion.fecha.between(fecha_ini, fecha_fin)
            ).all()
            
            if asignaciones_stats:
                stats_emp = {}
                for a in asignaciones_stats:
                    if a.empleado_id not in stats_emp:
                        emp = session.get(Empleado, a.empleado_id)
                        stats_emp[a.empleado_id] = {
                            "nombre": emp.nombre if emp else "Desconocido",
                            "total": 0
                        }
                    stats_emp[a.empleado_id]["total"] += 1
                
                st.markdown("#### 📈 Turnos por empleado")
                data_graf = [{"Empleado": s["nombre"], "Total": s["total"]} for s in stats_emp.values()]
                df_graf = pd.DataFrame(data_graf).sort_values("Total", ascending=False)
                st.bar_chart(df_graf.set_index("Empleado"))
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total turnos", len(asignaciones_stats))
                with col2:
                    st.metric("Empleados activos", f"{len(stats_emp)}/{len(empleados_area)}")
                with col3:
                    if stats_emp:
                        max_t = max([s["total"] for s in stats_emp.values()])
                        emp_max = [s["nombre"] for s in stats_emp.values() if s["total"] == max_t][0]
                        st.metric("Más turnos", f"{emp_max} ({max_t})")
            else:
                st.info("No hay datos en el rango seleccionado")
        
        # TAB 4: EXPORTAR
        with tab4:
            st.markdown("### 📤 Exportar Datos")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📅 Exportar calendario")
                mes_exp = st.selectbox("Mes", meses, index=mes_index, key="exp_mes")
                año_exp = st.number_input("Año", min_value=2024, max_value=2030, value=año_actual, key="exp_ano")
                formato = st.radio("Formato", ["📊 Excel", "📄 PDF"], horizontal=True, key="exp_formato")
                
                if st.button("📥 Exportar calendario", use_container_width=True, type="primary"):
                    mes_num_exp = meses.index(mes_exp) + 1
                    fecha_ini_exp = date(año_exp, mes_num_exp, 1)
                    fecha_fin_exp = date(año_exp, mes_num_exp, monthrange(año_exp, mes_num_exp)[1])
                    
                    asig_exp = session.query(Asignacion).filter(
                        Asignacion.empleado_id.in_(empleados_ids),
                        Asignacion.fecha.between(fecha_ini_exp, fecha_fin_exp)
                    ).all()
                    
                    if formato == "📊 Excel":
                        output = exportar_calendario_area_excel(
                            empleados_area, asig_exp, turnos_nombres, mes_exp, año_exp, user.area
                        )
                        st.download_button(
                            "📥 Descargar Excel", output,
                            f"calendario_{user.area}_{mes_exp}_{año_exp}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        output = exportar_calendario_area_pdf(
                            empleados_area, asig_exp, turnos_nombres, mes_exp, año_exp, user.area
                        )
                        st.download_button(
                            "📥 Descargar PDF", output,
                            f"calendario_{user.area}_{mes_exp}_{año_exp}.pdf",
                            "application/pdf",
                            use_container_width=True
                        )
                    st.success(f"✅ Calendario generado correctamente")
            
            with col2:
                st.markdown("#### 📊 Exportar estadísticas")
                
                if st.button("📈 Generar reporte completo", use_container_width=True):
                    output = BytesIO()
                    
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        data_emp = [{
                            "Nombre": e.nombre, "Cargo": e.cargo or "", 
                            "Usuario": e.usuario, "Rol": e.rol
                        } for e in empleados_area]
                        pd.DataFrame(data_emp).to_excel(writer, sheet_name="Empleados", index=False)
                        
                        inicio_mes = date.today().replace(day=1)
                        asig_mes = session.query(Asignacion).filter(
                            Asignacion.empleado_id.in_(empleados_ids),
                            Asignacion.fecha >= inicio_mes
                        ).all()
                        
                        data_tur = []
                        for a in asig_mes:
                            emp = session.get(Empleado, a.empleado_id)
                            data_tur.append({
                                "Fecha": a.fecha.strftime("%d/%m/%Y"),
                                "Empleado": emp.nombre if emp else "N/A",
                                "Turno": a.turno.nombre if a.turno else "N/A"
                            })
                        pd.DataFrame(data_tur).to_excel(writer, sheet_name="Turnos del mes", index=False)
                    
                    output.seek(0)
                    st.download_button(
                        "📥 Descargar reporte", output,
                        f"reporte_{user.area}_{date.today().strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.success("✅ Reporte generado correctamente")

    # ============ PÁGINA: CALENDARIO ============
    elif op == "Calendario":
        if user.rol not in ["empleado", "supervisor"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📅 Mi Calendario Personal</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_index, año_actual = get_mes_actual()
            mes = st.selectbox("Mes", meses, index=mes_index)
        with col2:
            año = st.number_input("Año", min_value=2024, max_value=2030, value=año_actual)
        
        mes_num = meses.index(mes) + 1
        dias_mes = monthrange(año, mes_num)[1]
        
        mis_turnos = session.query(Asignacion).filter(
            Asignacion.empleado_id == user.id,
            Asignacion.fecha >= date(año, mes_num, 1),
            Asignacion.fecha <= date(año, mes_num, dias_mes)
        ).order_by(Asignacion.fecha).all()
        
        turnos_por_dia = {}
        for t in mis_turnos:
            turnos_por_dia[t.fecha.day] = t
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total turnos", len(mis_turnos))
        with col2:
            dias_trabajados = len(set([t.fecha.day for t in mis_turnos]))
            st.metric("Días trabajados", dias_trabajados)
        with col3:
            st.metric("Días descanso", dias_mes - dias_trabajados)
        
        st.markdown(f"### 📅 {mes} {año}")
        
        dias_semana = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
        dias_semana_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        primer_dia = date(año, mes_num, 1).weekday()
        
        cols = st.columns(7)
        for i, dia in enumerate(dias_semana):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align: center; font-weight: bold; color: #667eea; padding: 10px;
                            background: #f0f4ff; border-radius: 8px;">
                    {dia}
                </div>
                """, unsafe_allow_html=True)
        
        dia_actual = 1
        for semana in range(6):
            cols = st.columns(7)
            for dia_semana in range(7):
                with cols[dia_semana]:
                    if semana == 0 and dia_semana < primer_dia:
                        st.markdown("""
                        <div style="padding: 10px; min-height: 100px; background: #f5f5f5; 
                                    border-radius: 10px; opacity: 0.5; text-align: center;
                                    display: flex; align-items: center; justify-content: center;">
                            <div style="color: #999;">-</div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif dia_actual <= dias_mes:
                        fecha_actual = date(año, mes_num, dia_actual)
                        dia_semana_nombre = dias_semana_nombres[fecha_actual.weekday()]
                        
                        if dia_actual in turnos_por_dia:
                            turno = turnos_por_dia[dia_actual].turno
                            st.markdown(f"""
                            <div style="background: #e8f5e9; border-radius: 10px; padding: 10px; 
                                        min-height: 100px; border: 2px solid #4CAF50;">
                                <div style="font-weight: bold; text-align: center; font-size: 1.1rem;">{dia_actual}</div>
                                <div style="font-size: 0.7rem; color: #666; text-align: center;">{dia_semana_nombre[:3]}</div>
                                <div style="text-align: center; margin-top: 8px;">
                                    <span style="background: #4CAF50; color: white; padding: 3px 8px; 
                                                 border-radius: 20px; font-size: 0.75rem; font-weight: bold;">
                                        {turno.nombre}
                                    </span>
                                </div>
                                <div style="font-size: 0.65rem; text-align: center; color: #666; margin-top: 3px;">
                                    {turno.inicio} - {turno.fin}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            if fecha_actual.weekday() >= 5:
                                bg_color = "#fff3e0"
                            else:
                                bg_color = "#f9f9f9"
                            
                            st.markdown(f"""
                            <div style="background: {bg_color}; border-radius: 10px; padding: 10px; 
                                        min-height: 100px; text-align: center; border: 1px solid #e0e0e0;">
                                <div style="font-weight: bold; font-size: 1.1rem;">{dia_actual}</div>
                                <div style="font-size: 0.7rem; color: #666;">{dia_semana_nombre[:3]}</div>
                                <div style="color: #999; margin-top: 10px; font-size: 0.75rem;">
                                    🟢 Descanso
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        dia_actual += 1
                    else:
                        st.markdown("""
                        <div style="padding: 10px; min-height: 100px; background: #f5f5f5; 
                                    border-radius: 10px; opacity: 0.5; text-align: center;
                                    display: flex; align-items: center; justify-content: center;">
                            <div style="color: #999;">-</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            if dia_actual > dias_mes:
                break
        
        if mis_turnos:
            with st.expander("📋 Ver lista detallada"):
                data = []
                for t in mis_turnos:
                    data.append({
                        "Fecha": t.fecha.strftime("%d/%m/%Y"),
                        "Día": dias_semana_nombres[t.fecha.weekday()],
                        "Turno": t.turno.nombre if t.turno else "N/A",
                        "Horario": f"{t.turno.inicio} - {t.turno.fin}" if t.turno else "N/A"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    # ============ PÁGINA: MI PERFIL ============
    elif op == "Mi perfil":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">👤 Mi Perfil</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <h3>Información Personal</h3>
                <p><strong>Nombre:</strong> {user.nombre}</p>
                <p><strong>Usuario:</strong> {user.usuario}</p>
                <p><strong>Rol:</strong> {user.rol.upper()}</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stats-card">
                <h3>Información Laboral</h3>
                <p><strong>Área:</strong> {user.area if user.area else 'No asignada'}</p>
                <p><strong>Cargo:</strong> {user.cargo if user.cargo else 'No asignado'}</p>
            </div>
            """, unsafe_allow_html=True)
        
        total_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).count()
        st.metric("Total de turnos asignados", total_turnos)

    # ============ PÁGINA: MIS TURNOS ============
    elif op == "Mis turnos":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📊 Mis Turnos</h2>
        </div>
        """, unsafe_allow_html=True)
        
        mis_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).order_by(Asignacion.fecha.desc()).limit(50).all()
        
        if mis_turnos:
            data = []
            for t in mis_turnos:
                data.append({
                    "Fecha": t.fecha.strftime("%d/%m/%Y"),
                    "Turno": t.turno.nombre if t.turno else "N/A",
                    "Horario": f"{t.turno.inicio} - {t.turno.fin}" if t.turno else "N/A"
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info("No tienes turnos asignados")

    # ============ PÁGINA: MI EQUIPO ============
    elif op == "Mi equipo":
        if user.rol not in ["supervisor", "admin"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">👥 Mi Equipo</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if user.rol == "admin":
            areas = list(set([e.area for e in session.query(Empleado).all() if e.area]))
            areas.sort()
            area_sel = st.selectbox("Seleccionar área", areas)
        else:
            area_sel = user.area
        
        empleados = session.query(Empleado).filter_by(area=area_sel).all()
        
        if empleados:
            st.markdown(f"### Área: {area_sel}")
            
            cols = st.columns(3)
            for i, e in enumerate(empleados):
                with cols[i % 3]:
                    turno_hoy = session.query(Asignacion).filter_by(
                        empleado_id=e.id, fecha=date.today()
                    ).first()
                    
                    st.markdown(f"""
                    <div class="empleado-card">
                        <h4>{e.nombre}</h4>
                        <p style="color: #666;">{e.cargo or 'Sin cargo'}</p>
                        <p><strong>Turno hoy:</strong> {turno_hoy.turno.nombre if turno_hoy else 'Sin turno'}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            with st.expander("📋 Ver tabla detallada"):
                data = [{
                    "Nombre": e.nombre,
                    "Cargo": e.cargo or "N/A",
                    "Usuario": e.usuario,
                    "Rol": e.rol
                } for e in empleados]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.info(f"No hay empleados en el área '{area_sel}'")

    # ============ PÁGINA: MATRIZ AREA ============
    elif op == "Matriz area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📊 Matriz de Turnos</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_index, año_actual = get_mes_actual()
            mes = st.selectbox("Mes", meses, index=mes_index)
        with col2:
            año = st.number_input("Año", min_value=2024, max_value=2030, value=año_actual)
        
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

    # ============ PÁGINA: ASIGNAR AREA ============
    elif op == "Asignar area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">✏️ Asignar Turnos</h2>
        </div>
        """, unsafe_allow_html=True)
        
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

    # ============ PÁGINA: REPORTES AREA ============
    elif op == "Reportes area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📈 Reportes del Área</h2>
        </div>
        """, unsafe_allow_html=True)
        
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

    # ============ PÁGINA: OTRAS AREAS ============
    elif op == "Otras areas":
        if user.rol not in ["admin", "supervisor"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">🌐 Vista de Otras Áreas</h2>
        </div>
        """, unsafe_allow_html=True)
        
        areas = list(set([e.area for e in session.query(Empleado).all() if e.area]))
        areas.sort()
        
        if user.rol == "supervisor":
            areas = [user.area]
        
        area_sel = st.selectbox("Selecciona un área", areas)
        
        if area_sel:
            empleados = session.query(Empleado).filter_by(area=area_sel).all()
            
            if empleados:
                st.markdown(f"### Área: {area_sel}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total empleados", len(empleados))
                with col2:
                    turnos_hoy = session.query(Asignacion).filter(
                        Asignacion.empleado_id.in_([e.id for e in empleados]),
                        Asignacion.fecha == date.today()
                    ).count()
                    st.metric("Turnos hoy", turnos_hoy)
                with col3:
                    cargos = len(set([e.cargo for e in empleados if e.cargo]))
                    st.metric("Cargos diferentes", cargos)
                
                data = [{
                    "Nombre": e.nombre,
                    "Cargo": e.cargo or "N/A",
                    "Usuario": e.usuario,
                    "Rol": e.rol
                } for e in empleados]
                
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else:
                st.info(f"No hay empleados en el área {area_sel}")

    # ============ PÁGINA: EMPLEADOS (ADMIN) ============
    elif op == "Empleados":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">👥 Gestión de Empleados</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📋 Lista", "➕ Nuevo", "✏️ Editar"])
        
        with tab1:
            empleados = session.query(Empleado).all()
            if empleados:
                data = [{
                    "ID": e.id, "Nombre": e.nombre, "Área": e.area or "N/A",
                    "Cargo": e.cargo or "N/A", "Usuario": e.usuario, "Rol": e.rol
                } for e in empleados]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else:
                st.info("No hay empleados registrados")
        
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
                seleccion = st.selectbox("Seleccionar empleado", list(opciones.keys()))
                emp_id = opciones[seleccion]
                emp = session.get(Empleado, emp_id)
                
                if emp:
                    with st.form("editar_emp"):
                        nombre = st.text_input("Nombre", value=emp.nombre)
                        usuario = st.text_input("Usuario", value=emp.usuario)
                        col1, col2 = st.columns(2)
                        with col1:
                            area = st.text_input("Área", value=emp.area or "")
                        with col2:
                            cargo = st.text_input("Cargo", value=emp.cargo or "")
                        rol = st.selectbox("Rol", ["empleado", "supervisor", "admin"], 
                                          index=["empleado", "supervisor", "admin"].index(emp.rol))
                        nueva_pass = st.text_input("Nueva contraseña (opcional)", type="password")
                        
                        if st.form_submit_button("💾 Guardar"):
                            emp.nombre = nombre
                            emp.usuario = usuario
                            emp.area = area or None
                            emp.cargo = cargo or None
                            emp.rol = rol
                            if nueva_pass:
                                emp.password = nueva_pass
                            session.commit()
                            st.success("✅ Actualizado")
                            st.rerun()
                    
                    if st.button("🗑️ Eliminar", type="secondary"):
                        if emp.id != user.id:
                            session.delete(emp)
                            session.commit()
                            st.success("✅ Eliminado")
                            st.rerun()
                        else:
                            st.error("❌ No puedes eliminarte a ti mismo")

    # ============ PÁGINA: TURNOS (ADMIN) ============
    elif op == "Turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">⏰ Gestión de Turnos</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📋 Lista", "➕ Nuevo", "✏️ Editar"])
        
        with tab1:
            turnos = session.query(Turno).all()
            if turnos:
                data = [{"ID": t.id, "Nombre": t.nombre, "Inicio": t.inicio, "Fin": t.fin} for t in turnos]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                st.metric("Total turnos", len(turnos))
            else:
                st.info("No hay turnos registrados")
        
        with tab2:
            with st.form("nuevo_turno"):
                n = st.text_input("Nombre *", placeholder="Ej: 151")
                col1, col2 = st.columns(2)
                with col1:
                    hi = st.text_input("Hora inicio *", placeholder="08:00")
                with col2:
                    hf = st.text_input("Hora fin *", placeholder="16:00")
                
                if st.form_submit_button("✅ Crear"):
                    if n and hi and hf:
                        session.add(Turno(nombre=n, inicio=hi, fin=hf))
                        session.commit()
                        st.success("✅ Creado")
                        st.rerun()
        
        with tab3:
            turnos = session.query(Turno).all()
            if turnos:
                opciones = {f"{t.nombre} ({t.inicio}-{t.fin})": t.id for t in turnos}
                seleccion = st.selectbox("Seleccionar turno", list(opciones.keys()))
                turno_id = opciones[seleccion]
                turno = session.get(Turno, turno_id)
                
                if turno:
                    with st.form("editar_turno"):
                        nombre = st.text_input("Nombre", value=turno.nombre)
                        col1, col2 = st.columns(2)
                        with col1:
                            inicio = st.text_input("Hora inicio", value=turno.inicio)
                        with col2:
                            fin = st.text_input("Hora fin", value=turno.fin)
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.form_submit_button("💾 Guardar"):
                                turno.nombre = nombre
                                turno.inicio = inicio
                                turno.fin = fin
                                session.commit()
                                st.success("✅ Actualizado")
                                st.rerun()
                        with col_b:
                            if st.form_submit_button("🗑️ Eliminar"):
                                asignaciones = session.query(Asignacion).filter_by(turno_id=turno.id).first()
                                if asignaciones:
                                    st.warning("⚠️ Este turno tiene asignaciones")
                                else:
                                    session.delete(turno)
                                    session.commit()
                                    st.success("✅ Eliminado")
                                    st.rerun()

    # ============ PÁGINA: MATRIZ TURNOS (ADMIN) ============
    elif op == "Matriz turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📊 Matriz General de Turnos</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_index, año_actual = get_mes_actual()
            mes = st.selectbox("Mes", meses, index=mes_index)
        with col2:
            año = st.number_input("Año", min_value=2024, max_value=2030, value=2026)
        with col3:
            areas = list(set([e.area for e in session.query(Empleado).all() if e.area]))
            areas.sort()
            area_filtro = st.selectbox("Filtrar por área", ["Todas"] + areas)
        
        mes_num = meses.index(mes) + 1
        dias_mes = monthrange(año, mes_num)[1]
        
        empleados = session.query(Empleado).all()
        if area_filtro != "Todas":
            empleados = [e for e in empleados if e.area == area_filtro]
        
        if not empleados:
            st.warning("No hay empleados")
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
            fila = {
                "Empleado": emp.nombre,
                "Área": emp.area or "N/A",
                "Cargo": emp.cargo or "N/A",
            }
            for dia in range(1, dias_mes + 1):
                turno_id = matriz.get(emp.id, {}).get(dia)
                fila[str(dia)] = turnos_dict.get(turno_id, "—") if turno_id else "—"
            data.append(fila)
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=600)
            
            total = sum(1 for emp in matriz for dia in matriz[emp])
            st.metric("Total turnos asignados", total)
            
            if st.button("📥 Exportar a Excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name=f"Matriz {mes} {año}", index=False)
                output.seek(0)
                st.download_button(
                    "📥 Descargar Excel", output,
                    f"matriz_{mes}_{año}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # ============ PÁGINA: ASIGNACION MANUAL (ADMIN) ============
    elif op == "Asignacion manual":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">✏️ Asignación Manual</h2>
        </div>
        """, unsafe_allow_html=True)
        
        empleados = session.query(Empleado).all()
        turnos = session.query(Turno).all()
        
        if not empleados or not turnos:
            st.warning("Faltan empleados o turnos")
            st.stop()
        
        col1, col2 = st.columns(2)
        with col1:
            emp_sel = st.selectbox("Empleado", [e.nombre for e in empleados])
            empleado = next(e for e in empleados if e.nombre == emp_sel)
        with col2:
            turno_sel = st.selectbox("Turno", [t.nombre for t in turnos])
            turno = next(t for t in turnos if t.nombre == turno_sel)
        
        fecha = st.date_input("Fecha", date.today())
        
        if st.button("✅ Asignar", use_container_width=True):
            existe = session.query(Asignacion).filter_by(
                empleado_id=empleado.id, fecha=fecha
            ).first()
            
            if existe:
                existe.turno_id = turno.id
            else:
                session.add(Asignacion(empleado_id=empleado.id, fecha=fecha, turno_id=turno.id))
            
            session.commit()
            st.success("✅ Asignado")
            st.rerun()

    # ============ PÁGINA: GENERAR MALLA (ADMIN) ============
    elif op == "Generar malla":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">🤖 Generar Malla Automática</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Función en desarrollo - Generación automática de turnos")

    # ============ PÁGINA: REPORTES (ADMIN) ============
    elif op == "Reportes":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📊 Reportes Generales</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Función en desarrollo - Reportes avanzados")

    # ============ PÁGINA: BACKUP (ADMIN) ============
    elif op == "Backup":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">🛡 Backup y Restauración</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📤 Exportar", "📥 Importar"])
        
        with tab1:
            st.markdown("### Exportar base de datos")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Generar backup automático", use_container_width=True):
                    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre = f"backup_{fecha}.db"
                    
                    shutil.copy("data.db", nombre)
                    
                    with open(nombre, "rb") as f:
                        st.download_button(
                            "📥 Descargar backup", f, nombre,
                            "application/octet-stream", use_container_width=True
                        )
                    
                    os.remove(nombre)
                    st.success("✅ Backup generado")
            
            with col2:
                nombre_personalizado = st.text_input("Nombre del archivo", placeholder="ej: backup_enero")
                
                if st.button("📝 Generar backup personalizado", use_container_width=True):
                    if nombre_personalizado:
                        nombre_limpio = "".join(c for c in nombre_personalizado if c.isalnum() or c in [' ', '-', '_']).strip()
                        nombre_limpio = nombre_limpio.replace(' ', '_')
                        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre = f"{nombre_limpio}_{fecha}.db"
                        
                        shutil.copy("data.db", nombre)
                        
                        with open(nombre, "rb") as f:
                            st.download_button(
                                "📥 Descargar backup", f, nombre,
                                "application/octet-stream", use_container_width=True
                            )
                        
                        os.remove(nombre)
                        st.success("✅ Backup generado")
        
        with tab2:
            st.markdown("### Importar base de datos")
            st.warning("⚠️ Al importar un backup, se sobrescribirá la base de datos actual")
            
            archivo = st.file_uploader("Seleccionar archivo de backup", type=['db'])
            
            if archivo:
                st.info(f"**Archivo:** {archivo.name}")
                
                confirmar = st.checkbox("Confirmo que quiero restaurar este backup")
                
                if st.button("♻️ Restaurar backup", type="primary", disabled=not confirmar):
                    try:
                        fecha_ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
                        os.makedirs("data/backups", exist_ok=True)
                        backup_seguridad = f"data/backups/ANTES_RESTAURAR_{fecha_ahora}.db"
                        
                        if os.path.exists("data.db"):
                            shutil.copy("data.db", backup_seguridad)
                            st.info(f"✅ Backup de seguridad creado")
                        
                        with open("data.db", "wb") as f:
                            f.write(archivo.getbuffer())
                        
                        st.success("✅ Base de datos restaurada")
                        st.warning("🔄 Recarga la página para aplicar los cambios")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

else:
    login()