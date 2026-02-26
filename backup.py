import shutil
import os
import datetime
import streamlit as st

def backup_sqlite(nombre_personalizado=None, ruta_destino=None):
    """
    Crea un backup de la base de datos
    - nombre_personalizado: nombre del archivo (opcional)
    - ruta_destino: ruta externa para guardar el backup (opcional)
    """
    # Carpeta local de backups (siempre existe)
    os.makedirs("data/backups", exist_ok=True)
    
    # Generar nombre del archivo
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if nombre_personalizado:
        # Limpiar el nombre (quitar espacios, caracteres especiales)
        nombre_limpio = "".join(c for c in nombre_personalizado if c.isalnum() or c in [' ', '-', '_']).strip()
        nombre_limpio = nombre_limpio.replace(' ', '_')
        nombre_archivo = f"backup_{nombre_limpio}_{fecha}.db"
    else:
        nombre_archivo = f"backup_{fecha}.db"
    
    # Verificar que el archivo de BD existe
    if not os.path.exists("data.db"):
        print("⚠️ Archivo data.db no encontrado")
        return False, None
    
    # 1. Guardar en carpeta local siempre
    ruta_local = f"data/backups/{nombre_archivo}"
    shutil.copy("data.db", ruta_local)
    
    resultados = {
        "local": ruta_local,
        "externo": None
    }
    
    # 2. Si se especificó ruta externa, guardar también allí
    if ruta_destino:
        try:
            # Crear la carpeta de destino si no existe
            os.makedirs(ruta_destino, exist_ok=True)
            
            ruta_externa = os.path.join(ruta_destino, nombre_archivo)
            shutil.copy("data.db", ruta_externa)
            
            resultados["externo"] = ruta_externa
            print(f"✅ Backup guardado en ruta externa: {ruta_externa}")
            
        except Exception as e:
            print(f"❌ Error al guardar en ruta externa: {str(e)}")
            resultados["error_externo"] = str(e)
    
    return True, resultados

def listar_backups(ruta=None):
    """
    Lista los backups disponibles
    - ruta: si se proporciona, lista los de esa ruta
    """
    backups = []
    
    # Backups locales
    if os.path.exists("data/backups"):
        for b in os.listdir("data/backups"):
            ruta_completa = f"data/backups/{b}"
            if os.path.isfile(ruta_completa):
                tamaño = os.path.getsize(ruta_completa)
                fecha_mod = os.path.getmtime(ruta_completa)
                backups.append({
                    "nombre": b,
                    "ruta": ruta_completa,
                    "tamaño": tamaño,
                    "fecha": fecha_mod,
                    "tipo": "local"
                })
    
    # Backups en ruta externa (si se proporciona)
    if ruta and os.path.exists(ruta):
        for b in os.listdir(ruta):
            ruta_completa = os.path.join(ruta, b)
            if os.path.isfile(ruta_completa) and b.endswith('.db'):
                tamaño = os.path.getsize(ruta_completa)
                fecha_mod = os.path.getmtime(ruta_completa)
                backups.append({
                    "nombre": b,
                    "ruta": ruta_completa,
                    "tamaño": tamaño,
                    "fecha": fecha_mod,
                    "tipo": "externo"
                })
    
    # Ordenar por fecha (más reciente primero)
    backups.sort(key=lambda x: x["fecha"], reverse=True)
    
    return backups

def restaurar_backup(ruta_backup):
    """
    Restaura un backup desde cualquier ruta
    """
    if not os.path.exists(ruta_backup):
        return False, "Archivo de backup no encontrado"
    
    try:
        # Crear backup de seguridad antes de restaurar
        fecha_ahora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_seguridad = f"data/backups/ANTES_RESTAURAR_{fecha_ahora}.db"
        
        if os.path.exists("data.db"):
            shutil.copy("data.db", backup_seguridad)
        
        # Restaurar el backup
        shutil.copy(ruta_backup, "data.db")
        
        return True, backup_seguridad
        
    except Exception as e:
        return False, str(e)

def formatear_tamaño(tamaño_bytes):
    """Formatea el tamaño de archivo para mostrar"""
    if tamaño_bytes < 1024:
        return f"{tamaño_bytes} B"
    elif tamaño_bytes < 1024 * 1024:
        return f"{tamaño_bytes/1024:.1f} KB"
    else:
        return f"{tamaño_bytes/(1024*1024):.1f} MB"