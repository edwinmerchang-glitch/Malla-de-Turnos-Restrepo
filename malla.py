import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import Session, Empleado, Turno, Asignacion
from scheduler import generar_malla_inteligente
from backup import backup_sqlite

st.set_page_config("Malla de Turnos", layout="wide")

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

# -------- MENÚ CON BOTONES --------
st.sidebar.title("📅 Malla de Turnos")
st.sidebar.markdown(f"**Usuario:** {user.nombre}")
st.sidebar.markdown(f"**Rol:** {user.rol}")
if user.area:  # Mostrar área si existe
    st.sidebar.markdown(f"**Área:** {user.area}")
if user.cargo:  # Mostrar cargo si existe
    st.sidebar.markdown(f"**Cargo:** {user.cargo}")
st.sidebar.markdown("---")

# Inicializar la página actual si no existe
if "pagina_actual" not in st.session_state:
    st.session_state.pagina_actual = "Calendario"

# Función para cambiar de página
def cambiar_pagina(pagina):
    st.session_state.pagina_actual = pagina

# Crear botones en el sidebar
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("📅 Calendario", use_container_width=True):
        cambiar_pagina("Calendario")
    if st.button("👥 Empleados", use_container_width=True):
        cambiar_pagina("Empleados")
    if st.button("⏰ Turnos", use_container_width=True):
        cambiar_pagina("Turnos")

with col2:
    if st.button("🤖 Generar", use_container_width=True):
        cambiar_pagina("Generar malla")
    if st.button("📊 Reportes", use_container_width=True):
        cambiar_pagina("Reportes")
    if st.button("🛡 Backup", use_container_width=True):
        cambiar_pagina("Backup")

# Mostrar la página actual con un indicador
st.sidebar.markdown("---")
st.sidebar.info(f"📍 Página actual: **{st.session_state.pagina_actual}**")

# Botón de cerrar sesión
if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# -------- CONTENIDO SEGÚN LA PÁGINA SELECCIONADA --------
op = st.session_state.pagina_actual

