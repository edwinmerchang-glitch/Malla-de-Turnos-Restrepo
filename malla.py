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
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
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
        st.error(f"Error inicializando tabla de comentarios: {e}")

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
        st.error(f"Error guardando comentario: {e}")
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
            return comentarios
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
    
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
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
    for dia in range(1, min(dias_mes + 1, 16)):  # Limitamos a 15 días para que quepa en PDF horizontal
        fecha = date(año, mes_num, dia)
        header.append(f"{dia}\n{fecha.strftime('%a')}")
    table_data.append(header)
    
    for emp in empleados[:15]:  # Limitamos empleados para el PDF
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
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
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
            margin-bottom: 0.5rem;
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
            transition: all 0.3s !important;
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
                <p>© 2026 Edwin Merchán - Versión 2.0</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============ CONTENIDO PRINCIPAL ============
if "user" in st.session_state:
    user = st.session_state["user"]
    
    # Verificar notificaciones
    notificaciones = 0
    if user.area:
        notificaciones = verificar_notificaciones_area(user.area)
    
    # ============ ESTILOS GENERALES ============
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
        .notificacion-badge {
            background: #ff6b6b;
            color: white;
            border-radius: 20px;
            padding: 3px 10px;
            font-size: 0.8rem;
            margin-left: 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ============ SIDEBAR ============
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
                🔔 {notificaciones} notificaciones nuevas
            </div>
            """, unsafe_allow_html=True)
        
        # Inicializar página actual
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
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👥 Mi área", use_container_width=True):
                    cambiar_pagina("Mi area")
                if st.button("📅 Mi calendario", use_container_width=True):
                    cambiar_pagina("Calendario")
            with col2:
                if st.button("📊 Mis turnos", use_container_width=True):
                    cambiar_pagina("Mis turnos")
                if st.button("👤 Mi perfil", use_container_width=True):
                    cambiar_pagina("Mi perfil")
        
        elif user.rol == "supervisor":
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👥 Mi equipo", use_container_width=True):
                    cambiar_pagina("Mi equipo")
                if st.button("📊 Matriz área", use_container_width=True):
                    cambiar_pagina("Matriz area")
                if st.button("✏️ Asignar", use_container_width=True):
                    cambiar_pagina("Asignar area")
            with col2:
                if st.button("📈 Reportes", use_container_width=True):
                    cambiar_pagina("Reportes area")
                if st.button("🌐 Otras áreas", use_container_width=True):
                    cambiar_pagina("Otras areas")
                if st.button("👤 Mi perfil", use_container_width=True):
                    cambiar_pagina("Mi perfil")
        
        elif user.rol == "admin":
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👥 Empleados", use_container_width=True):
                    cambiar_pagina("Empleados")
                if st.button("⏰ Turnos", use_container_width=True):
                    cambiar_pagina("Turnos")
                if st.button("📊 Matriz", use_container_width=True):
                    cambiar_pagina("Matriz turnos")
                if st.button("✏️ Asignar", use_container_width=True):
                    cambiar_pagina("Asignacion manual")
            with col2:
                if st.button("🤖 Generar", use_container_width=True):
                    cambiar_pagina("Generar malla")
                if st.button("📈 Reportes", use_container_width=True):
                    cambiar_pagina("Reportes")
                if st.button("🛡 Backup", use_container_width=True):
                    cambiar_pagina("Backup")
                if st.button("🌐 Áreas", use_container_width=True):
                    cambiar_pagina("Otras areas")
        
        st.markdown("---")
        st.markdown(f"📍 **Página actual:** {st.session_state.pagina_actual}")
        
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #999; font-size: 0.8rem;">
            © 2026 Edwin Merchán<br>Versión 2.0
        </div>
        """, unsafe_allow_html=True)
    
    # ============ CONTENIDO PRINCIPAL ============
    op = st.session_state.pagina_actual
    
    # ============ PÁGINA: MI ÁREA (NUEVA FUNCIONALIDAD PRINCIPAL) ============
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
        
        # Tabs para organizar funcionalidades
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Calendario", "💬 Comentarios", "📊 Estadísticas", "📤 Exportar"])
        
        # Obtener datos del área
        empleados_area = session.query(Empleado).filter_by(area=user.area).all()
        turnos = session.query(Turno).all()
        turnos_dict = {t.id: t for t in turnos}
        turnos_nombres = {t.id: t.nombre for t in turnos}
        
        if not empleados_area:
            st.warning(f"⚠️ No hay empleados registrados en el área '{user.area}'")
            st.stop()
        
        # ============ TAB 1: CALENDARIO DEL ÁREA ============
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
            
            # Organizar turnos por empleado y día
            turnos_por_empleado_dia = {}
            for a in asignaciones:
                if a.empleado_id not in turnos_por_empleado_dia:
                    turnos_por_empleado_dia[a.empleado_id] = {}
                turnos_por_empleado_dia[a.empleado_id][a.fecha.day] = a.turno
            
            # Estadísticas rápidas
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
                
                # Leyenda
                st.markdown("""
                <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin: 10px 0;">
                    <span style="margin-right: 20px;">🟢 <strong>Con turno</strong></span>
                    <span style="margin-right: 20px;">⚪ <strong>Descanso</strong></span>
                    <span>📌 <strong>Tú</strong></span>
                </div>
                """, unsafe_allow_html=True)
                
                dias_semana = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
                primer_dia = date(año_sel, mes_num, 1).weekday()
                
                # Cabecera de días
                cols = st.columns(7)
                for i, dia in enumerate(dias_semana):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="text-align: center; font-weight: bold; color: #667eea; padding: 10px;">
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
                                <div style="padding: 10px; min-height: 120px; background: #f9f9f9; 
                                            border-radius: 10px; opacity: 0.5; text-align: center;">
                                    <div style="color: #ccc;">-</div>
                                </div>
                                """, unsafe_allow_html=True)
                            elif dia_actual <= dias_mes:
                                fecha_actual = date(año_sel, mes_num, dia_actual)
                                dia_semana_nombre = fecha_actual.strftime("%a").upper()
                                
                                empleados_con_turno = []
                                for emp in empleados_area:
                                    if emp.id in turnos_por_empleado_dia and dia_actual in turnos_por_empleado_dia[emp.id]:
                                        turno = turnos_por_empleado_dia[emp.id][dia_actual]
                                        empleados_con_turno.append((emp, turno))
                                
                                # Verificar comentarios
                                comentarios = obtener_comentarios(user.area, fecha_actual)
                                tiene_comentarios = len(comentarios) > 0
                                
                                html_dia = f"""
                                <div style="background: white; border-radius: 10px; padding: 8px; 
                                            min-height: 120px; border: 1px solid #e0e0e0;
                                            {'border: 2px solid #ff6b6b;' if tiene_comentarios else ''}">
                                    <div style="font-weight: bold; text-align: center; 
                                                padding-bottom: 5px; border-bottom: 2px solid #667eea;
                                                display: flex; justify-content: space-between;">
                                        <span>{dia_actual} <span style="color: #999; font-size: 0.8rem;">{dia_semana_nombre}</span></span>
                                        {'<span>💬</span>' if tiene_comentarios else ''}
                                    </div>
                                    <div style="margin-top: 5px; max-height: 85px; overflow-y: auto;">
                                """
                                
                                if empleados_con_turno:
                                    for emp, turno in empleados_con_turno[:4]:
                                        es_usuario = "📌 " if emp.id == user.id else ""
                                        bg_color = "#e8f5e9" if emp.id == user.id else "#f0f8ff"
                                        border_color = "#4CAF50" if emp.id == user.id else "#667eea"
                                        
                                        html_dia += f"""
                                        <div style="background: {bg_color}; padding: 2px 5px; margin: 2px 0; 
                                                    border-radius: 5px; font-size: 0.7rem; 
                                                    border-left: 3px solid {border_color};">
                                            <strong>{es_usuario}{emp.nombre[:10]}...</strong> {turno.nombre}
                                        </div>
                                        """
                                    if len(empleados_con_turno) > 4:
                                        html_dia += f"""
                                        <div style="font-size: 0.7rem; color: #999; text-align: center;">
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
                                <div style="padding: 10px; min-height: 120px; background: #f9f9f9; 
                                            border-radius: 10px; opacity: 0.5; text-align: center;">
                                    <div style="color: #ccc;">-</div>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    if dia_actual > dias_mes:
                        break
            
            else:  # Vista Individual
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
                    
                    # Tabla de turnos
                    if turnos_emp:
                        data_turnos = []
                        for dia, turno in sorted(turnos_emp.items()):
                            fecha = date(año_sel, mes_num, dia)
                            data_turnos.append({
                                "Fecha": fecha.strftime("%d/%m/%Y"),
                                "Día": fecha.strftime("%A"),
                                "Turno": turno.nombre,
                                "Horario": f"{turno.inicio} - {turno.fin}"
                            })
                        df_turnos = pd.DataFrame(data_turnos)
                        st.dataframe(df_turnos, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"{emp.nombre} no tiene turnos asignados en {mes_sel} {año_sel}")
        
        # ============ TAB 2: COMENTARIOS ============
        with tab2:
            st.markdown("### 💬 Chat del Área")
            st.markdown("Coordina con tu equipo, deja notas o comparte información importante")
            
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
                - 📅 Coordinar cambios de turno
                - 📝 Dejar notas importantes
                - 🎉 Anunciar eventos
                - ⚠️ Reportar novedades
                """)
                
                st.markdown("#### 📊 Actividad reciente")
                try:
                    engine = create_engine("sqlite:///data.db")
                    with engine.connect() as conn:
                        result = conn.execute(text("""
                            SELECT usuario, COUNT(*) as total 
                            FROM comentarios_area 
                            WHERE area = :area 
                            GROUP BY usuario 
                            ORDER BY total DESC 
                            LIMIT 5
                        """), {"area": user.area})
                        top = result.fetchall()
                    
                    if top:
                        st.markdown("**Top contribuidores:**")
                        for usuario, total in top:
                            st.write(f"• {usuario}: {total} comentarios")
                except:
                    pass
        
        # ============ TAB 3: ESTADÍSTICAS ============
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
                # Estadísticas por empleado
                stats_emp = {}
                for a in asignaciones_stats:
                    if a.empleado_id not in stats_emp:
                        emp = session.get(Empleado, a.empleado_id)
                        stats_emp[a.empleado_id] = {
                            "nombre": emp.nombre if emp else "Desconocido",
                            "total": 0,
                            "turnos": {}
                        }
                    stats_emp[a.empleado_id]["total"] += 1
                    if a.turno:
                        stats_emp[a.empleado_id]["turnos"][a.turno.nombre] = \
                            stats_emp[a.empleado_id]["turnos"].get(a.turno.nombre, 0) + 1
                
                st.markdown("#### 📈 Turnos por empleado")
                data_graf = [{"Empleado": s["nombre"], "Total": s["total"]} for s in stats_emp.values()]
                df_graf = pd.DataFrame(data_graf).sort_values("Total", ascending=False)
                st.bar_chart(df_graf.set_index("Empleado"))
                
                st.markdown("#### 📋 Detalle por empleado")
                for emp_id, stats in stats_emp.items():
                    with st.expander(f"📌 {stats['nombre']} - {stats['total']} turnos"):
                        if stats["turnos"]:
                            for turno, cant in stats["turnos"].items():
                                st.write(f"• {turno}: {cant} veces")
                        
                        dias_trab = len(set([a.fecha for a in asignaciones_stats if a.empleado_id == emp_id]))
                        st.write(f"• Días trabajados: {dias_trab}")
                
                # Resumen general
                st.markdown("---")
                st.markdown("#### 📊 Resumen general")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total turnos", len(asignaciones_stats))
                with col2:
                    st.metric("Empleados activos", f"{len(stats_emp)}/{len(empleados_area)}")
                with col3:
                    if stats_emp:
                        max_t = max([s["total"] for s in stats_emp.values()])
                        emp_max = [s["nombre"] for s in stats_emp.values() if s["total"] == max_t][0]
                        st.metric("Más turnos", f"{emp_max} ({max_t})")
                with col4:
                    turnos_count = {}
                    for a in asignaciones_stats:
                        if a.turno:
                            turnos_count[a.turno.nombre] = turnos_count.get(a.turno.nombre, 0) + 1
                    if turnos_count:
                        turno_comun = max(turnos_count, key=turnos_count.get)
                        st.metric("Turno más común", turno_comun)
            else:
                st.info("No hay datos en el rango seleccionado")
        
        # ============ TAB 4: EXPORTAR ============
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
                        # Empleados
                        data_emp = [{
                            "Nombre": e.nombre, "Cargo": e.cargo or "", 
                            "Usuario": e.usuario, "Rol": e.rol
                        } for e in empleados_area]
                        pd.DataFrame(data_emp).to_excel(writer, sheet_name="Empleados", index=False)
                        
                        # Turnos del mes
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
    
    # ============ OTRAS PÁGINAS (SIMPLIFICADAS) ============
    elif op == "Calendario":
        st.subheader("📅 Mi Calendario")
        
        if user.rol not in ["empleado", "supervisor"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
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
        
        if mis_turnos:
            data = []
            for t in mis_turnos:
                data.append({
                    "Fecha": t.fecha.strftime("%d/%m/%Y"),
                    "Día": t.fecha.strftime("%A"),
                    "Turno": t.turno.nombre if t.turno else "N/A",
                    "Horario": f"{t.turno.inicio} - {t.turno.fin}" if t.turno else "N/A"
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
            st.metric("Total turnos", len(mis_turnos))
        else:
            st.info(f"No tienes turnos en {mes} {año}")
    
    elif op == "Mi perfil":
        st.subheader(f"👤 Perfil de {user.nombre}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **Nombre:** {user.nombre}  
            **Usuario:** {user.usuario}  
            **Rol:** {user.rol.upper()}
            """)
        with col2:
            st.markdown(f"""
            **Área:** {user.area if user.area else 'No asignada'}  
            **Cargo:** {user.cargo if user.cargo else 'No asignado'}
            """)
        
        total_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).count()
        st.metric("Total de turnos asignados", total_turnos)
    
    elif op == "Mis turnos":
        st.subheader("📊 Mis turnos")
        st.info("Esta sección muestra el listado detallado de tus turnos")
        
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
    
    elif op == "Mi equipo":
        if user.rol not in ["supervisor", "admin"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
        area_sel = user.area if user.rol == "supervisor" else st.selectbox(
            "Área", list(set([e.area for e in session.query(Empleado).all() if e.area]))
        )
        
        st.subheader(f"👥 Mi Equipo - {area_sel}")
        
        empleados = session.query(Empleado).filter_by(area=area_sel).all()
        
        if empleados:
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
        else:
            st.info(f"No hay empleados en el área {area_sel}")
    
    elif op == "Matriz area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader(f"📊 Matriz de turnos - {user.area}")
        st.info("Matriz de turnos del área")
    
    elif op == "Asignar area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader(f"✏️ Asignar turnos - {user.area}")
        st.info("Asignación de turnos para el área")
    
    elif op == "Reportes area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader(f"📈 Reportes - {user.area}")
        st.info("Reportes del área")
    
    elif op == "Otras areas":
        if user.rol not in ["admin", "supervisor"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("🌐 Vista de Otras Áreas")
        
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
    
    elif op == "Empleados":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("👥 Gestión de Empleados")
        
        empleados = session.query(Empleado).all()
        if empleados:
            data = [{
                "ID": e.id, "Nombre": e.nombre, "Área": e.area or "N/A",
                "Cargo": e.cargo or "N/A", "Usuario": e.usuario, "Rol": e.rol
            } for e in empleados]
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        
        with st.expander("➕ Nuevo empleado"):
            with st.form("nuevo_emp"):
                col1, col2 = st.columns(2)
                with col1:
                    nombre = st.text_input("Nombre *")
                    usuario = st.text_input("Usuario *")
                    rol = st.selectbox("Rol *", ["empleado", "supervisor", "admin"])
                with col2:
                    area = st.text_input("Área")
                    cargo = st.text_input("Cargo")
                    password = st.text_input("Contraseña *", type="password")
                
                if st.form_submit_button("✅ Crear"):
                    if nombre and usuario and password:
                        session.add(Empleado(
                            nombre=nombre, usuario=usuario, password=password,
                            rol=rol, area=area or None, cargo=cargo or None
                        ))
                        session.commit()
                        st.success("✅ Empleado creado")
                        st.rerun()
    
    elif op == "Turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("⏰ Gestión de Turnos")
        
        turnos = session.query(Turno).all()
        if turnos:
            data = [{"ID": t.id, "Nombre": t.nombre, "Inicio": t.inicio, "Fin": t.fin} for t in turnos]
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        
        with st.expander("➕ Nuevo turno"):
            with st.form("nuevo_turno"):
                nombre = st.text_input("Nombre *")
                col1, col2 = st.columns(2)
                with col1:
                    inicio = st.text_input("Hora inicio *", placeholder="08:00")
                with col2:
                    fin = st.text_input("Hora fin *", placeholder="16:00")
                
                if st.form_submit_button("✅ Crear"):
                    if nombre and inicio and fin:
                        session.add(Turno(nombre=nombre, inicio=inicio, fin=fin))
                        session.commit()
                        st.success("✅ Turno creado")
                        st.rerun()
    
    elif op == "Matriz turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("📊 Matriz general de turnos")
        st.info("Matriz completa de turnos")
    
    elif op == "Asignacion manual":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("✏️ Asignación manual")
        st.info("Asignación manual de turnos")
    
    elif op == "Generar malla":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("🤖 Generar malla automática")
        st.info("Generación automática de turnos")
    
    elif op == "Reportes":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("📊 Reportes generales")
        st.info("Reportes del sistema")
    
    elif op == "Backup":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.subheader("🛡 Backup y Restauración")
        
        if st.button("🔄 Generar backup"):
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

else:
    login()