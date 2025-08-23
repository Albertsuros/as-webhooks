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

    # Teléfono
    tel_match = re.search(r'\b\d{9,}\b', mensaje)
    if tel_match:
        datos["telefono"] = tel_match.group()

    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', mensaje)
    if email_match:
        datos["email"] = email_match.group()

    # Detectar servicios de entretenimiento
    servicio_detectado = None
    
    if any(palabra in mensaje_lower for palabra in ["chistes", "chiste", "humor", "entretenimiento", "risa", "gracioso"]):
        servicio_detectado = "Chistes y Entretenimiento"
    
    if servicio_detectado:
        datos["servicio"] = servicio_detectado

    campos = ["nombre", "telefono", "email", "servicio"]
    completos = all(c in datos for c in campos)
    return datos, completos

def enviar_a_make(datos):
    try:
        url = os.getenv("MAKE_WEBHOOK_CHISTES1")
        
        print(f"=== DEBUG ENVIAR_A_MAKE (CHISTES1) ===")
        print(f"URL desde .env: {url}")
        print(f"Datos a enviar: {datos}")
        
        if not url:
            print("❌ ERROR: No hay URL de Make configurada para MAKE_WEBHOOK_CHISTES1")
            return False
            
        if not url.startswith(('http://', 'https://')):
            print(f"❌ ERROR: URL inválida - debe comenzar con http:// o https://")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'AS-Asesores-Chistes/1.0'
        }
        
        response = requests.post(
            url, 
            json=datos, 
            headers=headers,
            timeout=30
        )
        
        print(f"✅ Respuesta de Make:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Contenido: {response.text}")
        
        if response.status_code == 200:
            print("✅ Datos enviados exitosamente a Make")
            return True
        else:
            print(f"⚠️ Make respondió con código: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Timeout al conectar con Make")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se pudo conectar con Make")
        return False
    except Exception as e:
        print(f"❌ ERROR inesperado enviando a Make: {e}")
        return False

def responder_ia(mensaje_usuario, datos_actuales=None):
    try:
        contexto = ""
        if datos_actuales:
            nombre = datos_actuales.get("nombre", "")
            if nombre:
                contexto = f"(El usuario se llama {nombre}) "

        # Detectar tipo de chiste específico si se menciona
        mensaje_lower = mensaje_usuario.lower()
        tipo_chiste = ""
        
        if any(palabra in mensaje_lower for palabra in ["verde", "picante", "adulto"]):
            tipo_chiste = "un chiste verde divertido pero no ofensivo"
        elif any(palabra in mensaje_lower for palabra in ["trabajo", "oficina"]):
            tipo_chiste = "un chiste de trabajo"
        elif any(palabra in mensaje_lower for palabra in ["inteligente", "listo"]):
            tipo_chiste = "un chiste inteligente"
        else:
            tipo_chiste = "un chiste divertido y original"

        prompt = f"""{contexto}Eres Pedro, un contador de chistes muy divertido y optimista, sabes todos los chistes, los cuentas con una personalidad muy alegre, cuentas todo tipo de chistes y no los repites casi nunca, tienes todo el Internet mundial como base de datos, aunque los cuentes siempre en español. NO REPITAS NUNCA UN CHISTE.

Cuenta chistes. Responde únicamente con el chiste, sin saludos ni despedidas. No uses "jajaja", "jejeje" ni risas escritas, puedes reirtes de una forma real y natural humana para dar mas gracia en algunos chistes, otros a veces se cuentan serio, puedes hacerlo como quieras pero haciendo reir.. El chiste debe ser:
-QUE HAGA MUCHA GRACIA, no demasiado largo, muy divertido, a ser posible original pero que tenga muca gracia y lo entienda todo el mundo, de todo tipo de temas, médicos, de oficina, niños, adultos, verdes, cualquier tema que tenga gracia y n sea ofensivo para nadie. NUNCA REPITAS UN CHISTE, NI AÑADAS PALABRAS O COSAS DIFERENTES A UN CHISTE PARA QUE PAREZCA DIFERENTE, CADA CHISTE DEBE SER COMPLETAMENTE DIFERENTE DEL ANTERIOR.
- Original y divertido
- Fácil de entender
- Apropiado para síntesis de voz

Mensaje: "{mensaje_usuario}"

Responde solo con el chiste:"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=140,  # Más corto
            temperature=0.9,  # Más creatividad
            presence_penalty=0.8,  # Evita repetición
            frequency_penalty=0.7   # Penaliza palabras repetidas
        )
        
        chiste = response.choices[0].message.content.strip()
        
        # Limpiar respuesta para TTS
        chiste = chiste.replace("jajaja", "").replace("jejeje", "").replace("jiji", "")
        chiste = chiste.replace("¡Ja, ja, ja!", "").replace("¡Je, je, je!", "")
        chiste = chiste.strip()
        
        return chiste

    except Exception as e:
        print(f"Error en responder_ia: {e}")
        return "¿Qué le dice un jardinero a otro? Nos vemos cuando podamos."

def handle_chistes1_webhook(data):
    try:
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "")

        print(f"=== WEBHOOK CHISTES ===")
        print(f"Session ID: {session_id}")
        print(f"Mensaje: {mensaje_usuario}")

        if not session_id or not mensaje_usuario:
            return {"type": "speak", "text": "Faltan datos para procesar tu mensaje."}

        datos, completos = completar_datos(session_id, mensaje_usuario)

        print(f"Datos actuales (chistes1): {datos}")
        print(f"Datos completos: {completos}")

        if completos:
            print("🎯 Todos los datos completos, enviando a Make...")
            exito_envio = enviar_a_make(datos)
            
            if exito_envio:
                sessions.pop(session_id, None)
                return {"type": "speak", "text": "¡Genial! Ya tengo toda tu información. Te contactaremos pronto para seguir riéndonos juntos. ¡Que tengas un día lleno de sonrisas!"}
            else:
                return {"type": "speak", "text": "Perfecto, ya tengo tus datos. Nos pondremos en contacto contigo pronto para más diversión y entretenimiento."}
        else:
            respuesta = responder_ia(mensaje_usuario, datos)
            return {"type": "speak", "text": respuesta}

    except Exception as e:
        print(f"❌ Error en handle_chistes1_webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"type": "speak", "text": "¡Uy! Se me ha ido el santo al cielo. ¿Puedes repetir?"}