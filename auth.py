import streamlit as st
from database import Session, Empleado

def login():
    session = Session()

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        st.markdown("## 🔐 Iniciar sesión")

        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")

        if st.button("Entrar", use_container_width=True):
            emp = session.query(Empleado).filter_by(usuario=user, password=pwd).first()
            if emp:
                st.session_state.auth = True
                st.session_state.user = emp.usuario
                st.session_state.rol = emp.rol
                st.rerun()  # Cambiado de experimental_rerun a rerun
            else:
                st.error("Credenciales incorrectas")

        return False

    return True