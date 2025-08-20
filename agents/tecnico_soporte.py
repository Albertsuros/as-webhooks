import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions = {}

def completar_datos(session_id, mensaje):
    if session_id not in sessions:
        sessions[session_id] = {}
    
    datos = sessions[session_id]
    mensaje_lower = mensaje.lower()

    # Nombre
    if "me llamo" in mensaje_lower or "soy" in mensaje_lower:
        if "me llamo" in mensaje_lower:
            partes = mensaje_lower.split("me llamo")
            if len(partes) > 1:
                nombre_parte = partes[1].strip()
                nombre = nombre_parte.split()[0] if nombre_parte else ""
                if nombre:
                    datos["nombre"] = nombre.title()
        elif "soy" in mensaje_lower:
            partes = mensaje_lower.split("soy")
            if len(partes) > 1:
                nombre_parte = partes[1].strip()
                nombre = nombre_parte.split()[0] if nombre_parte else ""
                if nombre:
                    datos["nombre"] = nombre.title()

    # Servicio de soporte técnico si se detectan ciertas palabras
    servicio_detectado = None
    if "problema" in mensaje_lower or "ayuda" in mensaje_lower or "webhook" in mensaje_lower or "soporte" in mensaje_lower:
        servicio_detectado = "Soporte técnico"
    elif "make" in mensaje_lower or "configuración" in mensaje_lower:
        servicio_detectado = "Soporte técnico"

    if servicio_detectado:
        datos["servicio"] = servicio_detectado

    # Teléfono (buscar números de 9 dígitos o más)
    tel_match = re.search(r'\b\d{9,}\b', mensaje)
    if tel_match:
        datos["telefono"] = tel_match.group()

    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', mensaje)
    if email_match:
        datos["email"] = email_match.group()

    # Servicio de interés (palabras clave)
    if "asesoría" in mensaje_lower or "consultoría" in mensaje_lower:
        datos["servicio"] = "Asesoría en IA"
    elif "automatización" in mensaje_lower:
        datos["servicio"] = "Automatización con IA"
    elif "inteligencia artificial" in mensaje_lower or "ia" in mensaje_lower:
        datos["servicio"] = "Servicios de IA"

    campos = ["nombre", "telefono", "email", "servicio"]
    completos = all(c in datos for c in campos)
    return datos, completos

def enviar_a_make(datos):
    try:
        url = os.getenv("MAKE_WEBHOOK_TECNICO_SOPORTE")
        if url:
            response = requests.post(url, json=datos, timeout=10)
            print(f"Enviado a Make (Tecnico soporte): {response.status_code}")
            print(f"Datos enviados: {datos}")
        else:
            print("No hay URL de Make configurada para Tecnico_soporte")
    except Exception as e:
        print(f"Error enviando a Make: {e}")

def responder_ia(mensaje_usuario, datos_actuales=None):
    try:
        contexto = ""
        if datos_actuales:
            for campo in ["nombre", "telefono", "email", "servicio"]:
                if campo in datos_actuales:
                    contexto += f"{campo.title()}: {datos_actuales[campo]}\n"
        
        prompt = f"""Eres Verónica, la secretaria virtual de AS Asesores. Atiendes llamadas entrantes de forma profesional y cálida para recopilar los datos necesarios para una asesoría empresarial en inteligencia artificial.

Necesitas recoger estos datos:
- Nombre completo
- Número de teléfono
- Email
- Servicio de interés (asesoría en IA, automatización, etc.)

Datos recopilados hasta ahora:
{contexto if contexto else "Ninguno"}

Si ya tienes todos los datos, agradece y despídete. Responde en el mismo idioma que el cliente.

Cliente: {mensaje_usuario}
Verónica:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error en responder_ia: {e}")
        return "Disculpa, ha ocurrido un error. ¿Podrías repetir?"

def handle_tecnico_soporte_webhook(data):
    try:
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "")
        
        if not session_id or not mensaje_usuario:
            return {"type": "speak", "text": "Faltan datos para procesar tu mensaje."}
        
        datos, completos = completar_datos(session_id, mensaje_usuario)
        
        print(f"Datos actuales (Verónica): {datos}")
        print(f"Completos: {completos}")
        
        if completos:
            enviar_a_make(datos)
            sessions.pop(session_id, None)
            return {"type": "speak", "text": "Gracias. Ya tengo toda la información. Un asesor se pondrá en contacto contigo pronto."}
        else:
            respuesta = responder_ia(mensaje_usuario, datos)
            return {"type": "speak", "text": respuesta}

    except Exception as e:
        print(f"Error en handle_tecnico_soporte_webhook: {e}")
        return {"type": "speak", "text": "Ha ocurrido un error. Inténtalo más tarde."}