# -------- EMPLEADOS --------
if op == "Empleados":
    st.subheader("👥 Empleados")
    
    # Pestañas para diferentes vistas
    tab1, tab2, tab3 = st.tabs(["📋 Lista de empleados", "➕ Nuevo empleado", "✏️ Editar/Eliminar"])
    
    with tab1:  # LISTA DE EMPLEADOS
        st.markdown("### Lista completa de empleados")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_area = st.text_input("🔍 Filtrar por área", key="filtro_area")
        with col2:
            filtro_cargo = st.text_input("🔍 Filtrar por cargo", key="filtro_cargo")
        with col3:
            filtro_nombre = st.text_input("🔍 Filtrar por nombre", key="filtro_nombre")
        
        empleados = session.query(Empleado).all()
        
        # Aplicar filtros
        if filtro_area:
            empleados = [e for e in empleados if e.area and filtro_area.lower() in e.area.lower()]
        if filtro_cargo:
            empleados = [e for e in empleados if e.cargo and filtro_cargo.lower() in e.cargo.lower()]
        if filtro_nombre:
            empleados = [e for e in empleados if filtro_nombre.lower() in e.nombre.lower()]
        
        if empleados:
            data = []
            for e in empleados:
                data.append({
                    "ID": e.id,
                    "Nombre": e.nombre,
                    "Área": e.area if e.area else "No asignada",
                    "Cargo": e.cargo if e.cargo else "No asignado",
                    "Usuario": e.usuario,
                    "Rol": e.rol
                })
            df = pd.DataFrame(data)
            
            # Mostrar estadísticas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total empleados", len(empleados))
            col2.metric("Áreas distintas", df["Área"].nunique() if not df.empty else 0)
            col3.metric("Cargos distintos", df["Cargo"].nunique() if not df.empty else 0)
            
            st.dataframe(df, use_container_width=True)
            
            # Botón para exportar
            if st.button("📥 Exportar lista a Excel"):
                output = pd.ExcelWriter('empleados.xlsx', engine='xlsxwriter')
                df.to_excel(output, index=False, sheet_name='Empleados')
                output.close()
                
                with open('empleados.xlsx', 'rb') as f:
                    st.download_button(
                        "📥 Confirmar descarga",
                        f,
                        "empleados.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("ℹ️ No hay empleados que coincidan con los filtros")
    
    with tab2:  # NUEVO EMPLEADO
        st.markdown("### Crear nuevo empleado")
        
        with st.form("nuevo_emp"):
            col1, col2 = st.columns(2)
            
            with col1:
                n = st.text_input("Nombre completo *", placeholder="Ej: Juan Pérez")
                u = st.text_input("Usuario *", placeholder="Ej: jperez")
                r = st.selectbox("Rol *", ["empleado", "admin"])
                
            with col2:
                area = st.text_input("Área", placeholder="Ej: Producción, Ventas, RRHH...")
                cargo = st.text_input("Cargo", placeholder="Ej: Operario, Supervisor, Analista...")
                p = st.text_input("Contraseña *", type="password", placeholder="Mínimo 4 caracteres")
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col2:
                submitted = st.form_submit_button("✅ Crear empleado", use_container_width=True, type="primary")
            
            if submitted:
                if not n or not u or not p:
                    st.error("❌ Los campos marcados con * son obligatorios")
                else:
                    # Verificar si el usuario ya existe
                    existe = session.query(Empleado).filter_by(usuario=u).first()
                    if existe:
                        st.error(f"❌ El usuario '{u}' ya existe")
                    else:
                        session.add(Empleado(
                            nombre=n, 
                            rol=r, 
                            usuario=u, 
                            password=p,
                            area=area if area else None,
                            cargo=cargo if cargo else None
                        ))
                        session.commit()
                        st.success(f"✅ Empleado '{n}' creado correctamente")
                        st.balloons()
    
    with tab3:  # EDITAR/ELIMINAR
        st.markdown("### Editar o eliminar empleados")
        
        empleados = session.query(Empleado).all()
        if empleados:
            # Selector de empleado
            empleado_dict = {f"{e.nombre} ({e.usuario})": e.id for e in empleados}
            empleado_seleccionado = st.selectbox("Seleccionar empleado", list(empleado_dict.keys()))
            emp_id = empleado_dict[empleado_seleccionado]
            emp = session.query(Empleado).get(emp_id)
            
            if emp:
                with st.form("editar_emp"):
                    st.markdown(f"**Editando: {emp.nombre}**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nombre_edit = st.text_input("Nombre", value=emp.nombre)
                        usuario_edit = st.text_input("Usuario", value=emp.usuario)
                        rol_edit = st.selectbox("Rol", ["empleado", "admin"], index=0 if emp.rol == "empleado" else 1)
                        
                    with col2:
                        area_edit = st.text_input("Área", value=emp.area if emp.area else "")
                        cargo_edit = st.text_input("Cargo", value=emp.cargo if emp.cargo else "")
                        password_edit = st.text_input("Nueva contraseña (dejar vacío para no cambiar)", type="password")
                    
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
                    with col3:
                        eliminar = st.form_submit_button("🗑️ Eliminar empleado", use_container_width=True)
                    
                    if guardar:
                        emp.nombre = nombre_edit
                        emp.usuario = usuario_edit
                        emp.rol = rol_edit
                        emp.area = area_edit if area_edit else None
                        emp.cargo = cargo_edit if cargo_edit else None
                        if password_edit:  # Solo cambiar si se ingresó una nueva
                            emp.password = password_edit
                        
                        session.commit()
                        st.success("✅ Cambios guardados")
                        st.rerun()
                    
                    if eliminar:
                        if emp.id == user.id:
                            st.error("❌ No puedes eliminarte a ti mismo")
                        else:
                            # Verificar si tiene asignaciones
                            asignaciones = session.query(Asignacion).filter_by(empleado_id=emp.id).first()
                            if asignaciones:
                                st.warning("⚠️ Este empleado tiene asignaciones. Elimínalas primero.")
                            else:
                                session.delete(emp)
                                session.commit()
                                st.success("✅ Empleado eliminado")
                                st.rerun()
        else:
            st.info("ℹ️ No hay empleados para editar")