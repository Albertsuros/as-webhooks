import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re
from informes import generar_y_enviar_informe_desde_agente

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

    # ✅ CORRECCIÓN 2: Detectar servicios astrológicos
    servicio_detectado = None
    
    if "carta astral" in mensaje_lower or "natal" in mensaje_lower:
        servicio_detectado = "Carta Astral"
    elif "revolución solar" in mensaje_lower or "revolusion solar" in mensaje_lower:
        servicio_detectado = "Revolución Solar"
    elif "sinastría" in mensaje_lower or "sinastria" in mensaje_lower or "compatibilidad" in mensaje_lower:
        servicio_detectado = "Sinastría"
    elif "tránsitos" in mensaje_lower or "transitos" in mensaje_lower:
        servicio_detectado = "Tránsitos"
    elif "progresiones" in mensaje_lower:
        servicio_detectado = "Progresiones"
    elif "astrología" in mensaje_lower or "astrologia" in mensaje_lower or "horóscopo" in mensaje_lower:
        servicio_detectado = "Carta Astral"  # Por defecto
    
    if servicio_detectado:
        datos["servicio"] = servicio_detectado

    campos = ["nombre", "telefono", "email", "servicio"]
    completos = all(c in datos for c in campos)
    return datos, completos

def enviar_a_make(datos):
    try:
        url = os.getenv("MAKE_WEBHOOK_ASTROLOGA_SINASTRIA")
        
        # ✅ CORRECCIÓN 3: Debugging mejorado
        print(f"=== DEBUG ENVIAR_A_MAKE (CARTA ASTRAL) ===")
        print(f"URL desde .env: {url}")
        print(f"Datos a enviar: {datos}")
        
        if not url:
            print("❌ ERROR: No hay URL de Make configurada para MAKE_WEBHOOK_ASTROLOGA_SINASTRIA")
            print("Verifica que MAKE_WEBHOOK_ASTROLOGA_SINASTRIA esté en tu archivo .env")
            return False
            
        if not url.startswith(('http://', 'https://')):
            print(f"❌ ERROR: URL inválida - debe comenzar con http:// o https://")
            return False
        
        # Agregar headers específicos
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'AS-Asesores-Astrologa-Sinastria/1.0'
        }
        
        print(f"Enviando POST a: {url}")
        print(f"Headers: {headers}")
        
        response = requests.post(
            url, 
            json=datos, 
            headers=headers,
            timeout=30
        )
        
        print(f"✅ Respuesta de Make:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
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
        print(f"Tipo de error: {type(e).__name__}")
        return False

def responder_ia(mensaje_usuario, datos_actuales=None):
    try:
        contexto = ""
        if datos_actuales:
            for campo in ["nombre", "telefono", "email", "servicio"]:
                if campo in datos_actuales:
                    contexto += f"{campo.title()}: {datos_actuales[campo]}\n"

        prompt = f"""Eres Sofía, la astróloga virtual de AS Carta Astral. Atiendes llamadas entrantes con una voz cálida y cercana para recoger los datos necesarios para generar una carta astral o interpretación personalizada.

Debes recoger:
- Nombre completo
- Número de teléfono
- Correo electrónico
- Tipo de servicio (carta astral, revolución solar, sinastría, tránsitos, progresiones, etc.)

Datos recopilados hasta ahora:
{contexto if contexto else "Ninguno"}

Si ya tienes todos los datos, agradécele al cliente y despídete con amabilidad.

Cliente: {mensaje_usuario}
astrologa_sinastria:"""

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

def handle_astrologa_sinastria_webhook(data):
    try:
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "")

        print(f"=== WEBHOOK ASTROLOGA SINASTRIA ===")
        print(f"Session ID: {session_id}")
        print(f"Mensaje: {mensaje_usuario}")

        if not session_id or not mensaje_usuario:
            return {"type": "speak", "text": "Faltan datos para procesar tu mensaje."}

        datos, completos = completar_datos(session_id, mensaje_usuario)

        print(f"Datos actuales (Astrologa - Sinastria): {datos}")
        print(f"Datos completos: {completos}")

        if completos:
            print("🎯 Todos los datos completos, enviando a Make...")
            exito_envio = enviar_a_make(datos)
            
            if exito_envio:
                # Generar informe de sinastría
                resumen = f"Resumen completo de 30 minutos sobre sinastría astrológica con todos los datos proporcionados durante la consulta."
                resultado = generar_y_enviar_informe_desde_agente(data, 'sinastria_ia', resumen)
                
                sessions.pop(session_id, None)
                return {"type": "speak", "text": "Gracias. Ya tengo toda la información. En breve recibirás tu interpretación astrológica y tu informe completo por email."}
            else:
                return {"type": "speak", "text": "Gracias por la información. Estamos procesando tu solicitud astrológica y nos contactaremos contigo pronto."}
        else:
            respuesta = responder_ia(mensaje_usuario, datos)
            return {"type": "speak", "text": respuesta}

    except Exception as e:
        print(f"❌ Error en handle_astrologa_sinastria_webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"type": "speak", "text": "Ha ocurrido un error. Inténtalo más tarde."}