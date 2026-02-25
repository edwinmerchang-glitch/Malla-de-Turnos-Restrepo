import shutil
import os
import datetime

def backup_sqlite():
    os.makedirs("data/backups", exist_ok=True)
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    
    # Verificar que el archivo existe
    if os.path.exists("data.db"):
        shutil.copy("data.db", f"data/backups/backup_{fecha}.db")
        return True
    else:
        print("⚠️ Archivo data.db no encontrado")
        return False