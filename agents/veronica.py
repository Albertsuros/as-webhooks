import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re
from flask import request
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions = {}

def ejecutar_transferencia_telefonica():
    """WORKAROUND: Notificar y terminar para transferencia manual"""
    try:
        print(f"🔄 WORKAROUND: Ejecutando transferencia manual")
        
        # Enviar notificación urgente
        enviar_telegram_mejora(f"""
🚨 <b>TRANSFERENCIA REQUERIDA</b>

📞 <b>Cliente en:</b> +34930450975 (Verónica)
🎯 <b>Solicita:</b> Hablar con Albert
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}

🔥 <b>ACCIÓN:</b> Llama a +34930450985 YA
💨 Cliente terminará llamada en 20 segundos
        """)
        
        return {
            "type": "end_call",
            "message": "Te transfiero con Albert ahora. Te llamará en 30 segundos al mismo número."
        }
        
    except Exception as e:
        print(f"❌ Error en transferencia workaround: {e}")
        return {
            "type": "speak",
            "text": "Un momento, te conecto con mi supervisor."
        }

def handle_veronica_webhook(data):
    try:
        # ✅ FIX ANTI-LOOP - AÑADIDO
        if not data or not isinstance(data, dict):
            return {"status": "ok"}
        
        user_text = data.get('text', '').strip()
        session_id = data.get("session_id")
        
        # SI NO HAY MENSAJE Y NO HAY SESSION, ES HEALTHCHECK
        if not user_text and not session_id:
            print("🏥 HEALTHCHECK detectado - respondiendo silenciosamente")
            return {"status": "ok"}
        
        # SI MÉTODO NO ES POST, ES VALIDACIÓN
        if request.method != 'POST':
            return {"status": "ok", "message": "Veronica webhook ready"}
        
        # SOLO CONTINUAR SI HAY CONTENIDO REAL
        if not user_text or len(user_text.strip()) < 3:
            print("⚠️ Request sin contenido real")
            return {"status": "ok"}
            
            # Terminar llamada para que puedas llamar tú
            return {
                "type": "end_call",
                "message": "Te voy a transferir ahora. Albert te llamará en 30 segundos al mismo número."
            }
        
        # AGENDAR CITA SIMPLE
        if any(palabra in user_text.lower() for palabra in [
            'cita', 'hora', 'agendar', 'reunión', 'llamar'
        ]):
            return {"type": "speak", "text": "Perfecto. Te llamaremos mañana entre las 10:00 y 11:00. ¿Te parece bien?"}
        
        # Datos normales - MUY SIMPLE
        session_id = data.get("session_id", "default")
        datos, completos = completar_datos(session_id, user_text)
        
        if completos:
            print(f"✅ DATOS: {datos}")
            # Solo enviar a Make por ahora
            enviar_a_make(datos)
            return {"type": "speak", "text": "Perfecto. Te contactaremos pronto."}
        else:
            return {"type": "speak", "text": "¿Puedes darme tu nombre y teléfono?"}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"status": "ok"}  # ✅ Evitar loops en errores

def enviar_a_make(datos):
    try:
        url = os.getenv("MAKE_WEBHOOK_VERONICA")
        if url:
            response = requests.post(url, json=datos, timeout=10)
            print(f"Enviado a Make (Verónica): {response.status_code}")
            print(f"Datos enviados: {datos}")
        else:
            print("No hay URL de Make configurada para Verónica")
    except Exception as e:
        print(f"Error enviando a Make: {e}")
        
def enviar_telegram_mejora(mensaje):
    """Enviar notificación por Telegram"""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("❌ Token o Chat ID de Telegram no configurados")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("✅ Notificación Telegram enviada (Verónica)")
            return True
        else:
            print(f"❌ Error enviando Telegram: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en notificación Telegram: {e}")
        return False

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
        
# ========================================
# FUNCIONES AGENDAMIENTO VERÓNICA
# ========================================

def obtener_horarios_veronica(tipo_cita, fecha_solicitada):
    """Obtener horarios disponibles para Verónica"""
    try:
        from logica_citas_inteligente import obtener_horarios_disponibles_inteligentes
        
        tipo_servicio = f"veronica_{tipo_cita}"  # veronica_presencial o veronica_telefono
        horarios, fecha_final = obtener_horarios_disponibles_inteligentes(tipo_servicio, fecha_solicitada)
        
        return horarios, fecha_final
        
    except Exception as e:
        print(f"❌ Error horarios Verónica: {e}")
        return [], fecha_solicitada

