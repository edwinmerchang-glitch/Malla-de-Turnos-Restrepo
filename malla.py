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
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from sqlalchemy import create_engine, text

# ============ FUNCIONES AUXILIARES ============

def get_mes_actual():
    hoy = datetime.now()
    return hoy.month - 1, hoy.year

def inicializar_tabla_comentarios():
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
    except:
        pass

def guardar_comentario(area, fecha, usuario, comentario):
    try:
        engine = create_engine("sqlite:///data.db")
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO comentarios_area (area, fecha, usuario, comentario)
                VALUES (:area, :fecha, :usuario, :comentario)
            """), {"area": area, "fecha": fecha, "usuario": usuario, "comentario": comentario})
            conn.commit()
        return True
    except:
        return False

def obtener_comentarios(area, fecha):
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
    except:
        return []

def verificar_notificaciones_area(area):
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
        'bold': True, 'bg_color': '#667eea', 'font_color': 'white',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True
    })
    descanso_format = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#f0f0f0'
    })
    turno_format = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#e8f5e9'
    })
    cell_format = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter'
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
    meses_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
        "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
        "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
    }
    mes_num = meses_dict[mes]
    dias_mes = monthrange(año, mes_num)[1]
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           rightMargin=0.5*cm, leftMargin=0.5*cm, 
                           topMargin=1.5*cm, bottomMargin=1*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=14,
        textColor=colors.HexColor('#667eea'), alignment=TA_CENTER, spaceAfter=15
    )
    
    elements = []
    title = Paragraph(f"Calendario de Turnos - {area}<br/>{mes} {año}", title_style)
    elements.append(title)
    
    mitad = 15
    partes = []
    for parte_inicio in range(1, dias_mes + 1, mitad):
        parte_fin = min(parte_inicio + mitad - 1, dias_mes)
        partes.append((parte_inicio, parte_fin))
    
    for idx, (parte_inicio, parte_fin) in enumerate(partes):
        table_data = []
        header = ["Empleado"]
        for dia in range(parte_inicio, parte_fin + 1):
            fecha = date(año, mes_num, dia)
            dias_sem = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
            header.append(f"{dia}\n{dias_sem[fecha.weekday()]}")
        table_data.append(header)
        
        for emp in empleados[:20]:
            nombre_corto = emp.nombre[:10] + "..." if len(emp.nombre) > 10 else emp.nombre
            row = [nombre_corto]
            for dia in range(parte_inicio, parte_fin + 1):
                turno_encontrado = None
                for a in asignaciones:
                    if a.empleado_id == emp.id and a.fecha.day == dia:
                        turno_encontrado = turnos_dict.get(a.turno_id, "?")
                        break
                if turno_encontrado:
                    if len(turno_encontrado) > 4:
                        turno_encontrado = turno_encontrado[:3] + "."
                else:
                    turno_encontrado = "D"
                row.append(turno_encontrado)
            table_data.append(row)
        
        col_widths = [2.5*cm] + [0.9*cm] * (parte_fin - parte_inicio + 1)
        table = Table(table_data, repeatRows=1, colWidths=col_widths)
        
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ])
        
        for dia in range(parte_inicio, parte_fin + 1):
            fecha = date(año, mes_num, dia)
            if fecha.weekday() >= 5:
                col_idx = dia - parte_inicio + 1
                style.add('BACKGROUND', (col_idx, 1), (col_idx, -1), colors.HexColor('#fff3e0'))
        
        table.setStyle(style)
        elements.append(table)
        
        if idx < len(partes) - 1:
            elements.append(Spacer(1, 0.5*cm))
    
    elements.append(Spacer(1, 0.8*cm))
    total_turnos = len([a for a in asignaciones if a.turno_id])
    empleados_con_turno = len(set([a.empleado_id for a in asignaciones if a.turno_id]))
    stats_text = f"""
    <b>Estadisticas del mes:</b><br/>
    • Total empleados: {len(empleados)}<br/>
    • Con turnos: {empleados_con_turno}<br/>
    • Total turnos: {total_turnos}<br/>
    • Promedio: {round(total_turnos/len(empleados), 1) if empleados else 0}
    """
    stats_para = Paragraph(stats_text, styles['Normal'])
    elements.append(stats_para)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============ CONFIGURACIÓN DE PÁGINA ============
st.set_page_config("Malla de Turnos", layout="wide")

session = Session()
inicializar_tabla_comentarios()

# ============ LOGIN ============
def login():
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px; margin: 0 auto; padding: 2rem;
            background: white; border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .login-header { text-align: center; margin-bottom: 2rem; }
        .login-header h1 {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 2.5rem; font-weight: bold;
        }
        .login-icon { font-size: 4rem; text-align: center; margin-bottom: 1rem; }
        .stButton button {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%) !important;
            color: white !important; border: none !important;
            border-radius: 12px !important; padding: 0.8rem !important;
            font-size: 1.1rem !important; font-weight: 600 !important; width: 100% !important;
        }
        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 20px rgba(46, 204, 113, 0.4) !important;
        }
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <div class="login-icon">📅</div>
                <h1>Malla de Turnos</h1>
                <p>Gestion de Horarios Locatel Restrepo</p>
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
                <p>© 2026 Edwin Merchan - Version 3.0</p>
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
            color: white !important; border: none !important;
            border-radius: 10px !important; padding: 0.8rem !important;
            font-size: 1rem !important; font-weight: 500 !important;
            transition: all 0.3s !important;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3) !important;
        }
        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 15px rgba(76, 175, 80, 0.4) !important;
            background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%) !important;
        }
        .empleado-card {
            background: white; border-radius: 15px; padding: 1.5rem;
            margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .empleado-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
        }
        .comentario-card {
            background: #f8f9fa; border-radius: 10px; padding: 10px;
            margin: 5px 0; border-left: 4px solid #667eea;
        }
        .stats-card {
            background: white; padding: 1.5rem; border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
        }
        .calendario-cabecera {
            display: grid; grid-template-columns: repeat(7, 1fr);
            gap: 6px; margin-bottom: 8px;
        }
        .cabecera-dia {
            background: linear-gradient(135deg, #5f9cff 0%, #7b61ff 100%);
            color: white; padding: 12px; text-align: center;
            font-weight: 700; border-radius: 10px; font-size: 0.9rem;
        }
        .semana-fila {
            display: grid; grid-template-columns: repeat(7, 1fr);
            gap: 6px; margin-bottom: 6px;
        }
        .dia-celda {
            background: white; border-radius: 12px; padding: 8px;
            min-height: 140px; border: 1px solid #eee;
        }
        .dia-celda.fin-semana { background: #faf9f6; }
        .dia-cabecera {
            display: flex; justify-content: space-between;
            border-bottom: 1px solid #eee; margin-bottom: 6px;
        }
        .dia-numero { font-size: 1.2rem; font-weight: bold; }
        .dia-semana { font-size: 0.7rem; color: #888; }
        .turno-mini {
            font-size: 0.65rem; padding: 4px; margin-bottom: 3px;
            border-radius: 6px; background: #f4f6fb;
            border-left: 3px solid #5f9cff;
        }
        .turno-mini.usuario {
            background: #d4fc79; font-weight: 700;
        }
        .turno-mini .nombre { font-weight: 600; }
        .turno-mini .horario { font-size: 0.6rem; color: #666; }
        .contador { font-size: 0.6rem; color: #999; text-align: right; }
        .sin-turnos {
            text-align: center; font-size: 0.7rem; color: #bbb;
            margin-top: 20px;
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
                <div>🏢 {user.area if user.area else 'Sin area'}</div>
                <div>📌 {user.cargo if user.cargo else 'Sin cargo'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if notificaciones > 0:
            st.markdown(f"""
            <div style="background: #ff6b6b; color: white; padding: 10px; 
                        border-radius: 10px; margin: 10px 0; text-align: center;">
                🔔 {notificaciones} notificaciones nuevas en tu area
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
        
        st.markdown("### 📋 Menu")
        
        if user.rol == "empleado":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("👥 Mi area", use_container_width=True):
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
                if st.button("📊 Matriz area", use_container_width=True):
                    cambiar_pagina("Matriz area")
                if st.button("👤 Mi perfil", use_container_width=True):
                    cambiar_pagina("Mi perfil")
            with col2:
                if st.button("✏️ Asignar", use_container_width=True):
                    cambiar_pagina("Asignar area")
                if st.button("📈 Reportes", use_container_width=True):
                    cambiar_pagina("Reportes area")
                if st.button("🌐 Otras areas", use_container_width=True):
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
        st.markdown(f"📍 **Pagina actual:** {st.session_state.pagina_actual}")
        
        if st.button("🚪 Cerrar sesion", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #999; font-size: 0.8rem;">
            © 2026 Edwin Merchan<br>Version 3.0
        </div>
        """, unsafe_allow_html=True)
    
    op = st.session_state.pagina_actual
    
    # ============ PAGINA: MI AREA ============
    if op == "Mi area":
        if user.rol not in ["empleado", "supervisor"]:
            st.error("❌ No tienes permiso para acceder a esta seccion")
            st.stop()
        
        area_usuario = user.area if user.area else "Sin area asignada"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 20px; margin-bottom: 2rem;">
            <h1 style="color: white; text-align: center; margin: 0;">👥 Mi Area de Trabajo</h1>
            <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 10px 0 0 0;">{area_usuario}</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Calendario", "💬 Comentarios", "📊 Estadisticas", "📤 Exportar"])
        
        empleados_area = session.query(Empleado).filter_by(area=user.area).all()
        turnos = session.query(Turno).all()
        turnos_dict = {t.id: t for t in turnos}
        turnos_nombres = {t.id: t.nombre for t in turnos}
        
        if not empleados_area:
            st.warning(f"⚠️ No hay empleados registrados en el area '{user.area}'")
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

                # Cabecera con nombres de días
                dias_semana = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
                dias_semana_corto = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                
                cols_header = st.columns(7)
                for i, dia in enumerate(dias_semana):
                    with cols_header[i]:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    color: white; padding: 10px 5px; text-align: center; 
                                    font-weight: bold; border-radius: 10px; font-size: 0.85rem;">
                            {dia}
                        </div>
                        """, unsafe_allow_html=True)

                # Preparar datos del mes
                primer_dia_semana = date(año_sel, mes_num, 1).weekday()
                
                # Crear matriz de días
                calendario = []
                semana = []
                dia_actual = 1
                
                for i in range(7):
                    if i < primer_dia_semana:
                        semana.append(None)
                    else:
                        semana.append(dia_actual)
                        dia_actual += 1
                calendario.append(semana)
                
                while dia_actual <= dias_mes:
                    semana = []
                    for i in range(7):
                        if dia_actual <= dias_mes:
                            semana.append(dia_actual)
                            dia_actual += 1
                        else:
                            semana.append(None)
                    calendario.append(semana)

                # Mostrar cada semana
                for semana in calendario:
                    cols = st.columns(7)
                    
                    for i, dia_num in enumerate(semana):
                        with cols[i]:
                            if dia_num is None:
                                # Celda vacía
                                with st.container():
                                    st.markdown("<br>", unsafe_allow_html=True)
                                continue
                            
                            fecha_actual = date(año_sel, mes_num, dia_num)
                            dia_nombre = dias_semana_corto[fecha_actual.weekday()]
                            
                            # Obtener empleados con turno este día
                            empleados_con_turno = []
                            for emp in empleados_area:
                                if emp.id in turnos_por_empleado_dia and dia_num in turnos_por_empleado_dia[emp.id]:
                                    turno = turnos_por_empleado_dia[emp.id][dia_num]
                                    empleados_con_turno.append((emp, turno))
                            
                            empleados_con_turno.sort(key=lambda x: (x[0].id != user.id, x[0].nombre))
                            
                            # Crear un expander o contenedor para cada día
                            with st.container():
                                # Cabecera del día
                                bg_color = "#fff3e0" if fecha_actual.weekday() >= 5 else "#f8f9fc"
                                
                                st.markdown(f"""
                                <div style="background: {bg_color}; border-radius: 10px 10px 0 0; 
                                            padding: 8px; border: 1px solid #e0e0e0; border-bottom: none;">
                                    <span style="font-weight: bold; font-size: 1.1rem;">{dia_num}</span>
                                    <span style="font-size: 0.7rem; color: #888; margin-left: 8px;">{dia_nombre}</span>
                                    <span style="float: right; font-size: 0.7rem; color: #666;">
                                        {len(empleados_con_turno)} turnos
                                    </span>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Lista de turnos
                                if empleados_con_turno:
                                    for emp, turno in empleados_con_turno[:8]:
                                        es_usuario = emp.id == user.id
                                        
                                        if es_usuario:
                                            st.markdown(f"""
                                            <div style="background: #e8f5e9; padding: 6px 8px; 
                                                        border-left: 4px solid #2e7d32; border-bottom: 1px solid #e0e0e0;
                                                        border-right: 1px solid #e0e0e0;">
                                                <span style="font-weight: bold;">⭐ {emp.nombre}</span><br>
                                                <span style="background: #c8e6c9; padding: 2px 8px; border-radius: 12px; 
                                                             font-size: 0.7rem; font-weight: bold;">{turno.nombre}</span>
                                                <span style="font-size: 0.65rem; color: #666; margin-left: 8px;">
                                                    🕒 {turno.inicio[:5]} - {turno.fin[:5]}
                                                </span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"""
                                            <div style="background: white; padding: 6px 8px; 
                                                        border-left: 4px solid #4CAF50; border-bottom: 1px solid #e0e0e0;
                                                        border-right: 1px solid #e0e0e0;">
                                                <span>👤 {emp.nombre}</span><br>
                                                <span style="background: #e0e7ff; padding: 2px 8px; border-radius: 12px; 
                                                             font-size: 0.7rem; font-weight: bold;">{turno.nombre}</span>
                                                <span style="font-size: 0.65rem; color: #666; margin-left: 8px;">
                                                    🕒 {turno.inicio[:5]} - {turno.fin[:5]}
                                                </span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                    
                                    if len(empleados_con_turno) > 8:
                                        st.markdown(f"""
                                        <div style="background: white; padding: 4px; text-align: center; 
                                                    border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;
                                                    font-size: 0.7rem; color: #888;">
                                            +{len(empleados_con_turno) - 8} más
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        # Cerrar el borde inferior
                                        st.markdown("""
                                        <div style="border: 1px solid #e0e0e0; border-top: none; 
                                                    border-radius: 0 0 10px 10px; height: 2px;"></div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown("""
                                    <div style="background: white; padding: 15px 8px; text-align: center; 
                                                border: 1px solid #e0e0e0; border-top: none; 
                                                border-radius: 0 0 10px 10px; color: #bbb; font-size: 0.75rem;">
                                        🌙 Descanso
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

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
                        st.metric("Dias trabajados", len(set(turnos_emp.keys())))
                    
                    st.markdown(f"#### 📅 Turnos de {emp.nombre}" + (" (Tu)" if es_usuario else ""))
                    
                    if turnos_emp:
                        data_turnos = []
                        for dia, turno in sorted(turnos_emp.items()):
                            fecha = date(año_sel, mes_num, dia)
                            dias_sem = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
                            data_turnos.append({
                                "Fecha": fecha.strftime("%d/%m/%Y"),
                                "Dia": dias_sem[fecha.weekday()],
                                "Turno": turno.nombre,
                                "Horario": f"{turno.inicio} - {turno.fin}"
                            })
                        df_turnos = pd.DataFrame(data_turnos)
                        st.dataframe(df_turnos, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"{emp.nombre} no tiene turnos asignados en {mes_sel} {año_sel}")

        # TAB 2: COMENTARIOS
        with tab2:
            st.markdown("### 💬 Chat del Area")
            
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
                    nuevo = st.text_area("Escribe tu mensaje", placeholder="Ej: Recordatorio de reunion...", height=100)
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

        # TAB 3: ESTADISTICAS
        with tab3:
            st.markdown("### 📊 Estadisticas del Area")
            
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
                        st.metric("Mas turnos", f"{emp_max} ({max_t})")
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
                st.markdown("#### 📊 Exportar estadisticas")
                
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

    # ============ PAGINA: CALENDARIO ============
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
            st.metric("Dias trabajados", dias_trabajados)
        with col3:
            st.metric("Dias descanso", dias_mes - dias_trabajados)
        
        st.markdown(f"### 📅 {mes} {año}")
        
        dias_semana = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]
        dias_semana_nombres = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
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
                        "Dia": dias_semana_nombres[t.fecha.weekday()],
                        "Turno": t.turno.nombre if t.turno else "N/A",
                        "Horario": f"{t.turno.inicio} - {t.turno.fin}" if t.turno else "N/A"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    # ============ PAGINA: MI PERFIL ============
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
                <h3>Informacion Personal</h3>
                <p><strong>Nombre:</strong> {user.nombre}</p>
                <p><strong>Usuario:</strong> {user.usuario}</p>
                <p><strong>Rol:</strong> {user.rol.upper()}</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="stats-card">
                <h3>Informacion Laboral</h3>
                <p><strong>Area:</strong> {user.area if user.area else 'No asignada'}</p>
                <p><strong>Cargo:</strong> {user.cargo if user.cargo else 'No asignado'}</p>
            </div>
            """, unsafe_allow_html=True)
        
        total_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).count()
        st.metric("Total de turnos asignados", total_turnos)

    # ============ PAGINA: MIS TURNOS ============
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

    # ============ PAGINA: MI EQUIPO ============
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
            area_sel = st.selectbox("Seleccionar area", areas)
        else:
            area_sel = user.area
        
        empleados = session.query(Empleado).filter_by(area=area_sel).all()
        
        if empleados:
            st.markdown(f"### Area: {area_sel}")
            
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
            st.info(f"No hay empleados en el area '{area_sel}'")

    # ============ PAGINA: MATRIZ AREA ============
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
            st.warning("No hay empleados en tu area")
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
            
            st.markdown("### ✏️ Editor de Matriz de Área")
            
            # Configurar editor
            df_editado = st.data_editor(
                df,
                column_config={
                    "Empleado": st.column_config.TextColumn(disabled=True),
                    **{str(d): st.column_config.TextColumn(default="—") for d in range(1, dias_mes+1)}
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_area_{mes}_{año}"
            )
            
            if st.button("💾 Guardar Cambios en Matriz", type="primary"):
                cambios = 0
                for index, row in df_editado.iterrows():
                    emp_id = empleados[index].id
                    for dia in range(1, dias_mes + 1):
                        dia_str = str(dia)
                        nuevo_valor = row[dia_str]
                        
                        # Si cambió o si no era "—"
                        if nuevo_valor != "—":
                            fecha_asignar = date(año, mes_num, dia)
                            turno_obj = session.query(Turno).filter_by(nombre=nuevo_valor).first()
                            
                            if turno_obj:
                                asig = session.query(Asignacion).filter_by(
                                    empleado_id=emp_id, fecha=fecha_asignar
                                ).first()
                                
                                if asig:
                                    asig.turno_id = turno_obj.id
                                else:
                                    session.add(Asignacion(empleado_id=emp_id, fecha=fecha_asignar, turno_id=turno_obj.id))
                                cambios += 1
                            elif nuevo_valor in ["Descanso", "D", ""]:
                                asig = session.query(Asignacion).filter_by(
                                    empleado_id=emp_id, fecha=fecha_asignar
                                ).first()
                                if asig:
                                    session.delete(asig)
                                    cambios += 1
                
                session.commit()
                st.success(f"✅ {cambios} cambios guardados")
                st.rerun()
            
            st.metric("Total turnos en el area", total)

    # ============ PAGINA: ASIGNAR AREA ============
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
            st.warning("No hay empleados en tu area")
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

    # ============ PAGINA: REPORTES AREA ============
    elif op == "Reportes area":
        if user.rol != "supervisor":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">📈 Reportes del Area</h2>
        </div>
        """, unsafe_allow_html=True)
        
        empleados_ids = [e.id for e in session.query(Empleado).filter_by(area=user.area).all()]
        
        if not empleados_ids:
            st.info("No hay empleados en tu area")
            st.stop()
        
        asignaciones = session.query(Asignacion).filter(
            Asignacion.empleado_id.in_(empleados_ids)
        ).all()
        
        if not asignaciones:
            st.info("No hay asignaciones en tu area")
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

    # ============ PAGINA: OTRAS AREAS ============
    elif op == "Otras areas":
        if user.rol not in ["admin", "supervisor"]:
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">🌐 Vista de Otras Areas</h2>
        </div>
        """, unsafe_allow_html=True)
        
        areas = list(set([e.area for e in session.query(Empleado).all() if e.area]))
        areas.sort()
        
        if user.rol == "supervisor":
            areas = [user.area]
        
        area_sel = st.selectbox("Selecciona un area", areas)
        
        if area_sel:
            empleados = session.query(Empleado).filter_by(area=area_sel).all()
            
            if empleados:
                st.markdown(f"### Area: {area_sel}")
                
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
                st.info(f"No hay empleados en el area {area_sel}")

    # ============ PAGINA: EMPLEADOS (ADMIN) ============
    elif op == "Empleados":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">👥 Gestion de Empleados</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📋 Lista", "➕ Nuevo", "✏️ Editar"])
        
        with tab1:
            empleados = session.query(Empleado).all()
            if empleados:
                data = [{
                    "ID": e.id, "Nombre": e.nombre, "Area": e.area or "N/A",
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
                    area = st.text_input("Area")
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
                            area = st.text_input("Area", value=emp.area or "")
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

    # ============ PAGINA: TURNOS (ADMIN) ============
    elif op == "Turnos":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">⏰ Gestion de Turnos</h2>
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

    # ============ PAGINA: MATRIZ TURNOS (ADMIN) ============
    elif op == "Matriz turnos":
        # ... (todo el código de arriba igual: imports, título, filtros, etc.) ...
        
        # Crear DataFrame editable
        if data:
            df = pd.DataFrame(data)
            
            # Configurar columnas para edición
            columnas_editable = [str(dia) for dia in range(1, dias_mes + 1)]
            columnas_fijas = ["Empleado", "Area", "Cargo"]
            
            # Guardar el estado original para comparar cambios después
            if 'df_original' not in st.session_state:
                st.session_state.df_original = df.copy()
            
            st.markdown("### ✏️ Editor de Matriz")
            st.caption("Haz clic en las celdas de turno para cambiarlas (ej: '151', 'Descanso', 'D')")
            
            # Usar data_editor en lugar de dataframe
            df_editado = st.data_editor(
                df,
                column_config={
                    "Empleado": st.column_config.TextColumn(disabled=True),
                    "Area": st.column_config.TextColumn(disabled=True),
                    "Cargo": st.column_config.TextColumn(disabled=True),
                    **{str(d): st.column_config.TextColumn(default="—") for d in range(1, dias_mes+1)}
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_matriz_{mes}_{año}"
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                    cambios_realizados = 0
                    
                    # Iterar por cada fila del dataframe editado
                    for index, row in df_editado.iterrows():
                        emp_id = empleados[index].id  # Asumiendo mismo orden
                        original_row = st.session_state.df_original.iloc[index]
                        
                        for dia in range(1, dias_mes + 1):
                            dia_str = str(dia)
                            nuevo_valor = row[dia_str]
                            original_valor = original_row[dia_str]
                            
                            # Solo procesar si cambió
                            if nuevo_valor != original_valor:
                                fecha_asignar = date(año, mes_num, dia)
                                
                                # 1. Buscar turno por nombre
                                turno_obj = session.query(Turno).filter_by(nombre=nuevo_valor).first()
                                
                                # 2. Buscar asignación existente
                                asignacion_existente = session.query(Asignacion).filter_by(
                                    empleado_id=emp_id,
                                    fecha=fecha_asignar
                                ).first()
                                
                                if not turno_obj:
                                    # Si el valor es "Descanso" o "D", eliminamos la asignación si existe
                                    if asignacion_existente:
                                        session.delete(asignacion_existente)
                                        cambios_realizados += 1
                                else:
                                    # Si hay turno, creamos o actualizamos
                                    if asignacion_existente:
                                        asignacion_existente.turno_id = turno_obj.id
                                    else:
                                        nueva_asig = Asignacion(
                                            empleado_id=emp_id,
                                            fecha=fecha_asignar,
                                            turno_id=turno_obj.id
                                        )
                                        session.add(nueva_asig)
                                    cambios_realizados += 1
                    
                    session.commit()
                    st.success(f"✅ {cambios_realizados} cambios guardados exitosamente")
                    # Limpiar caché de la sesión para forzar recarga visual
                    del st.session_state.df_original
                    st.rerun()
            
            with col2:
                if st.button("🔄 Descartar Cambios", use_container_width=True):
                    del st.session_state.df_original
                    st.rerun()
                    
            st.metric("Total turnos asignados", total)
            
            if st.button("📥 Exportar a Excel"):
                # ... (lógica de exportación existente, pero exportando df_editado) ...
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_editado.to_excel(writer, sheet_name=f"Matriz {mes} {año}", index=False)
                # ... resto igual ...
                output.seek(0)
                st.download_button(
                    "📥 Descargar Excel", output,
                    f"matriz_{mes}_{año}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # ============ PAGINA: ASIGNACION MANUAL (ADMIN) ============
    elif op == "Asignacion manual":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">✏️ Asignacion Manual</h2>
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

    # ============ PAGINA: GENERAR MALLA (ADMIN) ============
    elif op == "Generar malla":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">🤖 Generar Malla Automatica</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Funcion en desarrollo - Generacion automatica de turnos")

    # ============ PAGINA: REPORTES (ADMIN) ============
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
        
        # Obtener datos necesarios
        empleados = session.query(Empleado).all()
        turnos = session.query(Turno).all()
        areas_disponibles = list(set([e.area for e in empleados if e.area]))
        areas_disponibles.sort()
        
        if not empleados:
            st.warning("No hay empleados registrados")
            st.stop()
        
        if not turnos:
            st.warning("No hay turnos registrados")
            st.stop()
        
        # Filtros de fecha
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha_inicio = st.date_input("📅 Fecha inicio", date.today())
        with col2:
            fecha_fin = st.date_input("📅 Fecha fin", date.today() + timedelta(days=30))
        with col3:
            area_filtro = st.selectbox("🏢 Filtrar por área", ["Todas"] + areas_disponibles)
        
        # Obtener asignaciones en el rango
        asignaciones = session.query(Asignacion).filter(
            Asignacion.fecha.between(fecha_inicio, fecha_fin)
        ).all()
        
        # Preparar datos
        empleados_dict = {e.id: e for e in empleados}
        turnos_dict = {t.id: t for t in turnos}
        
        # Crear estructura para análisis horario
        horas_del_dia = list(range(0, 24))
        
        # ============ TABS PARA DIFERENTES VISTAS ============
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Cubrimiento Diario", 
            "📈 Cubrimiento por Área", 
            "⚠️ Áreas Descubiertas",
            "📋 Resumen General"
        ])
        
        # ============ TAB 1: CUBRIMIENTO DIARIO ============
        with tab1:
            st.markdown("### 📊 Empleados con Turno Asignado por Día")
            
            # Agrupar asignaciones por fecha
            asignaciones_por_dia = {}
            for a in asignaciones:
                fecha_str = a.fecha.strftime("%Y-%m-%d")
                if fecha_str not in asignaciones_por_dia:
                    asignaciones_por_dia[fecha_str] = {
                        'total': 0,
                        'por_area': {},
                        'empleados_ids': set()
                    }
                asignaciones_por_dia[fecha_str]['total'] += 1
                asignaciones_por_dia[fecha_str]['empleados_ids'].add(a.empleado_id)
                
                # Por área
                emp = empleados_dict.get(a.empleado_id)
                if emp and emp.area:
                    area = emp.area
                    if area not in asignaciones_por_dia[fecha_str]['por_area']:
                        asignaciones_por_dia[fecha_str]['por_area'][area] = {'turnos': 0, 'empleados': set()}
                    asignaciones_por_dia[fecha_str]['por_area'][area]['turnos'] += 1
                    asignaciones_por_dia[fecha_str]['por_area'][area]['empleados'].add(a.empleado_id)
            
            # Crear DataFrame para visualización
            fechas_ordenadas = sorted(asignaciones_por_dia.keys())
            
            if fechas_ordenadas:
                data_diaria = []
                for fecha_str in fechas_ordenadas:
                    fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    dia_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][fecha_obj.weekday()]
                    
                    info = asignaciones_por_dia[fecha_str]
                    
                    if area_filtro == "Todas":
                        total_empleados_activos = len([e for e in empleados if e.area])
                        empleados_con_turno = len(info['empleados_ids'])
                    else:
                        empleados_con_turno = len(info['por_area'].get(area_filtro, {}).get('empleados', set()))
                        total_empleados_activos = len([e for e in empleados if e.area == area_filtro])
                    
                    porcentaje = round((empleados_con_turno / total_empleados_activos * 100) if total_empleados_activos > 0 else 0, 1)
                    
                    data_diaria.append({
                        "Fecha": fecha_obj.strftime("%d/%m/%Y"),
                        "Día": dia_semana,
                        "Turnos Asignados": info['total'] if area_filtro == "Todas" else info['por_area'].get(area_filtro, {}).get('turnos', 0),
                        "Empleados con Turno": empleados_con_turno,
                        "Total Empleados": total_empleados_activos,
                        "% Cubrimiento": f"{porcentaje}%"
                    })
                
                df_diario = pd.DataFrame(data_diaria)
                
                # Métricas resumen
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📅 Días analizados", len(fechas_ordenadas))
                with col2:
                    total_turnos = df_diario["Turnos Asignados"].sum()
                    st.metric("📊 Total turnos", total_turnos)
                with col3:
                    prom_diario = round(df_diario["Turnos Asignados"].mean(), 1)
                    st.metric("📈 Promedio diario", prom_diario)
                with col4:
                    prom_cubrimiento = round(df_diario["% Cubrimiento"].str.rstrip('%').astype(float).mean(), 1)
                    st.metric("✅ Cubrimiento promedio", f"{prom_cubrimiento}%")
                
                # Mostrar tabla
                st.dataframe(df_diario, use_container_width=True, hide_index=True)
                
                # Gráfico de barras
                st.markdown("#### 📊 Evolución del Cubrimiento")
                
                # Preparar datos para gráfico
                df_graf = df_diario.copy()
                df_graf["% Cubrimiento"] = df_graf["% Cubrimiento"].str.rstrip('%').astype(float)
                df_graf["Fecha"] = pd.to_datetime(df_graf["Fecha"], format="%d/%m/%Y")
                df_graf = df_graf.sort_values("Fecha")
                
                chart_data = pd.DataFrame({
                    "Fecha": df_graf["Fecha"].dt.strftime("%d/%m"),
                    "Empleados con Turno": df_graf["Empleados con Turno"],
                    "Total Empleados": df_graf["Total Empleados"],
                    "% Cubrimiento": df_graf["% Cubrimiento"]
                })
                
                col1, col2 = st.columns(2)
                with col1:
                    st.bar_chart(chart_data.set_index("Fecha")[["Empleados con Turno", "Total Empleados"]])
                with col2:
                    st.line_chart(chart_data.set_index("Fecha")["% Cubrimiento"])
                
                # Exportar
                if st.button("📥 Exportar reporte diario a Excel", key="export_diario"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_diario.to_excel(writer, sheet_name="Cubrimiento Diario", index=False)
                        
                        # Hoja de resumen
                        resumen = pd.DataFrame({
                            "Métrica": ["Días analizados", "Total turnos", "Promedio diario", "Cubrimiento promedio"],
                            "Valor": [len(fechas_ordenadas), total_turnos, prom_diario, f"{prom_cubrimiento}%"]
                        })
                        resumen.to_excel(writer, sheet_name="Resumen", index=False)
                    
                    output.seek(0)
                    st.download_button(
                        "📥 Descargar Excel",
                        output,
                        f"reporte_diario_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info(f"No hay asignaciones en el rango seleccionado ({fecha_inicio} - {fecha_fin})")
        
        # ============ TAB 2: CUBRIMIENTO POR ÁREA ============
        with tab2:
            st.markdown("### 📈 Cubrimiento por Área")
            
            # Calcular estadísticas por área
            stats_por_area = {}
            total_empleados_por_area = {}
            
            for e in empleados:
                if e.area:
                    if e.area not in total_empleados_por_area:
                        total_empleados_por_area[e.area] = 0
                    total_empleados_por_area[e.area] += 1
            
            for a in asignaciones:
                emp = empleados_dict.get(a.empleado_id)
                if emp and emp.area:
                    area = emp.area
                    if area not in stats_por_area:
                        stats_por_area[area] = {
                            'turnos': 0,
                            'empleados_unicos': set(),
                            'dias': set()
                        }
                    stats_por_area[area]['turnos'] += 1
                    stats_por_area[area]['empleados_unicos'].add(a.empleado_id)
                    stats_por_area[area]['dias'].add(a.fecha)
            
            if stats_por_area:
                data_areas = []
                for area in areas_disponibles:
                    stats = stats_por_area.get(area, {'turnos': 0, 'empleados_unicos': set(), 'dias': set()})
                    total_emp = total_empleados_por_area.get(area, 0)
                    
                    emp_con_turno = len(stats['empleados_unicos'])
                    porcentaje_emp = round((emp_con_turno / total_emp * 100) if total_emp > 0 else 0, 1)
                    
                    dias_con_turno = len(stats['dias'])
                    total_dias = (fecha_fin - fecha_inicio).days + 1
                    porcentaje_dias = round((dias_con_turno / total_dias * 100) if total_dias > 0 else 0, 1)
                    
                    data_areas.append({
                        "Área": area,
                        "Total Empleados": total_emp,
                        "Empleados con Turno": emp_con_turno,
                        "% Empleados Cubiertos": f"{porcentaje_emp}%",
                        "Total Turnos": stats['turnos'],
                        "Días con Turnos": dias_con_turno,
                        "% Días Cubiertos": f"{porcentaje_dias}%",
                        "Promedio Turnos/Día": round(stats['turnos'] / dias_con_turno, 1) if dias_con_turno > 0 else 0
                    })
                
                df_areas = pd.DataFrame(data_areas)
                
                # Métricas generales
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🏢 Total Áreas", len(areas_disponibles))
                with col2:
                    areas_con_cobertura = len([a for a in data_areas if float(a["% Empleados Cubiertos"].rstrip('%')) > 0])
                    st.metric("✅ Áreas con cobertura", areas_con_cobertura)
                with col3:
                    prom_cob = df_areas["% Empleados Cubiertos"].str.rstrip('%').astype(float).mean()
                    st.metric("📊 Cubrimiento promedio", f"{round(prom_cob, 1)}%")
                
                # Mostrar tabla
                st.dataframe(df_areas, use_container_width=True, hide_index=True)
                
                # Gráfico comparativo
                st.markdown("#### 📊 Comparativo de Cubrimiento por Área")
                
                df_graf_areas = df_areas.copy()
                df_graf_areas["% Cubrimiento"] = df_graf_areas["% Empleados Cubiertos"].str.rstrip('%').astype(float)
                df_graf_areas = df_graf_areas.sort_values("% Cubrimiento", ascending=False)
                
                st.bar_chart(df_graf_areas.set_index("Área")[["% Cubrimiento", "Total Turnos"]])
                
                # Exportar
                if st.button("📥 Exportar reporte por área a Excel", key="export_areas"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_areas.to_excel(writer, sheet_name="Cubrimiento por Área", index=False)
                    output.seek(0)
                    st.download_button(
                        "📥 Descargar Excel",
                        output,
                        f"reporte_areas_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("No hay datos de asignaciones en el rango seleccionado")
        
        # ============ TAB 3: ÁREAS DESCUBIERTAS (VERSIÓN MODERNA) ============
        with tab3:
            st.markdown("### ⚠️ Análisis de Cobertura en Horas Pico")
            st.caption("Estrategia de cobertura para horario de alta demanda (10:00 - 19:00)")
            
            # Configuración de horas pico
            HORA_PICO_INICIO = 10
            HORA_PICO_FIN = 19
            
            col1, col2, col3 = st.columns(3)
            with col1:
                fecha_analisis = st.date_input(
                    "📅 Fecha análisis",
                    fecha_inicio,
                    min_value=fecha_inicio,
                    max_value=fecha_fin,
                    key="fecha_analisis_v2"
                )
            with col2:
                umbral_minimo = st.slider("🎯 Mínimo empleados requeridos", 1, 10, 2)
            with col3:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
                            padding: 10px; border-radius: 10px; text-align: center;">
                    <span style="color: white; font-size: 0.9rem;">🔥 Horas Pico</span><br>
                    <span style="color: white; font-weight: bold;">{HORA_PICO_INICIO}:00 - {HORA_PICO_FIN}:00</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Definir horas de análisis (enfocado en horas pico + márgenes)
            horas_operativas = list(range(HORA_PICO_INICIO, HORA_PICO_FIN))
            
            # Filtrar asignaciones para la fecha seleccionada
            asignaciones_fecha = [a for a in asignaciones if a.fecha == fecha_analisis]
            
            if not asignaciones_fecha:
                st.warning(f"No hay asignaciones para el {fecha_analisis.strftime('%d/%m/%Y')}")
            else:
                # Organizar turnos por área y hora
                cobertura_por_area_hora = {}
                empleados_por_area_hora = {}
                
                for area in areas_disponibles:
                    cobertura_por_area_hora[area] = {h: 0 for h in horas_operativas}
                    empleados_por_area_hora[area] = {h: [] for h in horas_operativas}
                
                for a in asignaciones_fecha:
                    emp = empleados_dict.get(a.empleado_id)
                    turno = turnos_dict.get(a.turno_id)
                    
                    if emp and emp.area and turno:
                        area = emp.area
                        try:
                            hora_inicio = int(turno.inicio.split(':')[0])
                            hora_fin = int(turno.fin.split(':')[0])
                            if hora_fin == 0:
                                hora_fin = 24
                            
                            for h in range(hora_inicio, hora_fin):
                                if h in horas_operativas:
                                    cobertura_por_area_hora[area][h] += 1
                                    empleados_por_area_hora[area][h].append({
                                        'empleado': emp.nombre,
                                        'empleado_id': emp.id,
                                        'turno': turno.nombre,
                                        'turno_id': turno.id,
                                        'horario': f"{turno.inicio} - {turno.fin}"
                                    })
                        except:
                            pass
                
                # ============ MÉTRICAS PRINCIPALES ============
                st.markdown("---")
                st.markdown("#### 📊 Estado de Cobertura en Horas Pico")
                
                # Calcular estadísticas
                areas_criticas = []
                areas_optimas = []
                areas_riesgo = []
                
                for area in areas_disponibles:
                    total_empleados_area = total_empleados_por_area.get(area, 0)
                    if total_empleados_area == 0:
                        continue
                    
                    # Promedio de cobertura en horas pico
                    cobertura_promedio = sum(cobertura_por_area_hora[area].values()) / len(horas_operativas)
                    horas_descubiertas = sum(1 for h in horas_operativas if cobertura_por_area_hora[area][h] < umbral_minimo)
                    porcentaje_cob = ((len(horas_operativas) - horas_descubiertas) / len(horas_operativas)) * 100
                    
                    estado = {
                        'area': area,
                        'total_emp': total_empleados_area,
                        'cobertura_prom': cobertura_promedio,
                        'horas_desc': horas_descubiertas,
                        'porcentaje': porcentaje_cob
                    }
                    
                    if horas_descubiertas > len(horas_operativas) * 0.3:  # Más del 30% descubierto
                        areas_criticas.append(estado)
                    elif horas_descubiertas > 0:
                        areas_riesgo.append(estado)
                    else:
                        areas_optimas.append(estado)
                
                # Mostrar tarjetas de resumen
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🏢 Total Áreas", len(areas_disponibles))
                with col2:
                    st.metric("🔴 Áreas Críticas", len(areas_criticas))
                with col3:
                    st.metric("🟡 En Riesgo", len(areas_riesgo))
                with col4:
                    st.metric("🟢 Óptimas", len(areas_optimas))
                
                # ============ VISUALIZACIÓN MODERNA POR ÁREA ============
                st.markdown("---")
                st.markdown("#### 🏪 Cobertura por Área en Horas Pico")
                
                for area in areas_disponibles:
                    total_emp = total_empleados_por_area.get(area, 0)
                    if total_emp == 0:
                        continue
                    
                    cobertura_area = cobertura_por_area_hora[area]
                    horas_criticas = [h for h in horas_operativas if cobertura_area[h] < umbral_minimo]
                    
                    # Determinar estado
                    if len(horas_criticas) > len(horas_operativas) * 0.3:
                        estado_color = "#ff4757"
                        estado_emoji = "🔴"
                        estado_texto = "CRÍTICO"
                    elif len(horas_criticas) > 0:
                        estado_color = "#ffa502"
                        estado_emoji = "🟡"
                        estado_texto = "EN RIESGO"
                    else:
                        estado_color = "#2ed573"
                        estado_emoji = "🟢"
                        estado_texto = "ÓPTIMO"
                    
                    with st.expander(f"{estado_emoji} {area} - {estado_texto} ({len(horas_criticas)} horas descubiertas)", expanded=(len(horas_criticas) > 0)):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Gráfico de barras horizontal para cobertura por hora
                            st.markdown("**📊 Cobertura por hora:**")
                            
                            # Crear visualización con HTML/CSS (CORREGIDO)
                            for h in horas_operativas:
                                empleados = cobertura_area[h]
                                if empleados >= umbral_minimo:
                                    bar_color = "#2ed573"
                                    text_color = "#2ed573"
                                elif empleados > 0:
                                    bar_color = "#ffa502"
                                    text_color = "#ffa502"
                                else:
                                    bar_color = "#ff4757"
                                    text_color = "#ff4757"
                                
                                bar_width = min(empleados * 20, 100)
                                if bar_width == 0:
                                    bar_width = 5  # Mínimo visible para barras vacías
                                
                                st.markdown(f"""
                                <div style="display: flex; align-items: center; margin: 5px 0;">
                                    <span style="width: 60px; font-weight: bold;">{h:02d}:00</span>
                                    <div style="flex: 1; height: 24px; background: #f0f0f0; border-radius: 12px; margin: 0 10px; overflow: hidden;">
                                        <div style="width: {bar_width}%; height: 100%; background: {bar_color}; border-radius: 12px;"></div>
                                    </div>
                                    <span style="width: 30px; text-align: right; font-weight: 600;">{empleados}</span>
                                    <span style="margin-left: 10px; font-size: 0.8rem; color: {text_color}; font-weight: 500;">{empleados}/{umbral_minimo}</span>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with col2:
                            # Métricas del área
                            cobertura_prom = sum(cobertura_area.values()) / len(horas_operativas)
                            st.markdown(f"""
                            <div style="background: {estado_color}15; padding: 15px; border-radius: 15px; 
                                        border: 1px solid {estado_color}30;">
                                <h4 style="margin: 0 0 10px 0; color: {estado_color};">📈 Estadísticas</h4>
                                <p><strong>Total empleados:</strong> {total_emp}</p>
                                <p><strong>Cobertura promedio:</strong> {cobertura_prom:.1f} emp/hora</p>
                                <p><strong>Horas críticas:</strong> {len(horas_criticas)}/{len(horas_operativas)}</p>
                                <p><strong>% Cubrimiento:</strong> {((len(horas_operativas) - len(horas_criticas)) / len(horas_operativas) * 100):.0f}%</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Si hay horas críticas, mostrar franjas y opción de asignación
                        if horas_criticas:
                            st.markdown("**⚠️ Franjas horarias con baja cobertura:**")
                            
                            # Agrupar horas consecutivas
                            franjas = []
                            inicio = horas_criticas[0]
                            fin = horas_criticas[0]
                            for h in horas_criticas[1:]:
                                if h == fin + 1:
                                    fin = h
                                else:
                                    franjas.append((inicio, fin + 1))
                                    inicio = h
                                    fin = h
                            franjas.append((inicio, fin + 1))
                            
                            for idx, (inicio, fin) in enumerate(franjas):
                                col1, col2, col3 = st.columns([2, 1, 1])
                                with col1:
                                    st.markdown(f"🔥 **{inicio:02d}:00 - {fin:02d}:00**")
                                with col2:
                                    deficit = umbral_minimo * (fin - inicio)
                                    actual = sum(cobertura_area[h] for h in range(inicio, fin))
                                    st.markdown(f"📉 Déficit: {max(0, deficit - actual)} empleados")
                                with col3:
                                    if st.button(f"➕ Reforzar", key=f"refuerzo_{area}_{idx}"):
                                        st.session_state[f"show_assign_{area}_{idx}"] = True
                                
                                if st.session_state.get(f"show_assign_{area}_{idx}", False):
                                    with st.container():
                                        st.markdown("---")
                                        st.markdown(f"#### 🚀 Asignar refuerzo - {area}")
                                        
                                        empleados_area = [e for e in empleados if e.area == area]
                                        if empleados_area:
                                            col_a, col_b, col_c = st.columns(3)
                                            with col_a:
                                                emp_sel = st.selectbox(
                                                    "Empleado",
                                                    [e.nombre for e in empleados_area],
                                                    key=f"emp_{area}_{idx}"
                                                )
                                            with col_b:
                                                turno_sel = st.selectbox(
                                                    "Turno",
                                                    [t.nombre for t in turnos],
                                                    key=f"turno_{area}_{idx}"
                                                )
                                            with col_c:
                                                st.markdown("<br>", unsafe_allow_html=True)
                                                if st.button("✅ Confirmar", key=f"conf_{area}_{idx}"):
                                                    emp = next(e for e in empleados_area if e.nombre == emp_sel)
                                                    turno = next(t for t in turnos if t.nombre == turno_sel)
                                                    
                                                    nueva = Asignacion(
                                                        empleado_id=emp.id,
                                                        fecha=fecha_analisis,
                                                        turno_id=turno.id
                                                    )
                                                    session.add(nueva)
                                                    session.commit()
                                                    st.success(f"✅ {emp.nombre} asignado como refuerzo")
                                                    st.session_state[f"show_assign_{area}_{idx}"] = False
                                                    st.rerun()
                                            
                                            if st.button("❌ Cancelar", key=f"cancel_{area}_{idx}"):
                                                st.session_state[f"show_assign_{area}_{idx}"] = False
                                                st.rerun()
                                        else:
                                            st.warning(f"No hay empleados en {area}")
                
                # ============ MAPA DE CALOR MEJORADO ============
                st.markdown("---")
                st.markdown("#### 🗺️ Mapa de Calor - Cobertura en Horas Pico")
                
                # Crear datos para el heatmap
                data_heatmap = []
                for area in areas_disponibles:
                    fila = {"Área": area}
                    for h in horas_operativas:
                        fila[f"{h:02d}:00"] = cobertura_por_area_hora[area][h]
                    data_heatmap.append(fila)
                
                df_heatmap = pd.DataFrame(data_heatmap)
                
                # Función de color mejorada
                def color_val_pico(val):
                    if val >= umbral_minimo:
                        return 'background-color: #2ed573; color: white; font-weight: bold'
                    elif val >= umbral_minimo * 0.5:
                        return 'background-color: #ffa502; color: white; font-weight: bold'
                    elif val > 0:
                        return 'background-color: #ff6b6b; color: white; font-weight: bold'
                    else:
                        return 'background-color: #c0392b; color: white; font-weight: bold'
                
                subset_cols = [f"{h:02d}:00" for h in horas_operativas]
                try:
                    styled_df = df_heatmap.style.map(color_val_pico, subset=subset_cols)
                except AttributeError:
                    styled_df = df_heatmap.style.applymap(color_val_pico, subset=subset_cols)
                
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # Leyenda mejorada
                st.markdown("""
                <div style="display: flex; gap: 15px; margin-top: 15px; justify-content: center;">
                    <span style="display: flex; align-items: center;"><span style="background: #c0392b; width: 20px; height: 20px; border-radius: 5px; margin-right: 8px;"></span> 0 empleados</span>
                    <span style="display: flex; align-items: center;"><span style="background: #ff6b6b; width: 20px; height: 20px; border-radius: 5px; margin-right: 8px;"></span> Insuficiente</span>
                    <span style="display: flex; align-items: center;"><span style="background: #ffa502; width: 20px; height: 20px; border-radius: 5px; margin-right: 8px;"></span> En riesgo</span>
                    <span style="display: flex; align-items: center;"><span style="background: #2ed573; width: 20px; height: 20px; border-radius: 5px; margin-right: 8px;"></span> Óptimo</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Exportar
                if st.button("📥 Exportar análisis de cobertura", key="export_cobertura"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_heatmap.to_excel(writer, sheet_name=f"Cobertura_{fecha_analisis}", index=False)
                        
                        # Usar areas_criticas y areas_riesgo en lugar de areas_descubiertas
                        todas_area_criticas = areas_criticas + areas_riesgo
                        if todas_area_criticas:
                            data_desc = []
                            for info in todas_area_criticas:
                                data_desc.append({
                                    "Área": info['area'],
                                    "Total Empleados": info['total_emp'],
                                    "Horas Descubiertas": info['horas_desc'],
                                    "% Cubrimiento": f"{info['porcentaje']:.0f}%"
                                })
                            pd.DataFrame(data_desc).to_excel(writer, sheet_name="Áreas Descubiertas", index=False)
                    
                    output.seek(0)
                    st.download_button(
                        "📥 Descargar Excel",
                        output,
                        f"cobertura_{fecha_analisis.strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        
        # ============ TAB 4: RESUMEN GENERAL ============
        with tab4:
            st.markdown("### 📋 Resumen General del Período")
            
            # Estadísticas generales
            total_empleados_sistema = len([e for e in empleados if e.area])
            empleados_con_turno_periodo = len(set([a.empleado_id for a in asignaciones]))
            total_turnos_periodo = len(asignaciones)
            dias_en_periodo = (fecha_fin - fecha_inicio).days + 1
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📅 Días en período", dias_en_periodo)
            with col2:
                st.metric("👥 Total empleados", total_empleados_sistema)
            with col3:
                st.metric("✅ Empleados con turno", empleados_con_turno_periodo)
            with col4:
                st.metric("📊 Total turnos", total_turnos_periodo)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                porcentaje_global = round((empleados_con_turno_periodo / total_empleados_sistema * 100) if total_empleados_sistema > 0 else 0, 1)
                st.metric("📈 Cubrimiento global", f"{porcentaje_global}%")
            with col2:
                prom_turnos_dia = round(total_turnos_periodo / dias_en_periodo, 1) if dias_en_periodo > 0 else 0
                st.metric("📊 Prom. turnos/día", prom_turnos_dia)
            with col3:
                prom_turnos_emp = round(total_turnos_periodo / empleados_con_turno_periodo, 1) if empleados_con_turno_periodo > 0 else 0
                st.metric("👤 Prom. turnos/emp", prom_turnos_emp)
            with col4:
                areas_activas = len(set([empleados_dict[a.empleado_id].area for a in asignaciones if empleados_dict.get(a.empleado_id) and empleados_dict[a.empleado_id].area]))
                st.metric("🏢 Áreas activas", f"{areas_activas}/{len(areas_disponibles)}")
            
            # Ranking de empleados con más turnos
            st.markdown("---")
            st.markdown("#### 🏆 Ranking de Empleados con Más Turnos")
            
            turnos_por_empleado = {}
            for a in asignaciones:
                emp = empleados_dict.get(a.empleado_id)
                if emp:
                    if emp.id not in turnos_por_empleado:
                        turnos_por_empleado[emp.id] = {
                            'nombre': emp.nombre,
                            'area': emp.area or 'N/A',
                            'turnos': 0
                        }
                    turnos_por_empleado[emp.id]['turnos'] += 1
            
            ranking = sorted(turnos_por_empleado.values(), key=lambda x: x['turnos'], reverse=True)[:10]
            
            if ranking:
                df_ranking = pd.DataFrame(ranking)
                df_ranking.index = range(1, len(df_ranking) + 1)
                df_ranking.index.name = "#"
                st.dataframe(df_ranking, use_container_width=True)
            
            # Ranking de áreas con más actividad
            st.markdown("#### 🏢 Ranking de Áreas por Actividad")
            
            turnos_por_area = {}
            for a in asignaciones:
                emp = empleados_dict.get(a.empleado_id)
                if emp and emp.area:
                    area = emp.area
                    turnos_por_area[area] = turnos_por_area.get(area, 0) + 1
            
            ranking_areas = sorted(turnos_por_area.items(), key=lambda x: x[1], reverse=True)
            
            if ranking_areas:
                df_ranking_areas = pd.DataFrame(ranking_areas, columns=["Área", "Total Turnos"])
                df_ranking_areas.index = range(1, len(df_ranking_areas) + 1)
                df_ranking_areas.index.name = "#"
                st.dataframe(df_ranking_areas, use_container_width=True)
            
            # Exportar resumen completo
            if st.button("📥 Exportar resumen completo", key="export_resumen"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Hoja de resumen
                    resumen_data = {
                        "Métrica": [
                            "Período", "Días analizados", "Total empleados", 
                            "Empleados con turno", "Total turnos", "Cubrimiento global",
                            "Promedio turnos/día", "Promedio turnos/empleado", "Áreas activas"
                        ],
                        "Valor": [
                            f"{fecha_inicio} - {fecha_fin}", dias_en_periodo, total_empleados_sistema,
                            empleados_con_turno_periodo, total_turnos_periodo, f"{porcentaje_global}%",
                            prom_turnos_dia, prom_turnos_emp, f"{areas_activas}/{len(areas_disponibles)}"
                        ]
                    }
                    pd.DataFrame(resumen_data).to_excel(writer, sheet_name="Resumen", index=False)
                    
                    # Ranking empleados
                    if ranking:
                        pd.DataFrame(ranking).to_excel(writer, sheet_name="Ranking Empleados", index=False)
                    
                    # Ranking áreas
                    if ranking_areas:
                        pd.DataFrame(ranking_areas, columns=["Área", "Total Turnos"]).to_excel(
                            writer, sheet_name="Ranking Áreas", index=False
                        )
                
                output.seek(0)
                st.download_button(
                    "📥 Descargar Excel",
                    output,
                    f"resumen_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        # ============ TAB 5: ESTRATEGIA HORAS PICO ============
        tab5 = st.tabs(["📊 Cubrimiento Diario", "📈 Cubrimiento por Área", "⚠️ Áreas Descubiertas", "📋 Resumen General", "🔥 Estrategia Horas Pico"])[4]
        with tab5:
            st.markdown("### 🔥 Estrategia de Cobertura - Horas Pico")
            st.caption("Análisis estratégico para maximizar cobertura en horario de alta demanda (10:00 - 19:00)")
            
            HORA_PICO_INICIO = 10
            HORA_PICO_FIN = 19
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                fecha_estrategia = st.date_input(
                    "📅 Fecha de análisis",
                    fecha_inicio,
                    key="fecha_estrategia"
                )
            with col2:
                umbral_optimo = st.slider("🎯 Objetivo empleados/hora", 2, 10, 3, key="umbral_estrategia")
            with col3:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 10px; border-radius: 10px; text-align: center;">
                    <span style="color: white; font-size: 0.9rem;">🎯 Meta de Cobertura</span><br>
                    <span style="color: white; font-weight: bold;">{umbral_optimo} empleados/hora</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Obtener asignaciones del día
            asignaciones_dia = [a for a in asignaciones if a.fecha == fecha_estrategia]
            
            # Calcular cobertura actual
            cobertura_actual = {}
            for area in areas_disponibles:
                cobertura_actual[area] = {h: 0 for h in range(HORA_PICO_INICIO, HORA_PICO_FIN)}
            
            for a in asignaciones_dia:
                emp = empleados_dict.get(a.empleado_id)
                turno = turnos_dict.get(a.turno_id)
                if emp and emp.area and turno:
                    area = emp.area
                    try:
                        h_ini = int(turno.inicio.split(':')[0])
                        h_fin = int(turno.fin.split(':')[0])
                        if h_fin == 0:
                            h_fin = 24
                        for h in range(max(h_ini, HORA_PICO_INICIO), min(h_fin, HORA_PICO_FIN)):
                            cobertura_actual[area][h] += 1
                    except:
                        pass
            
            # ============ ANÁLISIS DE BRECHA ============
            st.markdown("---")
            st.markdown("#### 📊 Brecha de Cobertura por Área")
            
            brechas = []
            for area in areas_disponibles:
                total_emp = total_empleados_por_area.get(area, 0)
                if total_emp == 0:
                    continue
                
                horas_deficit = []
                deficit_total = 0
                for h in range(HORA_PICO_INICIO, HORA_PICO_FIN):
                    actual = cobertura_actual[area][h]
                    if actual < umbral_optimo:
                        horas_deficit.append(h)
                        deficit_total += (umbral_optimo - actual)
                
                if horas_deficit:
                    brechas.append({
                        'area': area,
                        'total_emp': total_emp,
                        'horas_deficit': len(horas_deficit),
                        'deficit_total': deficit_total,
                        'deficit_prom': deficit_total / len(horas_deficit) if horas_deficit else 0,
                        'horas': horas_deficit
                    })
            
            if brechas:
                # Ordenar por gravedad
                brechas.sort(key=lambda x: x['deficit_total'], reverse=True)
                
                # Mostrar tarjetas de brecha
                for b in brechas[:5]:  # Top 5 áreas con mayor brecha
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.markdown(f"**🏢 {b['area']}**")
                            st.caption(f"Total empleados: {b['total_emp']}")
                        with col2:
                            st.metric("Horas con déficit", b['horas_deficit'])
                        with col3:
                            st.metric("Déficit total", f"{b['deficit_total']} emp-hora")
                        with col4:
                            st.metric("Déficit promedio", f"{b['deficit_prom']:.1f} emp/hora")
                        
                        # Recomendación
                        st.info(f"💡 **Recomendación:** Agregar {int(b['deficit_prom']) + 1} empleado(s) adicional(es) en {b['area']} durante horas pico")
                        st.markdown("---")
                
                # ============ GRÁFICO DE BRECHA ============
                st.markdown("#### 📈 Visualización de Brecha por Área")
                
                data_brecha = pd.DataFrame([{
                    'Área': b['area'],
                    'Déficit Total (emp-hora)': b['deficit_total'],
                    'Horas con Déficit': b['horas_deficit']
                } for b in brechas])
                
                st.bar_chart(data_brecha.set_index('Área')[['Déficit Total (emp-hora)']])
                
                # ============ PLAN DE ACCIÓN ============
                st.markdown("---")
                st.markdown("#### 🎯 Plan de Acción Recomendado")
                
                total_deficit = sum(b['deficit_total'] for b in brechas)
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                            padding: 20px; border-radius: 15px; color: white;">
                    <h3 style="margin: 0 0 15px 0;">📋 Resumen Ejecutivo</h3>
                    <p><strong>Total déficit identificado:</strong> {total_deficit} empleados-hora</p>
                    <p><strong>Áreas críticas:</strong> {len(brechas)}</p>
                    <p><strong>Horario pico analizado:</strong> {HORA_PICO_INICIO}:00 - {HORA_PICO_FIN}:00</p>
                    <hr style="border-color: rgba(255,255,255,0.3);">
                    <p><strong>🚀 Acciones prioritarias:</strong></p>
                    <ol>
                """, unsafe_allow_html=True)
                
                for i, b in enumerate(brechas[:3]):
                    st.markdown(f"<li><strong>{b['area']}:</strong> Reforzar con {int(b['deficit_prom']) + 1} empleado(s) adicional(es)</li>", unsafe_allow_html=True)
                
                st.markdown("""
                    </ol>
                    <p style="margin-top: 15px;">💡 <em>Implementar estas acciones mejorará significativamente la experiencia del cliente en horas pico.</em></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Exportar plan de acción
                if st.button("📥 Exportar Plan de Acción", key="export_plan"):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Datos de brecha
                        pd.DataFrame(brechas).to_excel(writer, sheet_name="Análisis de Brecha", index=False)
                        
                        # Plan de acción
                        plan = pd.DataFrame([{
                            'Área': b['area'],
                            'Acción Recomendada': f"Agregar {int(b['deficit_prom']) + 1} empleado(s)",
                            'Horas Críticas': ', '.join([f"{h}:00" for h in b['horas'][:5]]) + ('...' if len(b['horas']) > 5 else ''),
                            'Prioridad': 'ALTA' if b['deficit_total'] > total_deficit/len(brechas) else 'MEDIA'
                        } for b in brechas])
                        plan.to_excel(writer, sheet_name="Plan de Acción", index=False)
                    
                    output.seek(0)
                    st.download_button(
                        "📥 Descargar Plan de Acción",
                        output,
                        f"plan_accion_{fecha_estrategia.strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.success(f"🎉 ¡Excelente! Todas las áreas cumplen con el objetivo de {umbral_optimo} empleados/hora en horario pico")
                st.balloons()

    # ============ PAGINA: BACKUP (ADMIN) ============
    elif op == "Backup":
        if user.rol != "admin":
            st.error("❌ No tienes permiso")
            st.stop()
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;">
            <h2 style="color: white; text-align: center; margin: 0;">🛡 Backup y Restauracion</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📤 Exportar", "📥 Importar"])
        
        with tab1:
            st.markdown("### Exportar base de datos")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Generar backup automatico", use_container_width=True):
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
            st.warning("⚠️ Al importar un backup, se sobrescribira la base de datos actual")
            
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
                        st.warning("🔄 Recarga la pagina para aplicar los cambios")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

else:
    login()