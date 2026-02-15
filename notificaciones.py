import yagmail

def enviar_correo(destino, asunto, contenido):
    yag = yagmail.SMTP("TU_CORREO@gmail.com","CLAVE_APP")
    yag.send(destino, asunto, contenido)