def agendar_cita_veronica(datos_cliente, tipo_cita, fecha, horario):
    """Agendar cita con Verónica (presencial o teléfono)"""
    try:
        from logica_citas_inteligente import agendar_cita_inteligente
        
        tipo_servicio = f"veronica_{tipo_cita}"
        
        exito, resultado = agendar_cita_inteligente(
            tipo_servicio, fecha, horario, datos_cliente
        )
        
        if exito:
            # Enviar notificación Telegram
            enviar_telegram_mejora(f"""
📅 <b>NUEVA CITA - AS ASESORES</b>

👤 <b>Cliente:</b> {datos_cliente.get('nombre', 'Sin nombre')}
📧 <b>Email:</b> {datos_cliente.get('email', 'Sin email')}
📞 <b>Teléfono:</b> {datos_cliente.get('telefono', 'Sin teléfono')}
🎯 <b>Tipo:</b> {"Presencial" if tipo_cita == "presencial" else "Teléfono"}
📅 <b>Fecha:</b> {fecha.strftime('%d/%m/%Y')}
⏰ <b>Horario:</b> {horario}
🔢 <b>Código:</b> {resultado}

✅ <b>Estado:</b> Confirmada
            """.strip())
        
        return exito, resultado
        
    except Exception as e:
        print(f"❌ Error agendando cita Verónica: {e}")
        return False, str(e)

def enviar_telegram_mejora(mensaje):
    """Enviar notificación por Telegram (igual que en main.py)"""
    try:
        import os
        import requests
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("❌ Token o Chat ID de Telegram no configurados")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("✅ Notificación Telegram enviada (Verónica)")
            return True
        else:
            print(f"❌ Error enviando Telegram: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en notificación Telegram: {e}")
        return False
        
def crear_cita_google_calendar(datos):
    """Crear cita en Google Calendar cuando Verónica recoge datos completos"""
    try:
        from datetime import datetime, timedelta
        
        # Crear cita para mañana (o próximo día laboral)
        mañana = datetime.now() + timedelta(days=1)
        
        # Si es viernes, programar para lunes
        if mañana.weekday() == 5:  # Sábado
            mañana += timedelta(days=2)
        elif mañana.weekday() == 6:  # Domingo  
            mañana += timedelta(days=1)
        
        # Determinar tipo de cita según servicio
        servicio = datos.get('servicio', '').lower()
        if 'telefono' in servicio or 'llamada' in servicio:
            tipo_cita = 'veronica_telefono'
            duracion = 30
        else:
            tipo_cita = 'veronica_presencial' 
            duracion = 90
            
        # Crear evento usando función de main.py
        from main import crear_evento_calendar
        
        exito, evento_id = crear_evento_calendar(
            tipo=tipo_cita,
            nombre=datos.get('nombre', 'Cliente'),
            telefono=datos.get('telefono', ''),
            fecha=mañana.strftime('%Y-%m-%d'),
            horario='10:00-11:00',  # Horario por defecto
            codigo='',
            direccion=''
        )
        
        if exito:
            print(f"✅ Cita creada en Google Calendar: {evento_id}")
            # Notificar por Telegram
            enviar_telegram_mejora(f"""
📅 <b>NUEVA CITA AGENDADA</b>
👤 <b>Cliente:</b> {datos.get('nombre', 'Sin nombre')}
📞 <b>Teléfono:</b> {datos.get('telefono', 'Sin teléfono')}
📧 <b>Email:</b> {datos.get('email', 'Sin email')}
🎯 <b>Servicio:</b> {datos.get('servicio', 'Consulta general')}
📅 <b>Fecha:</b> {mañana.strftime('%d/%m/%Y')}
⏰ <b>Horario:</b> 10:00-11:00
🆔 <b>Evento:</b> {evento_id}
            """)
        else:
            print(f"❌ Error creando cita: {evento_id}")
            
    except Exception as e:
        print(f"❌ Error en crear_cita_google_calendar: {e}")