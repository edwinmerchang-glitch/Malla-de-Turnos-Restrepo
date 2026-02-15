import sqlite3

def get_connection():
    return sqlite3.connect("turnos.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        cargo TEXT,
        usuario TEXT UNIQUE,
        correo TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado TEXT,
        fecha TEXT,
        turno TEXT
    )""")

    conn.commit()
    conn.close()
