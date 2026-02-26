import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from database import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite
import os
import shutil  # IMPORTANTE: para copiar archivos
from calendar import monthrange
from datetime import datetime  # Agrega esto junto con los otros imports

st.set_page_config("Malla de Turnos", layout="wide")

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
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state["user"]
session = Session()

# -------- MENÚ CON BOTONES SEGÚN EL ROL --------
st.sidebar.title("📅 Malla de Turnos")
st.sidebar.markdown(f"**Usuario:** {user.nombre}")
st.sidebar.markdown(f"**Rol:** {user.rol}")
if user.area:
    st.sidebar.markdown(f"**Área:** {user.area}")
if user.cargo:
    st.sidebar.markdown(f"**Cargo:** {user.cargo}")
st.sidebar.markdown("---")

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
    st.sidebar.markdown("### 📋 Mi espacio")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("📅 Calendario", use_container_width=True):
            cambiar_pagina("Calendario")
        if st.button("👤 Mi perfil", use_container_width=True):
            cambiar_pagina("Mi perfil")
    
    with col2:
        if st.button("📊 Mis turnos", use_container_width=True):
            cambiar_pagina("Mis turnos")

# -------- MENÚ PARA SUPERVISORES --------
elif user.rol == "supervisor":
    st.sidebar.markdown("### 📋 Mi área")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("👥 Mi equipo", use_container_width=True):
            cambiar_pagina("Mi equipo")
        if st.button("📊 Matriz área", use_container_width=True):
            cambiar_pagina("Matriz area")
        if st.button("👤 Mi perfil", use_container_width=True):
            cambiar_pagina("Mi perfil")
    
    with col2:
        if st.button("✏️ Asignar turnos", use_container_width=True):
            cambiar_pagina("Asignar area")
        if st.button("📈 Reportes área", use_container_width=True):
            cambiar_pagina("Reportes area")
        if st.button("📅 Mi calendario", use_container_width=True):
            cambiar_pagina("Calendario")

# -------- MENÚ PARA ADMINISTRADORES --------
elif user.rol == "admin":
    st.sidebar.markdown("### ⚙️ Administración")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("👥 Empleados", use_container_width=True):
            cambiar_pagina("Empleados")
        if st.button("⏰ Turnos", use_container_width=True):
            cambiar_pagina("Turnos")
        if st.button("📊 Matriz general", use_container_width=True):
            cambiar_pagina("Matriz turnos")
        if st.button("👤 Mi perfil", use_container_width=True):
            cambiar_pagina("Mi perfil")
    
    with col2:
        if st.button("✏️ Asignar manual", use_container_width=True):
            cambiar_pagina("Asignacion manual")
        if st.button("🤖 Generar malla", use_container_width=True):
            cambiar_pagina("Generar malla")
        if st.button("📊 Reportes", use_container_width=True):
            cambiar_pagina("Reportes")
        if st.button("🛡 Backup", use_container_width=True):
            cambiar_pagina("Backup")

st.sidebar.markdown("---")
st.sidebar.info(f"📍 Página actual: **{st.session_state.pagina_actual}**")

if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# -------- CONTENIDO --------
op = st.session_state.pagina_actual

# ========== PÁGINAS PARA EMPLEADOS ==========

