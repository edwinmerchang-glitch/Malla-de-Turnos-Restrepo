import shutil
import os
import datetime

def backup_sqlite(nombre_personalizado=None):
    """
    Crea un backup de la base de datos
    Si se proporciona nombre_personalizado, lo usa, sino genera automático
    """
    os.makedirs("data/backups", exist_ok=True)
    
    if nombre_personalizado:
        # Usar el nombre proporcionado
        nombre_archivo = nombre_personalizado
    else:
        # Generar nombre automático
        fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"data/backups/backup_{fecha}.db"
    
    # Verificar que el archivo existe
    if os.path.exists("data.db"):
        shutil.copy("data.db", nombre_archivo)
        return True
    else:
        print("⚠️ Archivo data.db no encontrado")
        return False