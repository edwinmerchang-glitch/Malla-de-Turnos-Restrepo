import streamlit as st
import hashlib

USUARIOS = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "rol": "admin"
    },
    "empleado": {
        "password": hashlib.sha256("empleado123".encode()).hexdigest(),
        "rol": "empleado"
    }
}

def login():
    st.sidebar.header("🔐 Acceso")

    usuario = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")

    if st.sidebar.button("Ingresar"):
        if usuario in USUARIOS:
            clave = hashlib.sha256(password.encode()).hexdigest()
            if clave == USUARIOS[usuario]["password"]:
                st.session_state["usuario"] = usuario
                st.session_state["rol"] = USUARIOS[usuario]["rol"]
                st.experimental_rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no válido")

def proteger_app():
    if "usuario" not in st.session_state:
        login()
        st.stop()