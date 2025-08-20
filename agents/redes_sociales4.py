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

    tel_match = re.search(r'\b\d{9,}\b', mensaje)
    if tel_match:
        datos["telefono"] = tel_match.group()

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', mensaje)
    if email_match:
        datos["email"] = email_match.group()

    # Servicio de interés - REDES SOCIALES
    servicio_detectado = None

    if any(palabra in mensaje_lower for palabra in ["redes", "sociales", "social", "instagram", "facebook", "twitter"]):
        servicio_detectado = "Gestión de Redes Sociales"
    elif any(palabra in mensaje_lower for palabra in ["automatización", "automatizar"]):
        servicio_detectado = "Automatización con IA"
    elif any(palabra in mensaje_lower for palabra in ["buscar", "empresas", "empresa"]):
        servicio_detectado = "Busca empresas"
    elif "asesoría" in mensaje_lower or "consultoría" in mensaje_lower:
        servicio_detectado = "Asesoría en IA"
    elif "inteligencia artificial" in mensaje_lower or "ia" in mensaje_lower:
        servicio_detectado = "Servicios de IA"

    if servicio_detectado:
        datos["servicio"] = servicio_detectado

    campos = ["nombre", "telefono", "email", "servicio"]
    completos = all(c in datos for c in campos)
    return datos, completos

def enviar_a_make(datos):
    try:
        url = os.getenv("MAKE_WEBHOOK_REDES_SOCIALES4")
        if url:
            response = requests.post(url, json=datos, timeout=10)
            print(f"Enviado a Make (Redes Sociales4): {response.status_code}")
            print(f"Datos enviados: {datos}")
        else:
            print("No hay URL de Make configurada para Redes Sociales4")
    except Exception as e:
        print(f"Error enviando a Make: {e}")

def responder_ia(mensaje_usuario, datos_actuales=None):
    try:
        contexto = ""
        if datos_actuales:
            for campo in ["nombre", "telefono", "email", "servicio"]:
                if campo in datos_actuales:
                    contexto += f"{campo.title()}: {datos_actuales[campo]}\n"
        
        prompt = f"""Eres el agente de redes sociales número 4 de AS Asesores. Atiendes llamadas o chats para captar empresas interesadas en la gestión profesional de sus redes sociales y otros servicios relacionados con inteligencia artificial.

Necesitas recopilar:
- Nombre de la persona de contacto
- Número de teléfono
- Email
- Servicio que le interesa (gestión redes, automatización, IA, etc.)

Datos recopilados hasta ahora:
{contexto if contexto else "Ninguno"}

Si ya tienes todos los datos, agradece y termina. Responde en el mismo idioma del cliente.

Cliente: {mensaje_usuario}
Redes_Sociales4:"""

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


def handle_redes_sociales4_webhook(data):
    try:
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "")
        
        if not session_id or not mensaje_usuario:
            return {"type": "speak", "text": "Faltan datos para procesar tu mensaje."}
        
        datos, completos = completar_datos(session_id, mensaje_usuario)
        
        print(f"Datos actuales (Redes Sociales4): {datos}")
        print(f"Completos: {completos}")
        
        if completos:
            enviar_a_make(datos)
            sessions.pop(session_id, None)
            return {"type": "speak", "text": "Gracias. Ya he anotado todos los datos. Nuestro equipo se pondrá en contacto contigo en breve."}
        else:
            respuesta = responder_ia(mensaje_usuario, datos)
            return {"type": "speak", "text": respuesta}

    except Exception as e:
        print(f"Error en handle_redes_sociales4_webhook: {e}")
        return {"type": "speak", "text": "Ha ocurrido un error. Inténtalo más tarde."}