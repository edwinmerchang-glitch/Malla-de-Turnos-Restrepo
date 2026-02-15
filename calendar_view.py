from streamlit_calendar import calendar

def mostrar_calendario(df):

    eventos = []
    for _, row in df.iterrows():
        eventos.append({
            "title": f"{row['empleado']} - {row['turno']}",
            "start": row['fecha']
        })

    calendar(events=eventos, options={"initialView": "dayGridMonth"})
