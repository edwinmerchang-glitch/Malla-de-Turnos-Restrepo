# backup.py
import shutil
import os
import datetime

def backup_sqlite():
    """Crea un backup de la base de datos en la carpeta local"""
    os.makedirs("data/backups", exist_ok=True)
    
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"data/backups/backup_{fecha}.db"
    
    if os.path.exists("data.db"):
        shutil.copy("data.db", nombre_archivo)
        return True
    else:
        print("⚠️ Archivo data.db no encontrado")
        return False