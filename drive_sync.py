"""
drive_sync.py — Sincronización automática con Google Drive
Lee el archivo Excel desde Drive y actualiza la BD si hubo cambios.
"""

import os
import io
import json
import logging
import hashlib
import pandas as pd
from datetime import datetime, date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from database import Session, Empleado, Turno, Asignacion

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ── Cargar credenciales desde variable de entorno ──────────────────────────
def _get_credentials():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("Variable de entorno GOOGLE_SERVICE_ACCOUNT_JSON no configurada.")
    
    # Railway a veces escapa las comillas o agrega comillas externas
    # Intentar múltiples formas de parsear
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        try:
            # Puede venir con comillas externas escapadas
            info = json.loads(raw.strip('"').replace('\\"', '"'))
        except json.JSONDecodeError:
            try:
                # Puede venir con \\n en lugar de \n
                info = json.loads(raw.replace('\\n', '\n'))
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON inválido en GOOGLE_SERVICE_ACCOUNT_JSON: {e}. Primeros 100 chars: {raw[:100]}")
    
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def _get_drive_service():
    return build("drive", "v3", credentials=_get_credentials(), cache_discovery=False)


# ── Descargar el Excel desde Drive como bytes ──────────────────────────────
def descargar_excel_drive(file_id: str) -> bytes:
    service = _get_drive_service()
    file_id = file_id.strip()  # Limpiar espacios o saltos de línea
    # Si es un Google Sheet hay que exportarlo; si es .xlsx se descarga directo
    meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
    mime = meta.get("mimeType", "")

    if "spreadsheet" in mime:
        # Google Sheets → exportar como xlsx
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        request = service.files().get_media(fileId=file_id)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


# ── Hash del archivo para detectar cambios ────────────────────────────────
def _hash_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ── Parser de la malla (igual que en malla.py) ────────────────────────────
def _parsear_malla(data: bytes):
    df_raw = pd.read_excel(io.BytesIO(data), header=None)

    # Detectar fila de fechas
    fila_fechas = None
    primera_col_dia = 4
    for i in range(min(5, len(df_raw))):
        fila = df_raw.iloc[i]
        fechas_en_fila = [v for v in fila[4:] if isinstance(v, (pd.Timestamp, datetime)) or hasattr(v, "year")]
        if len(fechas_en_fila) >= 20:
            fila_fechas = i
            primera_col_dia = next(
                j for j in range(4, len(fila))
                if isinstance(fila[j], (pd.Timestamp, datetime)) or hasattr(fila[j], "year")
            )
            break

    if fila_fechas is None:
        raise ValueError("No se encontró la fila de fechas en el archivo.")

    # Extraer fechas
    fila_enc = df_raw.iloc[fila_fechas]
    columnas_fecha = {}
    for j in range(primera_col_dia, len(fila_enc)):
        val = fila_enc[j]
        if isinstance(val, (pd.Timestamp, datetime)) or hasattr(val, "year"):
            try:
                columnas_fecha[j] = pd.Timestamp(val).date()
            except Exception:
                pass

    # Detectar primera fila de empleados
    primera_fila_emp = fila_fechas + 2
    for i in range(fila_fechas + 1, min(fila_fechas + 6, len(df_raw))):
        val_num    = df_raw.iloc[i, 0]
        val_nombre = df_raw.iloc[i, 2]
        val_cargo  = df_raw.iloc[i, 1]
        try:
            float(val_num)
            nombre_str_test = str(val_nombre).strip()
            cargo_str_test  = str(val_cargo).strip()
            if (nombre_str_test and nombre_str_test.upper() not in ["NAN", "CC"]
                    and cargo_str_test and cargo_str_test.upper() not in ["NAN", "CC"]):
                primera_fila_emp = i
                break
        except (ValueError, TypeError):
            continue

    CODIGOS_NO_TURNO = {"df", "vc", "cp", "-1", "nan", ""}

    empleados_detectados = []
    for i in range(primera_fila_emp, len(df_raw)):
        fila = df_raw.iloc[i]
        try:
            float(fila[0])
        except (ValueError, TypeError):
            continue

        nombre_val = fila[2]
        cargo_val  = fila[1]
        cedula_val = fila[3]

        if pd.isna(nombre_val) or not str(nombre_val).strip():
            continue
        nombre_str = str(nombre_val).strip()
        if nombre_str.upper() in ["TIENDA", "DOMI", "TOTAL", "MADRUGON", "VACANTE", "NAN"]:
            continue
        cargo_str = str(cargo_val).strip() if pd.notna(cargo_val) else ""
        if not cargo_str or cargo_str.upper() == "NAN":
            continue

        cedula_str = ""
        if pd.notna(cedula_val):
            try:
                cedula_str = str(int(float(str(cedula_val))))
            except Exception:
                cedula_str = str(cedula_val).strip()

        turnos_emp = {}
        for j, fecha in columnas_fecha.items():
            cod = fila[j] if j < len(fila) else None
            if pd.notna(cod):
                cod_str = str(cod).strip()
                try:
                    cod_str = str(int(float(cod_str)))
                except (ValueError, OverflowError):
                    pass
                if cod_str.lower() not in CODIGOS_NO_TURNO:
                    turnos_emp[fecha] = cod_str

        empleados_detectados.append({
            "nombre":  nombre_str,
            "cargo":   cargo_str,
            "area":    cargo_str,
            "cedula":  cedula_str,
            "turnos":  turnos_emp,
        })

    return empleados_detectados, columnas_fecha


