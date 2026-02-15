import pandas as pd

def generar_reporte(df):
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["semana"] = df["fecha"].dt.isocalendar().week
    resumen = df.groupby(["semana","empleado"])["turno"].count().reset_index()
    resumen.columns = ["Semana","Empleado","Turnos"]
    return resumen
