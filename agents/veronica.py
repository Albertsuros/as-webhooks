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

def completar_datos(session_id, mensaje):
    """Extraer datos del cliente desde el mensaje de voz"""
    try:
        if session_id not in sessions:
            sessions[session_id] = {
                'nombre': '',
                'telefono': '',
                'email': '',
                'empresa': '',
                'notas': ''
            }
        
        datos = sessions[session_id]
        mensaje_lower = mensaje.lower()
        
        # Detectar nombre
        if "me llamo" in mensaje_lower or "soy" in mensaje_lower:
            if "me llamo" in mensaje_lower:
                partes = mensaje_lower.split("me llamo")
                if len(partes) > 1:
                    nombre = partes[1].strip().split()[0]
                    if nombre:
                        datos["nombre"] = nombre.title()
            elif "soy" in mensaje_lower:
                partes = mensaje_lower.split("soy")
                if len(partes) > 1:
                    nombre = partes[1].strip().split()[0]
                    if nombre:
                        datos["nombre"] = nombre.title()
        
        # Detectar teléfono (9 dígitos mínimo)
        telefono_match = re.search(r'\b[6-9]\d{8}\b', mensaje)
        if telefono_match:
            datos["telefono"] = telefono_match.group()
        
        # Detectar email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', mensaje)
        if email_match:
            datos["email"] = email_match.group()
        
        # Detectar empresa
        empresa_patterns = [
            r'(?:empresa|compañía|trabajo en)\s+([^,\.]+)',
            r'(?:de la empresa|en)\s+([A-Z][a-zA-Z\s]+)'
        ]
        for pattern in empresa_patterns:
            empresa_match = re.search(pattern, mensaje, re.IGNORECASE)
            if empresa_match:
                datos["empresa"] = empresa_match.group(1).strip()
                break
        
        # Agregar notas adicionales
        if not any(datos.values()):  # Si no se capturó nada específico
            datos["notas"] += f" {mensaje}"
        
        # Debug
        print(f"🔍 DEBUG Verónica - Mensaje: {mensaje}")
        print(f"🔍 DEBUG Verónica - Datos extraídos: {datos}")
        
        # Verificar si están completos (al menos nombre Y teléfono)
        completos = bool(datos["nombre"] and datos["telefono"])
        
        sessions[session_id] = datos
        return datos, completos
        
    except Exception as e:
        print(f"❌ Error completar_datos Verónica: {e}")
        return sessions.get(session_id, {}), False

def handle_veronica_webhook(data):
    try:
        # Fix anti-loop
        if not data or not isinstance(data, dict):
            return {"status": "ok"}
        
        user_text = data.get('text', '').strip()
        session_id = data.get("session_id")
        
        # Healthcheck
        if not user_text and not session_id:
            print("🥽 HEALTHCHECK detectado - respondiendo silenciosamente")
            return {"status": "ok"}
        
        if request.method != 'POST':
            return {"status": "ok", "message": "Veronica webhook ready"}
        
        if not user_text or len(user_text.strip()) < 3:
            print("⚠️ Request sin contenido real")
            return {"status": "ok"}
        
        print(f"=== VERÓNICA WEBHOOK ===")
        print(f"Session ID: {session_id}")
        print(f"Mensaje: {user_text}")
        # DEBUG ADICIONAL
        print(f"🔍 DEBUG - Función ejecutada correctamente")
        print(f"🔍 DEBUG - Session ID: {session_id}")
        print(f"🔍 DEBUG - Texto limpio: '{mensaje_usuario}'")
        
        # Completar datos del cliente
        datos, completos = completar_datos(session_id, user_text)
        
        if completos:
            print(f"✅ DATOS COMPLETOS: {datos}")
            
            # Enviar notificación Telegram con datos
            mensaje_telegram = f"""
🤖 <b>NUEVA CONSULTA - AS ASESORES</b>

👤 <b>Cliente:</b> {datos.get('nombre', 'Sin nombre')}
🏢 <b>Empresa:</b> {datos.get('empresa', 'Sin empresa')}
📞 <b>Teléfono:</b> {datos.get('telefono', 'Sin teléfono')}
📧 <b>Email:</b> {datos.get('email', 'Sin email')}
📝 <b>Notas:</b> {datos.get('notas', 'Sin notas')}

👩‍💼 <b>Agente:</b> Verónica
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}
✅ <b>Estado:</b> Registrado para seguimiento
            """.strip()
            
            enviar_telegram_mejora(mensaje_telegram)
            
            return {"type": "speak", "text": "Perfecto. He registrado todos tus datos. Te contactaremos pronto para ayudarte."}
        else:
            # Pedir más datos
            if not datos.get('nombre'):
                return {"type": "speak", "text": "¿Puedes decirme tu nombre, por favor?"}
            elif not datos.get('telefono'):
                return {"type": "speak", "text": "¿Cuál es tu número de teléfono de contacto?"}
            else:
                return {"type": "speak", "text": "¿Hay algo más que quieras añadir sobre tu consulta?"}

    except Exception as e:
        print(f"❌ Error en handle_veronica_webhook: {e}")
        return {"status": "ok"}
        
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
