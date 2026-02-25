import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def resumen_mensual(session):
    from database import Asignacion, Empleado

    data = session.query(Asignacion).all()
    emp = session.query(Empleado).all()
    mapa = {e.id: e.nombre for e in emp}

    df = pd.DataFrame([(a.fecha, a.turno, a.empleado_id) for a in data],
                      columns=["Fecha", "Turno", "EmpleadoID"])

    df["Empleado"] = df["EmpleadoID"].map(mapa)
    df["Mes"] = pd.to_datetime(df["Fecha"]).dt.month

    return df.groupby(["Empleado", "Mes"]).size().reset_index(name="Total Turnos")

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