# ---------- CALENDARIO MODERNO ----------
elif op == "Calendario":
    if user.rol not in ["empleado", "supervisor"]:
        st.error("❌ No tienes permiso para acceder a esta sección")
        st.stop()
    
    # Estilos CSS personalizados
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
    }
    .evento-card:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    .evento-hora {
        font-size: 0.8rem;
        opacity: 0.9;
        margin-top: 0.2rem;
    }
    .dia-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        min-height: 120px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
        transition: all 0.3s;
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
    }
    .dia-semana {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cabecera moderna
    st.markdown("""
    <div class="calendario-container">
        <div class="calendario-titulo">📅 Mi Calendario de Turnos</div>
        <div class="calendario-subtitulo">Visualiza y gestiona tus horarios de trabajo</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Información del usuario en tarjeta moderna
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
    
    # Filtros modernos
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
    
    # Obtener asignaciones
    asignaciones = session.query(Asignacion).filter(
        Asignacion.empleado_id == user.id,
        Asignacion.fecha.between(fecha_inicio_mes, fecha_fin_mes)
    ).all()
    
    if not asignaciones:
        st.info(f"ℹ️ No tienes turnos asignados en {mes} {año}")
        st.stop()
    
    # Estadísticas rápidas
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
    
    # Crear diccionario de asignaciones por día
    turnos_por_dia = {}
    for a in asignaciones:
        dia = a.fecha.day
        turnos_por_dia[dia] = a
    
    # Crear vista de calendario en grid
    dias_semana = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
    
    # Calcular primer día del mes
    primer_dia = date(año, mes_num, 1).weekday()  # 0 = lunes, 6 = domingo
    
    # Ajustar para que empiece en lunes (en Python weekday() 0 = lunes)
    
    st.markdown(f"### 📅 {mes} {año}")
    
    # Cabecera de días de la semana
    cols = st.columns(7)
    for i, dia in enumerate(dias_semana):
        with cols[i]:
            st.markdown(f"""
            <div style="text-align: center; font-weight: bold; color: #667eea; padding: 10px;">
                {dia}
            </div>
            """, unsafe_allow_html=True)
    
    # Grid del calendario
    dia_actual = 1
    semanas = []
    
    # Crear matriz de semanas
    for semana in range(6):  # Máximo 6 semanas
        fila = []
        for dia_semana in range(7):
            if semana == 0 and dia_semana < primer_dia:
                fila.append(None)  # Días vacíos antes del inicio del mes
            elif dia_actual <= dias_mes:
                fila.append(dia_actual)
                dia_actual += 1
            else:
                fila.append(None)  # Días vacíos después del fin del mes
        semanas.append(fila)
    
    # Mostrar el calendario
    for semana in semanas:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            with cols[i]:
                if dia is not None:
                    # Verificar si hay turno este día
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
                    # Día vacío (fuera del mes)
                    st.markdown(f"""
                    <div class="dia-card" style="background: #f9f9f9; opacity: 0.5;">
                        <div style="text-align: center; color: #ccc;">-</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Leyenda de colores
    with st.expander("📖 Ver detalles de turnos", expanded=False):
        st.markdown("### 📊 Distribución de turnos")
        
        # Gráfico de barras con pandas
        df_turnos = pd.DataFrame(list(turnos_por_tipo.items()), columns=["Turno", "Cantidad"])
        df_turnos = df_turnos.sort_values("Cantidad", ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(df_turnos.set_index("Turno"))
        
        with col2:
            st.markdown("### 📋 Detalle por turno")
            for turno, cantidad in turnos_por_tipo.items():
                porcentaje = (cantidad / total_turnos) * 100
                st.markdown(f"""
                <div style="margin: 10px 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <span><strong>{turno}</strong></span>
                        <span>{cantidad} turnos ({porcentaje:.1f}%)</span>
                    </div>
                    <div style="background: #f0f0f0; height: 8px; border-radius: 4px;">
                        <div style="background: linear-gradient(90deg, #667eea, #764ba2); width: {porcentaje}%; height: 8px; border-radius: 4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Vista de tabla detallada
    with st.expander("📋 Ver todos los turnos en tabla"):
        data_tabla = []
        for a in asignaciones:
            data_tabla.append({
                "Fecha": a.fecha.strftime("%d/%m/%Y"),
                "Día": a.fecha.strftime("%A").capitalize(),
                "Turno": a.turno.nombre if a.turno else "N/A",
                "Hora inicio": a.turno.inicio if a.turno else "N/A",
                "Hora fin": a.turno.fin if a.turno else "N/A"
            })
        
        df_tabla = pd.DataFrame(data_tabla)
        df_tabla = df_tabla.sort_values("Fecha")
        st.dataframe(
            df_tabla,
            use_container_width=True,
            column_config={
                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "Día": "Día",
                "Turno": "Turno",
                "Hora inicio": "Inicio",
                "Hora fin": "Fin"
            }
        )
        
        # Botón para exportar
        if st.button("📥 Exportar a Excel", use_container_width=True):
            output = pd.ExcelWriter('mis_turnos.xlsx', engine='xlsxwriter')
            df_tabla.to_excel(output, index=False, sheet_name=f'Turnos_{mes}_{año}')
            output.close()
            
            with open('mis_turnos.xlsx', 'rb') as f:
                st.download_button(
                    "📥 Descargar Excel",
                    f,
                    f"mis_turnos_{mes}_{año}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ---------- MI PERFIL ----------
elif op == "Mi perfil":
    st.subheader("👤 Mi perfil")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Información personal")
        st.markdown(f"**Nombre:** {user.nombre}")
        st.markdown(f"**Usuario:** {user.usuario}")
        st.markdown(f"**Rol:** {user.rol}")
        st.markdown(f"**Área:** {user.area if user.area else 'No asignada'}")
        st.markdown(f"**Cargo:** {user.cargo if user.cargo else 'No asignado'}")
    
    with col2:
        st.markdown("### Estadísticas")
        total_turnos = session.query(Asignacion).filter_by(empleado_id=user.id).count()
        st.metric("Total turnos asignados", total_turnos)

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
    
    with tab1:  # LISTA DE TURNOS
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
    
    with tab2:  # NUEVO TURNO
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
                    # Verificar si ya existe
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
    
    with tab3:  # EDITAR/ELIMINAR TURNOS
        st.markdown("### Editar o eliminar turnos")
        
        turnos = session.query(Turno).all()
        
        if not turnos:
            st.info("No hay turnos para editar")
        else:
            # Selector de turno
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
                            # Verificar si el nuevo nombre ya existe (excepto el mismo turno)
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
                            # Verificar si el turno está siendo usado
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
                    # Mostrar estadísticas del turno
                    st.markdown("#### 📊 Estadísticas")
                    
                    # Contar asignaciones de este turno
                    total_asignaciones = session.query(Asignacion).filter_by(turno_id=turno.id).count()
                    st.metric("Asignaciones", total_asignaciones)
                    
                    # Última vez usado
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
        
        # Preparar datos
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
        
        # Botón para descargar plantilla
        with st.expander("📥 Descargar plantilla de ejemplo"):
            # Crear plantilla
            template_data = []
            for emp in empleados[:5]:  # Solo 5 empleados de ejemplo
                fila = {
                    "Empleado": emp.nombre,
                    "Área": emp.area if emp.area else "",
                    "Cargo": emp.cargo if emp.cargo else "",
                }
                # Agregar algunos días de ejemplo
                for dia in [1, 2, 3, 4, 5]:
                    fila[dia] = ""
                template_data.append(fila)
            
            df_template = pd.DataFrame(template_data)
            
            # Guardar temporalmente
            template_path = "plantilla.xlsx"
            df_template.to_excel(template_path, index=False)
            
            with open(template_path, "rb") as f:
                st.download_button(
                    "📥 Descargar plantilla Excel",
                    f,
                    "plantilla_turnos.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        archivo = st.file_uploader("Seleccionar archivo Excel", type=['xlsx', 'xls'])
        
        if archivo:
            try:
                df_carga = pd.read_excel(archivo)
                
                # Mostrar vista previa
                st.success("✅ Archivo cargado correctamente")
                
                # Opción para mostrar todas o solo vista previa
                mostrar_todas = st.checkbox("Mostrar todas las filas", value=False)
                if mostrar_todas:
                    st.dataframe(df_carga, use_container_width=True)
                else:
                    st.dataframe(df_carga.head(10), use_container_width=True)
                    st.caption(f"Mostrando 10 de {len(df_carga)} filas. Marca la casilla para ver todas.")
                
                # Identificar columnas de días (las que son números)
                columnas_dias = []
                for col in df_carga.columns:
                    try:
                        # Intentar convertir a entero
                        int(col)
                        columnas_dias.append(str(col))
                    except:
                        pass
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Empleados a procesar", len(df_carga))
                with col2:
                    st.metric("Días encontrados", len(columnas_dias))
                
                if 'Empleado' not in df_carga.columns:
                    st.error("❌ El archivo debe tener una columna llamada 'Empleado'")
                else:
                    # ===== DEPURACIÓN =====
                    with st.expander("🔍 Ver información de depuración"):
                        st.write("**Primeras 3 filas del Excel:**")
                        st.dataframe(df_carga.head(3))
                        
                        # Mostrar tipos de datos
                        st.write("**Tipos de datos en Excel:**")
                        for col in df_carga.columns[:5]:  # Primeras 5 columnas
                            st.write(f"- {col}: {df_carga[col].dtype}")
                        
                        # Mostrar turnos disponibles en BD
                        st.write("**Turnos en Base de Datos:**")
                        todos_turnos = session.query(Turno).all()
                        turnos_bd = [t.nombre for t in todos_turnos]
                        st.write(turnos_bd)
                        
                        # Mostrar muestra de valores de turnos del Excel
                        st.write("**Muestra de valores de turnos del Excel (primeros 20):**")
                        valores_muestra = []
                        for dia_str in columnas_dias[:3]:  # Primeros 3 días
                            # Usar dia_str directamente (ya es string)
                            valores = df_carga[dia_str].dropna().unique()[:5]
                            for v in valores:
                                valores_muestra.append(f"Día {dia_str}: {v} (tipo: {type(v)})")
                        for v in valores_muestra[:10]:
                            st.write(f"  - {v}")
                        
                        # Botón para probar una fila específica
                        st.write("**Prueba manual:**")
                        fila_prueba = st.selectbox("Seleccionar empleado para probar", df_carga['Empleado'].tolist())
                        if fila_prueba:
                            row_prueba = df_carga[df_carga['Empleado'] == fila_prueba].iloc[0]
                            st.write("Datos de la fila:")
                            st.write(row_prueba)
                            
                            # Buscar empleado
                            emp_test = session.query(Empleado).filter(Empleado.nombre.ilike(f"%{fila_prueba}%")).first()
                            if emp_test:
                                st.success(f"✅ Empleado encontrado: {emp_test.nombre}")
                                
                                # Probar un día
                                dia_test = st.number_input("Día a probar", 1, dias_mes, 1)
                                valor_test = row_prueba[dia_test]
                                st.write(f"Valor en Excel para día {dia_test}: '{valor_test}' (tipo: {type(valor_test)})")
                                
                                if pd.notna(valor_test):
                                    # Buscar turno
                                    turno_test = session.query(Turno).filter(Turno.nombre == str(valor_test)).first()
                                    if turno_test:
                                        st.success(f"✅ Turno encontrado: {turno_test.nombre}")
                                    else:
                                        st.error(f"❌ Turno no encontrado: '{valor_test}'")
                                        
                                        # Buscar flexible
                                        turno_test2 = session.query(Turno).filter(Turno.nombre.ilike(f"%{str(valor_test)}%")).first()
                                        if turno_test2:
                                            st.info(f"  Pero se encontró por coincidencia parcial: {turno_test2.nombre}")
                            else:
                                st.error(f"❌ Empleado no encontrado: {fila_prueba}")
                    
                    if st.button("📤 Procesar carga masiva", use_container_width=True, type="primary"):
                        count_total = 0
                        empleados_no_encontrados = []
                        turnos_no_encontrados = []
                        
                        # Barra de progreso
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Obtener todos los turnos para búsqueda flexible
                        todos_turnos = session.query(Turno).all()
                        
                        for idx, row in df_carga.iterrows():
                            # Actualizar progreso
                            progress = (idx + 1) / len(df_carga)
                            progress_bar.progress(progress)
                            status_text.text(f"Procesando fila {idx + 1} de {len(df_carga)}...")
                            
                            nombre_emp = str(row['Empleado']).strip()
                            
                            # Buscar empleado de manera flexible
                            empleado = None
                            
                            # Búsqueda 1: Exacta ignorando mayúsculas
                            empleado = session.query(Empleado).filter(
                                Empleado.nombre.ilike(nombre_emp)
                            ).first()
                            
                            # Búsqueda 2: Contiene el nombre
                            if not empleado:
                                empleado = session.query(Empleado).filter(
                                    Empleado.nombre.ilike(f"%{nombre_emp}%")
                                ).first()
                            
                            # Búsqueda 3: Por partes del nombre
                            if not empleado:
                                partes = nombre_emp.split()
                                for parte in partes:
                                    if len(parte) > 2:
                                        empleado = session.query(Empleado).filter(
                                            Empleado.nombre.ilike(f"%{parte}%")
                                        ).first()
                                        if empleado:
                                            break
                            
                            if empleado:
                                # Procesar cada día
                                for dia_str in columnas_dias:
                                    dia = int(dia_str)
                                    if 1 <= dia <= dias_mes:
                                        # Usar dia_str para acceder al DataFrame
                                        valor_turno = row[dia_str] if dia_str in row else None
                                        
                                        # Verificar si es descanso
                                        if pd.isna(valor_turno) or str(valor_turno).strip() in ['', 'None', '—', '-']:
                                            # Eliminar si existe
                                            existe = session.query(Asignacion).filter_by(
                                                empleado_id=empleado.id,
                                                fecha=date(año, mes_num, dia)
                                            ).first()
                                            if existe:
                                                session.delete(existe)
                                                count_total += 1
                                        else:
                                            # Buscar turno de manera flexible
                                            turno_nombre = str(valor_turno).strip()
                                            
                                            # Si es número (float/int), convertir a string sin decimales
                                            if isinstance(valor_turno, (int, float)):
                                                if valor_turno == int(valor_turno):  # Si es número entero
                                                    turno_nombre = str(int(valor_turno))
                                                else:
                                                    turno_nombre = str(valor_turno)
                                            
                                            turno = None
                                            
                                            # Intentar búsqueda exacta
                                            turno = session.query(Turno).filter_by(nombre=turno_nombre).first()
                                            
                                            # Si no encuentra, intentar como string sin espacios
                                            if not turno:
                                                turno = session.query(Turno).filter(
                                                    Turno.nombre.ilike(f"%{turno_nombre}%")
                                                ).first()
                                            
                                            # Si aún no encuentra, intentar convertir a string y comparar
                                            if not turno:
                                                for t in todos_turnos:
                                                    if str(t.nombre).strip() == turno_nombre:
                                                        turno = t
                                                        break
                                            
                                            if turno:
                                                existe = session.query(Asignacion).filter_by(
                                                    empleado_id=empleado.id,
                                                    fecha=date(año, mes_num, dia)
                                                ).first()
                                                
                                                if existe:
                                                    existe.turno_id = turno.id
                                                else:
                                                    session.add(Asignacion(
                                                        empleado_id=empleado.id,
                                                        fecha=date(año, mes_num, dia),
                                                        turno_id=turno.id
                                                    ))
                                                count_total += 1
                                            else:
                                                if turno_nombre not in turnos_no_encontrados:
                                                    turnos_no_encontrados.append(turno_nombre)
                            else:
                                if nombre_emp not in empleados_no_encontrados:
                                    empleados_no_encontrados.append(nombre_emp)
                            
                            # Commit cada 10 filas
                            if (idx + 1) % 10 == 0:
                                session.commit()
                        
                        # Commit final
                        session.commit()
                        progress_bar.empty()
                        status_text.empty()
                        
                        # Mostrar resultados
                        st.success(f"✅ Procesamiento completado: {count_total} turnos actualizados")
                        
                        if empleados_no_encontrados:
                            st.warning(f"⚠️ No se encontraron {len(empleados_no_encontrados)} empleados:")
                            for emp in empleados_no_encontrados[:10]:
                                st.write(f"  - {emp}")
                        
                        if turnos_no_encontrados:
                            st.warning(f"⚠️ No se encontraron {len(turnos_no_encontrados)} turnos:")
                            for turno in turnos_no_encontrados[:10]:
                                st.write(f"  - '{turno}'")
                        
                        if count_total > 0:
                            st.balloons()
                        
                        if st.button("🔄 Recargar matriz"):
                            st.rerun()
                            
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Botón de exportar
    st.markdown("---")
    if st.button("📥 Exportar matriz a Excel"):
        data_export = []
        for emp in empleados:
            fila = {
                "Empleado": emp.nombre,
                "Área": emp.area or "N/A",
                "Cargo": emp.cargo or "N/A",
            }
            for dia in range(1, dias_mes + 1):
                turno_id = matriz.get(emp.id, {}).get(dia)
                fila[str(dia)] = turnos_dict.get(turno_id, "") if turno_id else ""
            data_export.append(fila)
        
        df_export = pd.DataFrame(data_export)
        df_export.to_excel("matriz_turnos.xlsx", index=False)
        
        with open("matriz_turnos.xlsx", "rb") as f:
            st.download_button(
                "📥 Descargar Excel",
                f,
                f"matriz_{mes}_{año}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
                # Generar nombre automático
                fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"backup_{fecha}.db"
                
                # Crear archivo temporal
                shutil.copy("data.db", nombre_archivo)
                
                # Ofrecer descarga
                with open(nombre_archivo, "rb") as f:
                    st.download_button(
                        "📥 Descargar backup",
                        f,
                        nombre_archivo,
                        "application/octet-stream",
                        use_container_width=True
                    )
                
                # Limpiar archivo temporal después de la descarga
                os.remove(nombre_archivo)
        
        with col2:
            st.markdown("**Backup con nombre**")
            nombre_personalizado = st.text_input("Nombre del archivo", placeholder="ej: backup_enero")
            
            if st.button("📝 Generar backup personalizado", use_container_width=True):
                if nombre_personalizado:
                    # Limpiar nombre (quitar espacios, caracteres especiales)
                    nombre_limpio = "".join(c for c in nombre_personalizado if c.isalnum() or c in [' ', '-', '_']).strip()
                    nombre_limpio = nombre_limpio.replace(' ', '_')
                    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"{nombre_limpio}_{fecha}.db"
                    
                    # Crear archivo temporal
                    shutil.copy("data.db", nombre_archivo)
                    
                    # Ofrecer descarga
                    with open(nombre_archivo, "rb") as f:
                        st.download_button(
                            "📥 Descargar backup personalizado",
                            f,
                            nombre_archivo,
                            "application/octet-stream",
                            use_container_width=True
                        )
                    
                    # Limpiar archivo temporal
                    os.remove(nombre_archivo)
                else:
                    st.warning("⚠️ Ingresa un nombre para el archivo")
        
        st.markdown("---")
        st.markdown("### 📁 Backups recientes")
        
        # Mostrar backups de la carpeta local
        if os.path.exists("data/backups"):
            backups = os.listdir("data/backups")
            if backups:
                # Ordenar por fecha (más reciente primero)
                backups.sort(reverse=True)
                
                for i, b in enumerate(backups[:5]):
                    ruta_completa = f"data/backups/{b}"
                    tamaño = os.path.getsize(ruta_completa)
                    
                    # Formatear tamaño
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
            # Mostrar información del archivo
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Archivo:** {archivo_subido.name}")
            with col2:
                tamaño_kb = len(archivo_subido.getvalue()) / 1024
                st.info(f"**Tamaño:** {tamaño_kb:.1f} KB")
            
            # Confirmación
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col2:
                confirmar = st.checkbox("Confirmo que quiero restaurar este backup")
                
                if st.button("♻️ Restaurar backup", use_container_width=True, type="primary", disabled=not confirmar):
                    try:
                        # Crear backup de seguridad antes de restaurar
                        fecha_ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_seguridad = f"data/backups/ANTES_RESTAURAR_{fecha_ahora}.db"
                        
                        if os.path.exists("data.db"):
                            shutil.copy("data.db", backup_seguridad)
                            st.info(f"✅ Backup de seguridad creado: {os.path.basename(backup_seguridad)}")
                        
                        # Guardar el archivo subido
                        with open("data.db", "wb") as f:
                            f.write(archivo_subido.getbuffer())
                        
                        st.success("✅ Base de datos restaurada correctamente")
                        st.balloons()
                        st.warning("🔄 La aplicación se recargará para aplicar los cambios")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error al restaurar: {str(e)}")