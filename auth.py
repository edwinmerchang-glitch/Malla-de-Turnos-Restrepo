import hashlib
from database import get_connection

def hash_password(password):
    """Genera hash SHA256 de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role):
    """Crea un nuevo usuario en la base de datos"""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return True, "Usuario creado exitosamente"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Error al crear usuario: {str(e)}"
    finally:
        if conn:
            conn.close()

def login_user(username, password):
    """Verifica credenciales y retorna el rol si son correctas"""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (username, hash_password(password))
        )
        result = c.fetchone()
        return result if result else None
    except Exception as e:
        print(f"Error en login: {str(e)}")  # Para debugging
        return None
    finally:
        if conn:
            conn.close()

def user_exists(username):
    """Verifica si un usuario ya existe"""
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        result = c.fetchone()
        return result is not None
    except Exception as e:
        print(f"Error en user_exists: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()