# ── Sincronizar BD ─────────────────────────────────────────────────────────
def sincronizar(data: bytes) -> dict:
    """Aplica los datos del Excel a la BD. Retorna estadísticas."""
    empleados_detectados, columnas_fecha = _parsear_malla(data)

    session = Session()
    creados_emp = creados_tur = creadas_asig = actualizadas_asig = borradas_asig = 0

    try:
        turnos_db = {t.nombre: t for t in session.query(Turno).all()}

        # Crear turnos nuevos
        codigos_en_excel = {cod for e in empleados_detectados for cod in e["turnos"].values()}
        for cod in codigos_en_excel - set(turnos_db.keys()):
            nuevo_turno = Turno(nombre=cod, inicio="", fin="")
            session.add(nuevo_turno)
            creados_tur += 1
        session.flush()
        turnos_db = {t.nombre: t for t in session.query(Turno).all()}

        for emp_data in empleados_detectados:
            usuario_gen = emp_data["cedula"] if emp_data["cedula"] else emp_data["nombre"].lower().replace(" ", ".")[:20]

            emp_obj = session.query(Empleado).filter_by(usuario=usuario_gen).first()
            if not emp_obj:
                emp_obj = Empleado(
                    nombre=emp_data["nombre"],
                    usuario=usuario_gen,
                    password="123456",
                    rol="empleado",
                    area=emp_data["area"],
                    cargo=emp_data["cargo"],
                )
                session.add(emp_obj)
                session.flush()
                creados_emp += 1

            # Borrar asignaciones del mes que ya no están en el Excel
            fechas_en_excel = set(emp_data["turnos"].keys())
            fechas_del_mes  = set(columnas_fecha.values())
            for fecha_borrar in fechas_del_mes - fechas_en_excel:
                asig = session.query(Asignacion).filter_by(empleado_id=emp_obj.id, fecha=fecha_borrar).first()
                if asig:
                    session.delete(asig)
                    borradas_asig += 1

            # Crear/actualizar asignaciones
            for fecha, cod_turno in emp_data["turnos"].items():
                turno_obj = turnos_db.get(cod_turno)
                if not turno_obj:
                    continue
                existe = session.query(Asignacion).filter_by(empleado_id=emp_obj.id, fecha=fecha).first()
                if existe:
                    if existe.turno_id != turno_obj.id:
                        existe.turno_id = turno_obj.id
                        actualizadas_asig += 1
                else:
                    session.add(Asignacion(empleado_id=emp_obj.id, fecha=fecha, turno_id=turno_obj.id))
                    creadas_asig += 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return {
        "empleados_nuevos":      creados_emp,
        "turnos_nuevos":         creados_tur,
        "asignaciones_nuevas":   creadas_asig,
        "asignaciones_actualizadas": actualizadas_asig,
        "asignaciones_borradas": borradas_asig,
        "timestamp":             datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


# ── Función principal que usa el scheduler ────────────────────────────────
_ultimo_hash = None

def sync_si_cambio(file_id: str):
    """Descarga el archivo y sincroniza solo si cambió desde la última vez."""
    global _ultimo_hash
    try:
        data = descargar_excel_drive(file_id)
        nuevo_hash = _hash_bytes(data)
        if nuevo_hash == _ultimo_hash:
            logger.info("[Drive Sync] Sin cambios detectados.")
            return None
        logger.info("[Drive Sync] Cambio detectado — sincronizando...")
        stats = sincronizar(data)
        _ultimo_hash = nuevo_hash
        logger.info(f"[Drive Sync] Completado: {stats}")
        return stats
    except Exception as e:
        logger.error(f"[Drive Sync] Error: {e}")
        return None
