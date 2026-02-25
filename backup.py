import shutil, os, datetime

def backup_sqlite():
    os.makedirs("data/backups", exist_ok=True)
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    shutil.copy("data/turnos.db", f"data/backups/backup_{fecha}.db")