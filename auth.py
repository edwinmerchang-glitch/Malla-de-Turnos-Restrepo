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
        
        # Verificar si el usuario ya existe
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        if c.fetchone():
            return False, f"El usuario '{username}' ya existe"
        
        # Insertar nuevo usuario
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return True, f"Usuario '{username}' creado exitosamente"
        
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
        
        # Buscar usuario
        c.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (username, hash_password(password))
        )
        result = c.fetchone()
        
        if result:
            return result
        else:
            # Debug: verificar si el usuario existe
            c.execute("SELECT username FROM users WHERE username=?", (username,))
            if c.fetchone():
                print(f"Usuario '{username}' existe pero contraseña incorrecta")
            else:
                print(f"Usuario '{username}' no existe")
            return None
            
    except Exception as e:
        print(f"Error en login: {str(e)}")
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