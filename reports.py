import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def resumen_mensual(session):
    from database import Asignacion, Empleado

    data = session.query(Asignacion).all()
    emp = session.query(Empleado).all()
    mapa = {e.id: {"nombre": e.nombre, "area": e.area, "cargo": e.cargo} for e in emp}

    df = pd.DataFrame([(a.fecha, a.turno, a.empleado_id) for a in data],
                      columns=["Fecha", "Turno", "EmpleadoID"])

    df["Empleado"] = df["EmpleadoID"].map(lambda x: mapa[x]["nombre"] if x in mapa else "N/A")
    df["Área"] = df["EmpleadoID"].map(lambda x: mapa[x]["area"] if x in mapa and mapa[x]["area"] else "N/A")
    df["Cargo"] = df["EmpleadoID"].map(lambda x: mapa[x]["cargo"] if x in mapa and mapa[x]["cargo"] else "N/A")
    df["Mes"] = pd.to_datetime(df["Fecha"]).dt.month

    return df

def resumen_por_area(session):
    """Genera resumen de turnos por área"""
    from database import Asignacion, Empleado
    
    data = session.query(Asignacion).all()
    empleados = {e.id: e for e in session.query(Empleado).all()}
    
    resumen = {}
    for a in data:
        if a.empleado_id in empleados:
            emp = empleados[a.empleado_id]
            area = emp.area if emp.area else "Sin área"
            
            if area not in resumen:
                resumen[area] = {
                    "total_turnos": 0,
                    "empleados": set(),
                    "turnos_por_empleado": {}
                }
            
            resumen[area]["total_turnos"] += 1
            resumen[area]["empleados"].add(emp.nombre)
    
    # Convertir a DataFrame
    datos = []
    for area, stats in resumen.items():
        datos.append({
            "Área": area,
            "Total turnos": stats["total_turnos"],
            "Empleados": len(stats["empleados"]),
            "Promedio turnos/empleado": round(stats["total_turnos"] / len(stats["empleados"]), 1)
        })
    
    return pd.DataFrame(datos)

def exportar_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")
    buffer.seek(0)
    return buffer

def exportar_pdf(df, titulo="Reporte de Turnos"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 2*cm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, y, titulo)

    y -= 1*cm
    c.setFont("Helvetica", 9)

    for col in df.columns:
        c.drawString(2*cm, y, col)
        y -= 0.5*cm

    y -= 0.5*cm

    for _, row in df.iterrows():
        texto = " | ".join(str(v) for v in row.values)
        c.drawString(2*cm, y, texto)
        y -= 0.45*cm

        if y < 2*cm:
            c.showPage()
            y = height - 2*cm

    c.save()
    buffer.seek(0)
    return buffer