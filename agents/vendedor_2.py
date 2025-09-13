import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions = {}

def manejar_save_lead_vendedor2(data):
    """Personalizar save_lead para Vendedor 2"""
    # Añadir información específica del vendedor
    data['agente'] = 'Vendedor 2 - Comercial'
    data['notas'] = f"Lead comercial: {data.get('notas', '')}"
    
    # Llamar al endpoint principal
    import requests
    try:
        response = requests.post(
            'https://as-webhooks-production.up.railway.app/api/save_lead',
            json=data,
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

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

    # Servicio de interés
    servicio_detectado = None

    if "redes sociales" in mensaje_lower:
        servicio_detectado = "Gestión de Redes Sociales"
    elif "automatización" in mensaje_lower:
        servicio_detectado = "Automatización con IA"
    elif "asesoría" in mensaje_lower or "consultoría" in mensaje_lower:
        servicio_detectado = "Asesoría en IA"
    elif "inteligencia artificial" in mensaje_lower or "ia" in mensaje_lower:
        servicio_detectado = "Servicios de IA"

    if servicio_detectado:
        datos["servicio"] = servicio_detectado
    # Si no hay coincidencia, no se guarda nada, pero la IA seguirá conversando libremente.

    campos = ["nombre", "telefono", "email", "servicio"]
    completos = all(c in datos for c in campos)
    return datos, completos

def enviar_a_make(datos):
    try:
        url = os.getenv("MAKE_WEBHOOK_VENDEDOR_2")
        if url:
            response = requests.post(url, json=datos, timeout=10)
            print(f"Enviado a Make (Vendedor 2): {response.status_code}")
            print(f"Datos enviados: {datos}")
        else:
            print("No hay URL de Make configurada para Vendedor 2")
    except Exception as e:
        print(f"Error enviando a Make: {e}")

def responder_ia(mensaje_usuario, datos_actuales=None):
    try:
        contexto = ""
        if datos_actuales:
            for campo in ["nombre", "telefono", "email", "servicio"]:
                if campo in datos_actuales:
                    contexto += f"{campo.title()}: {datos_actuales[campo]}\n"
        
        prompt = f"""Eres el Vendedor 2 de AS Asesores. Atiendes llamadas entrantes de forma profesional y cercana para recopilar los datos necesarios para ofrecer asesoramiento en inteligencia artificial a negocios.

Necesitas recoger estos datos:
- Nombre completo
- Número de teléfono
- Email
- Servicio de interés (asesoría en IA, automatización, etc.)

Datos recopilados hasta ahora:
{contexto if contexto else "Ninguno"}

Si ya tienes todos los datos, agradece y despídete. Responde en el mismo idioma que el cliente.

Cliente: {mensaje_usuario}
Vendedor 2:"""

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

def handle_vendedor2_webhook(data):
    try:
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "")
        
        if not session_id or not mensaje_usuario:
            return {"type": "speak", "text": "Faltan datos para procesar tu mensaje."}
        
        datos, completos = completar_datos(session_id, mensaje_usuario)
        
        print(f"Datos actuales (Vendedor 2): {datos}")
        print(f"Completos: {completos}")
        
        if completos:
            enviar_a_make(datos)
            sessions.pop(session_id, None)
            return {"type": "speak", "text": "Gracias. Ya tengo toda la información. Un asesor se pondrá en contacto contigo pronto."}
        else:
            respuesta = responder_ia(mensaje_usuario, datos)
            return {"type": "speak", "text": respuesta}

    except Exception as e:
        print(f"Error en handle_vendedor2_webhook: {e}")
        return {"type": "speak", "text": "Ha ocurrido un error. Inténtalo más tarde."}