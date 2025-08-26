import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import re
import sys
import json
import matplotlib.pyplot as plt
import gc
import time
from email_photo_processor import buscar_fotos_cliente_email, marcar_fotos_como_procesadas
from datetime import datetime, timedelta

# IMPORTACIONES para generar cartas astrales
from carta_natal import CartaAstralNatal
from progresiones import generar_progresiones_personalizada as generar_progresiones
from transitos import generar_transitos_personalizada as generar_transitos

# IMPORTACIONES para revolución solar
from revolucion_sola import generar_revolucion_solar_sola_personalizada as generar_revolucion_sola
from revolucion_natal import generar_revolucion_solar_personalizada as generar_revolucion_natal

# IMPORTACIONES para astrología horaria y sinastría
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from astrol_horaria import main as generar_astrologia_horaria
from sinastria import main as generar_sinastria

# IMPORTAR SISTEMA DE SEGUIMIENTO (que ya tienes funcionando)
from sistema_seguimiento import SeguimientoTelefonico, obtener_numero_telefono_desde_vapi

# IMPORTACIONES para email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions = {}

# Inicializar sistema de seguimiento
seguimiento = SeguimientoTelefonico()

# DURACIONES DE SESIÓN POR SERVICIO (en minutos)
DURACIONES_SERVICIO = {
    'carta_astral_ia': 40,
    'revolucion_solar_ia': 50,
    'sinastria_ia': 30,
    'astrologia_horaria_ia': 15,
    'psico_coaching_ia': 45,
    'lectura_manos_ia': 30,
    'lectura_facial_ia': 15,
    'astrologo_humano': 60,
    'tarot_humano': 60,
    # EXTENSIONES ½ TIEMPO
    'carta_astral_ia_half': 20,
    'revolucion_solar_ia_half': 25,
    'sinastria_ia_half': 15,
    'lectura_manos_ia_half': 15,
    'psico_coaching_ia_half': 20,
    'grafologia_ia': 30
}

def verificar_sesion_activa(telefono):
    """Verificar si hay sesión cortada recientemente (últimos 5 minutos)"""
    try:
        if not telefono:
            return None
            
        # Buscar sesión activa o recién cortada
        sesion = seguimiento.buscar_sesion_activa(telefono)
        
        if sesion:
            # Verificar si la sesión se cortó hace menos de 5 minutos
            from datetime import datetime, timedelta
            ahora = datetime.now()
            fecha_exp = datetime.fromisoformat(sesion['fecha_expiracion'])
            
            # Si aún está en el período de reconexión O se cortó hace menos de 5 minutos
            if ahora < fecha_exp:
                # Sesión aún válida para reconexión
                return sesion
            elif (ahora - fecha_exp).total_seconds() < 300:
                # Se cortó hace menos de 5 minutos - permitir reconexión
                print(f"🚨 Detectada llamada cortada hace {int((ahora - fecha_exp).total_seconds())} segundos")
                enviar_notificacion_llamada_cortada(telefono, sesion)
                return sesion
                
        return None
        
    except Exception as e:
        print(f"❌ Error verificando sesión activa: {e}")
        return None

def manejar_reconexion(sesion_activa, data):
    """Manejar reconexión después de llamada cortada"""
    try:
        tiempo_restante = datetime.fromisoformat(sesion_activa['fecha_expiracion']) - datetime.now()
        horas_restantes = max(0, int(tiempo_restante.total_seconds() / 3600))
        
        # Mensaje de reconexión
        mensaje_reconexion = f"¡Hola de nuevo! Continuamos tu {sesion_activa['tipo_servicio']}. Te quedan {horas_restantes} horas para seguir nuestra conversación."
        
        # Actualizar que se reconectó
        seguimiento.actualizar_conversacion(sesion_activa['id'], {
            'tipo': 'reconexion_automatica',
            'mensaje': 'Cliente se reconectó después de corte'
        })
        
        # Transferir directo al especialista
        especialistas = {
            'carta_astral_ia': 'asst_78f4bfbd-cf67-46cb-910d-c8f0f8adf3fc',
            'revolucion_solar_ia': 'asst_9513ec30-f231-4171-959c-26c8588d248e', 
            'sinastria_ia': 'asst_9960b33c-db72-4ebd-ae3e-69ce6f7e6660',
            'astrologia_horaria_ia': 'asst_d218cde4-d4e1-4943-8fd9-a1df9404ebd6',
            'psico_coaching_ia': 'asst_63a0f9b9-c5d5-4df6-ba6f-52d700b51275',
            'lectura_manos_ia': 'asst_8473d3ab-22a7-479c-ae34-427e992023de',
            'lectura_facial_ia': 'asst_9cae2faa-2a8e-498b-b8f4-ab7af65bf734',
            'grafologia_ia': 'asst_84c67029-8059-4066-a5ae-8532b99fd24c'
        }
        
        especialista = especialistas.get(sesion_activa['tipo_servicio'])
        
        if especialista:
            return {
                "type": "transfer_call",
                "transfer": {"type": "assistant", "assistantId": especialista},
                "data_extra": {
                    "sesion_activa": sesion_activa,
                    "reconexion_automatica": True
                },
                "speak_first": mensaje_reconexion
            }
        else:
            return {"type": "speak", "text": mensaje_reconexion}
            
    except Exception as e:
        print(f"❌ Error manejando reconexión: {e}")
        return {"type": "speak", "text": "¡Hola de nuevo! ¿En qué puedo ayudarte?"}

def enviar_notificacion_llamada_cortada(numero_telefono, sesion_data=None):
    """Enviar email de notificación cuando se corta una llamada"""
    try:
        # Email del administrador
        email_admin = os.getenv("EMAIL_ADMIN", "albertsg@yahoo.es")
        
        # Preparar datos
        telefono = numero_telefono or "Número no disponible"
        servicio = sesion_data.get('tipo_servicio', 'No especificado') if sesion_data else 'No especificado'
        cliente_email = sesion_data.get('email', 'No proporcionado') if sesion_data else 'No proporcionado'
        nombre = sesion_data.get('datos_natales', {}).get('nombre', 'No proporcionado') if sesion_data else 'No proporcionado'
        
        # Crear mensaje
        asunto = f"🚨 Llamada cortada - {servicio}"
        cuerpo = f"""
ALERTA: Se ha cortado una llamada

📞 TELÉFONO: {telefono}
👤 CLIENTE: {nombre}
📧 EMAIL: {cliente_email}
🔮 SERVICIO: {servicio}
⏰ FECHA/HORA: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

---
Sistema de notificaciones automático
        """
        
        # Enviar email
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        email_sender = os.getenv("EMAIL_SENDER")
        email_password = os.getenv("EMAIL_PASSWORD")
        
        if email_sender and email_password:
            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = email_admin
            msg['Subject'] = asunto
            msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_sender, email_password)
            server.sendmail(email_sender, email_admin, msg.as_string())
            server.quit()
            
            print(f"✅ Email de notificación enviado para llamada cortada: {telefono}")
            return True
        else:
            print("❌ Credenciales de email no configuradas")
            return False
            
    except Exception as e:
        print(f"❌ Error enviando notificación de llamada cortada: {e}")
        return False

def obtener_horarios_disponibles_sofia(tipo_servicio, fecha_solicitada=None):
    """Obtener horarios disponibles usando lógica inteligente"""
    try:
        from logica_citas_inteligente import obtener_horarios_disponibles_inteligentes
        
        if not fecha_solicitada:
            from datetime import datetime, timedelta
            fecha_solicitada = datetime.now() + timedelta(days=1)
        
        horarios, fecha_final = obtener_horarios_disponibles_inteligentes(tipo_servicio, fecha_solicitada)
        return horarios
        
    except Exception as e:
        print(f"❌ Error en horarios Sofia: {e}")
        return []

def verificar_horario_disponible_sofia(tipo_servicio, fecha, horario):
    """Verificar si un horario específico está disponible desde Sofia"""
    try:
        import sqlite3
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Verificar en la nueva estructura de BD
        cur.execute("""
        SELECT COUNT(*) 
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE cs.tipo_servicio = ? AND ca.fecha_cita = ? AND ca.horario = ? AND ca.estado_cita != 'cancelada'
        """, (tipo_servicio, fecha.strftime('%Y-%m-%d'), horario))
        
        count = cur.fetchone()[0]
        conn.close()
        
        return count == 0  # True si está libre, False si está ocupado
        
    except Exception as e:
        print(f"❌ Error verificando disponibilidad desde Sofia: {e}")
        return True  # En caso de error, asumir que está libre

def agendar_cita_humana_sofia(datos_cliente, tipo_servicio, horario_elegido, fecha_elegida, codigo_servicio):
    """Agendar cita para astrólogo o tarot humano desde Sofia CON BD COMPLETA"""
    try:
        # IMPORTAR FUNCIONES DESDE MAIN.PY
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        nombre = datos_cliente.get('nombre', 'Cliente')
        email = datos_cliente.get('email', '')
        telefono = datos_cliente.get('telefono', '')
        
        # 1. REGISTRAR CLIENTE EN TABLA PRINCIPAL (como todos los servicios)
        try:
            from main import registrar_cliente_servicio, agendar_cita_especifica
            
            cliente_id = registrar_cliente_servicio(
                codigo_servicio=codigo_servicio,
                tipo_servicio=tipo_servicio,
                cliente_datos=datos_cliente,
                numero_telefono=telefono,
                especialista="Pendiente asignación"
            )
            
            if not cliente_id:
                return False, {"error": "Error registrando cliente"}
            
            # 2. AGENDAR CITA ESPECÍFICA (adicional para servicios humanos)
            exito, codigo_reserva = agendar_cita_especifica(cliente_id, fecha_elegida, horario_elegido, tipo_servicio)
            
            if not exito:
                return False, {"error": codigo_reserva}
                
        except ImportError:
            # Fallback si no se pueden importar las funciones de main.py
            return False, {"error": "Error del sistema - funciones no disponibles"}
        
        servicio_nombre = {
            'astrologo_humano': 'Astrólogo Personal (1 hora)',
            'tarot_humano': 'Tarot Personal (1 hora)'
        }.get(tipo_servicio, 'Consulta Personal')
        
        confirmacion = {
            'tipo': 'cita_agendada',
            'servicio': servicio_nombre,
            'cliente': nombre,
            'email': email,
            'telefono': telefono,
            'fecha': fecha_elegida.strftime("%d/%m/%Y"),
            'horario': horario_elegido,
            'codigo_reserva': codigo_reserva,
            'fecha_agendamiento': datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        
        print(f"✅ Cliente + Cita registrados desde Sofia: {servicio_nombre} - {fecha_elegida.strftime('%d/%m/%Y')} {horario_elegido}")
        return True, confirmacion
        
    except Exception as e:
        print(f"❌ Error agendando cita desde Sofia: {e}")
        return False, {"error": str(e)}

def enviar_email_instrucciones_fotos(email_cliente, nombre_cliente, tipo_servicio):
    """Enviar email con instrucciones para subir fotos"""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        email_sender = os.getenv("EMAIL_SENDER")
        email_password = os.getenv("EMAIL_PASSWORD")
        
        if tipo_servicio == 'lectura_manos_ia':
            asunto = "📸 Instrucciones para tu lectura de manos"
            cuerpo = f"""
Hola {nombre_cliente},

Para tu sesión de lectura de manos, necesitamos las fotos de tus palmas.

📧 RESPONDE ESTE EMAIL con:
📸 Foto de tu mano izquierda (palma abierta, bien iluminada)
📸 Foto de tu mano derecha (palma abierta, bien iluminada)
✋ Indica si eres diestro o zurdo

Una vez enviadas las fotos, llama al mismo número con el mismo teléfono para continuar tu sesión.

¡Gracias!
Equipo Sofía

---
IMPORTANTE: Las fotos deben ser claras y con buena iluminación para una lectura precisa.
            """
        elif tipo_servicio == 'lectura_facial_ia':
            asunto = "📸 Instrucciones para tu lectura facial"
            cuerpo = f"""
Hola {nombre_cliente},

Para tu sesión de lectura facial, necesitamos 3 fotos específicas.

📧 RESPONDE ESTE EMAIL con:
📸 Foto frontal de tu cara (mirando de frente)
📸 Foto diagonal derecha (tu cara girada 45° a la derecha)
📸 Foto diagonal izquierda (tu cara girada 45° a la izquierda)

Una vez enviadas las fotos, llama al mismo número con el mismo teléfono para continuar tu sesión.

¡Gracias!
Equipo Sofía

---
IMPORTANTE: Las fotos deben ser claras, con buena iluminación y sin filtros.
            """
        elif tipo_servicio == 'grafologia_ia':
            asunto = "📝 Instrucciones para tu análisis grafológico"
            cuerpo = f"""
Hola {nombre_cliente},

Para tu análisis grafológico, necesitamos una muestra de tu escritura.

📧 RESPONDE ESTE EMAIL con:
📝 Escribe a mano un texto de al menos 5 líneas (cuantas mas líneas mejor) sobre ti mismo
📸 Foto clara de la escritura (buena iluminación, letra legible)
✍️ Indica si eres diestro o zurdo

TEXTO SUGERIDO: "Me llamo [tu nombre], tengo [edad] años. Me gusta... Mi trabajo es... En mi tiempo libre... Lo que más me emociona es... Mi mayor sueño es..."

Una vez enviada la muestra, llama al mismo número para continuar tu sesión.

¡Gracias!
Equipo Sofía

---
IMPORTANTE: La escritura debe ser natural, en papel blanco y con bolígrafo azul o negro.
    """
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = email_sender
        msg['To'] = email_cliente
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        
        # Enviar email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_sender, email_password)
        text = msg.as_string()
        server.sendmail(email_sender, email_cliente, text)
        server.quit()
        
        print(f"✅ Email de instrucciones enviado a {email_cliente}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False

def validar_codigo_servicio(codigo):
    """Validar código de servicio con reconocimiento flexible"""
    if not codigo:
        return False, None
    
    # Limpiar y normalizar el código
    codigo_original = codigo
    codigo = codigo.upper().strip()
    
    # REMOVER PALABRAS COMUNES DEL RECONOCIMIENTO DE VOZ
    palabras_ignorar = [
        'GUION', 'GUIÓN', 'DASH', 'UNDERSCORE', 'BAJO', 
        'MENOS', 'RAYA', 'BARRA', 'SPACE', 'ESPACIO'
    ]
    
    for palabra in palabras_ignorar:
        codigo = codigo.replace(palabra, '')
    
    # REMOVER ESPACIOS Y CARACTERES ESPECIALES
    codigo = codigo.replace(' ', '').replace('-', '').replace('_', '')
    
    print(f"🔍 DEBUG: '{codigo_original}' → '{codigo}'")
    
    # PATTERNS FLEXIBLES (sin guión bajo, solo letras+números)
    import re
    
    # Patrones de 8-9 caracteres: AI123456 o AIM123456
    patterns = [
        r'^(AI|RS|SI|AH|PC|LM|LF|GR)(\d{6})$',        # AI123456
        r'^(AIM|RSM|SIM|LMM|PCM)(\d{6})$',             # AIM123456  
        r'^(AS|TH)(\d{6})$'                            # AS123456, TH123456
    ]
    
    for pattern in patterns:
        match = re.match(pattern, codigo)
        if match:
            prefijo = match.group(1)
            numeros = match.group(2)
            
            # RECONSTRUIR CÓDIGO EN FORMATO CORRECTO
            if prefijo in ['AIM', 'RSM', 'SIM', 'LMM', 'PCM']:
                codigo_final = f"{prefijo}{numeros}"  # Sin guión para extensiones
            else:
                codigo_final = f"{prefijo}_{numeros}"  # Con guión para normales
            
            # MAPEO A TIPOS DE SERVICIO
            tipos_servicio = {
                'AI_': 'carta_astral_ia',
                'RS_': 'revolucion_solar_ia', 
                'SI_': 'sinastria_ia',
                'AH_': 'astrologia_horaria_ia',
                'PC_': 'psico_coaching_ia',
                'LM_': 'lectura_manos_ia',
                'LF_': 'lectura_facial_ia',
                'GR_': 'grafologia_ia',
                'AS_': 'astrologo_humano',
                'TH_': 'tarot_humano',
                'AIM': 'carta_astral_ia_half',
                'RSM': 'revolucion_solar_ia_half',
                'SIM': 'sinastria_ia_half',
                'LMM': 'lectura_manos_ia_half',
                'PCM': 'psico_coaching_ia_half'
            }
            
            # Buscar tipo de servicio
            for prefijo_tipo, tipo in tipos_servicio.items():
                if codigo_final.startswith(prefijo_tipo):
                    print(f"✅ CÓDIGO RECONOCIDO: '{codigo_original}' → '{codigo_final}' → {tipo}")
                    return True, tipo
    
    print(f"❌ CÓDIGO NO VÁLIDO: '{codigo_original}' → '{codigo}'")
    return False, None

# TAMBIÉN AÑADIR FUNCIÓN DE DEBUG
def debug_reconocimiento_codigo(mensaje_usuario):
    """Debug para ver cómo se reconoce el código"""
    print(f"🎤 AUDIO RECONOCIDO: '{mensaje_usuario}'")
    
    # Intentar extraer posibles códigos
    import re
    
    # Buscar patrones de código en el mensaje
    posibles_codigos = re.findall(r'\b[A-Z]{2,3}[_\s\-]*\d{6}\b', mensaje_usuario.upper())
    
    for posible in posibles_codigos:
        valido, tipo = validar_codigo_servicio(posible)
        print(f"   🔍 Encontrado: '{posible}' → Válido: {valido} → Tipo: {tipo}")
    
    return posibles_codigos

# ACTUALIZAR handle_sofia_webhook para usar debug
# Añadir al inicio de handle_sofia_webhook, después de print(f"Mensaje: {mensaje_usuario}")

def detectar_email(mensaje):
    """Detectar email en el mensaje"""
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', mensaje)
    return email_match.group() if email_match else None

def detectar_preferencia_año(mensaje):
    """Detectar preferencia de año para revolución solar"""
    mensaje_lower = mensaje.lower()
    
    # Palabras clave para año actual
    palabras_actual = ['actual', 'este año', '2025', 'ahora', 'presente', 'ya']
    
    # Palabras clave para próximo cumpleaños
    palabras_proximo = ['próximo', 'siguiente', 'cumpleaños', 'próxima', 'futura', '2026']
    
    for palabra in palabras_actual:
        if palabra in mensaje_lower:
            return 'actual'
    
    for palabra in palabras_proximo:
        if palabra in mensaje_lower:
            return 'proximo'
    
    return None

def completar_datos_natales(datos_actuales, mensaje, tipo_servicio):
    """Completar datos natales según el tipo de servicio"""
    mensaje_lower = mensaje.lower()

    # Detectar nombre
    if "me llamo" in mensaje_lower or "soy" in mensaje_lower:
        if "me llamo" in mensaje_lower:
            partes = mensaje_lower.split("me llamo")
            if len(partes) > 1:
                nombre = partes[1].strip().split()[0]
                if nombre:
                    datos_actuales["nombre"] = nombre.title()
                    
    # Detectar edad
    edad_patterns = [
        r'tengo (\d{1,2}) años',
        r'(\d{1,2}) años',
        r'edad (\d{1,2})',
        r'soy de (\d{1,2})'
    ]
    
    for pattern in edad_patterns:
        edad_match = re.search(pattern, mensaje_lower)
        if edad_match:
            edad = edad_match.group(1)
            if 10 <= int(edad) <= 99:
                datos_actuales["edad"] = edad
            break

    # Detectar fecha de nacimiento
    fecha_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', mensaje)
    if fecha_match:
        dia, mes, año = fecha_match.groups()
        datos_actuales["fecha_nacimiento"] = f"{dia:0>2}/{mes:0>2}/{año}"

    # Detectar hora
    hora_match = re.search(r'(\d{1,2}):(\d{2})', mensaje)
    if hora_match:
        hora, minuto = hora_match.groups()
        datos_actuales["hora_nacimiento"] = f"{hora:0>2}:{minuto:0>2}"

    # Detectar lugar de nacimiento
    lugar_patterns = [
        r'(?:en|de|desde)\s+([^,]+)(?:,\s*([^,]+))?',
        r'(?:nací|nacido|nacida)\s+en\s+([^,]+)(?:,\s*([^,]+))?'
    ]
    
    for pattern in lugar_patterns:
        lugar_match = re.search(pattern, mensaje_lower)
        if lugar_match:
            ciudad = lugar_match.group(1).strip().title()
            pais = lugar_match.group(2).strip().title() if lugar_match.group(2) else "España"
            datos_actuales["lugar_nacimiento"] = f"{ciudad}, {pais}"

    # Detectar residencia actual
    residencia_patterns = [
        r'(?:vivo|resido|estoy)\s+en\s+([^,]+)(?:,\s*([^,]+))?',
        r'(?:residencia|actual)\s+([^,]+)(?:,\s*([^,]+))?'
    ]
    
    for pattern in residencia_patterns:
        res_match = re.search(pattern, mensaje_lower)
        if res_match:
            ciudad_res = res_match.group(1).strip().title()
            pais_res = res_match.group(2).strip().title() if res_match.group(2) else "España"
            datos_actuales["residencia_actual"] = f"{ciudad_res}, {pais_res}"

    # LÓGICA ESPECÍFICA PARA ASTROLOGÍA HORARIA
    if tipo_servicio == 'astrologia_horaria_ia':
        # Detectar pregunta
        if "pregunta" in mensaje_lower or "quiero saber" in mensaje_lower or "¿" in mensaje:
            if "pregunta" in mensaje_lower:
                partes = mensaje.split("pregunta")
                if len(partes) > 1:
                    pregunta = partes[1].strip().strip(":").strip()
                    if pregunta:
                        datos_actuales["pregunta"] = pregunta
            elif "¿" in mensaje:
                datos_actuales["pregunta"] = mensaje.strip()
            else:
                datos_actuales["pregunta"] = mensaje.strip()
        
        # Detectar momento (actual vs específico)
        if "ahora" in mensaje_lower or "momento actual" in mensaje_lower or "en este momento" in mensaje_lower:
            from datetime import datetime
            hoy = datetime.now()
            datos_actuales["fecha_pregunta"] = f"{hoy.day:02d}/{hoy.month:02d}/{hoy.year}"
            datos_actuales["hora_pregunta"] = f"{hoy.hour:02d}:{hoy.minute:02d}"
        
        # Si no especifica lugar, usar Madrid por defecto
        if "lugar_pregunta" not in datos_actuales:
            datos_actuales["lugar_pregunta"] = "Madrid, España"

    # LÓGICA ESPECÍFICA PARA SINASTRÍA
    elif tipo_servicio == 'sinastria_ia':
        # Detectar si habla de 2 personas
        if "persona 1" in mensaje_lower or "primera persona" in mensaje_lower or "yo nací" in mensaje_lower:
            fecha_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', mensaje)
            if fecha_match:
                dia, mes, año = fecha_match.groups()
                datos_actuales["fecha_nacimiento_p1"] = f"{dia:0>2}/{mes:0>2}/{año}"
            
            hora_match = re.search(r'(\d{1,2}):(\d{2})', mensaje)
            if hora_match:
                hora, minuto = hora_match.groups()
                datos_actuales["hora_nacimiento_p1"] = f"{hora:0>2}:{minuto:0>2}"
                
        elif "persona 2" in mensaje_lower or "segunda persona" in mensaje_lower or "él nació" in mensaje_lower or "ella nació" in mensaje_lower:
            fecha_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', mensaje)
            if fecha_match:
                dia, mes, año = fecha_match.groups()
                datos_actuales["fecha_nacimiento_p2"] = f"{dia:0>2}/{mes:0>2}/{año}"
            
            hora_match = re.search(r'(\d{1,2}):(\d{2})', mensaje)
            if hora_match:
                hora, minuto = hora_match.groups()
                datos_actuales["hora_nacimiento_p2"] = f"{hora:0>2}:{minuto:0>2}"
                
    # LÓGICA ESPECÍFICA PARA LECTURA DE MANOS
    elif tipo_servicio == 'lectura_manos_ia':
        # Detectar si es diestro o zurdo
        mano_patterns = [
            r'soy diestro', r'soy zurdo', r'mano derecha', r'mano izquierda',
            r'escribo con la derecha', r'escribo con la izquierda', r'diestro', r'zurdo'
        ]
        
        for pattern in mano_patterns:
            if pattern in mensaje_lower:
                if 'diestro' in pattern or 'derecha' in pattern:
                    datos_actuales["mano_dominante"] = "diestro"
                elif 'zurdo' in pattern or 'izquierda' in pattern:
                    datos_actuales["mano_dominante"] = "zurdo"
                break
        
        # Detectar confirmación de fotos
        foto_patterns = [
            r'foto enviada', r'he enviado', r'ya envié', r'mando foto',
            r'envío foto', r'ya mandé', r'foto de mis manos', r'fotos listas',
            r'mis palmas', r'palmas'
        ]
        
        for pattern in foto_patterns:
            if pattern in mensaje_lower:
                datos_actuales["fotos_manos"] = "enviadas"
                break

    # LÓGICA ESPECÍFICA PARA LECTURA FACIAL
    elif tipo_servicio == 'lectura_facial_ia':
        # Detectar confirmación de fotos
        foto_patterns = [
            r'foto enviada', r'he enviado', r'mando fotos', r'envío fotos',
            r'ya mandé', r'fotos de mi cara', r'fotos listas', r'3 fotos'
        ]
        
        for pattern in foto_patterns:
            if pattern in mensaje_lower:
                datos_actuales["fotos_facial"] = "enviadas"
                break
                
    elif tipo_servicio == 'grafologia_ia':
        # Detectar confirmación de escritura
        escritura_patterns = [
            r'texto enviado', r'he enviado', r'mando texto', r'envío escritura',
            r'ya escribí', r'escritura lista', r'texto escrito', r'muestra de letra'
        ]
        
        for pattern in escritura_patterns:
            if pattern in mensaje_lower:
                datos_actuales["muestra_escritura"] = "enviada"
                break

    # Verificar completitud según tipo de servicio
    if tipo_servicio in ['carta_astral_ia', 'revolucion_solar_ia']:
        campos_requeridos = ["nombre", "fecha_nacimiento", "hora_nacimiento", "lugar_nacimiento", "residencia_actual"]
    elif tipo_servicio == 'astrologia_horaria_ia':
        campos_requeridos = ["nombre", "pregunta", "fecha_pregunta", "hora_pregunta", "lugar_pregunta"]
    elif tipo_servicio == 'sinastria_ia':
        campos_requeridos = [
            "nombre_p1", "fecha_nacimiento_p1", "hora_nacimiento_p1", "lugar_nacimiento_p1",
            "nombre_p2", "fecha_nacimiento_p2", "hora_nacimiento_p2", "lugar_nacimiento_p2"
        ]
    elif tipo_servicio == 'psico_coaching_ia':
        campos_requeridos = ["nombre"]
    elif tipo_servicio == 'lectura_manos_ia':
        campos_requeridos = ["nombre", "mano_dominante", "fotos_manos"]
    elif tipo_servicio == 'lectura_facial_ia':
        campos_requeridos = ["nombre", "fotos_facial"]
    elif tipo_servicio == 'grafologia_ia':
        campos_requeridos = ["nombre", "muestra_escritura"]
    else:
        campos_requeridos = ["nombre", "fecha_nacimiento", "hora_nacimiento", "lugar_nacimiento"]
        
    completos = all(campo in datos_actuales for campo in campos_requeridos)
    return datos_actuales, completos

def calcular_año_revolucion_solar(fecha_nacimiento_str, preferencia_año):
    """Calcular el año de revolución solar según preferencia"""
    try:
        dia, mes, año = map(int, fecha_nacimiento_str.split('/'))
        
        # Fecha actual
        hoy = datetime.now()
        
        # Fecha de cumpleaños este año
        cumpleaños_este_año = datetime(hoy.year, mes, dia)
        
        if preferencia_año == 'actual':
            # Revolución solar del año actual
            if hoy >= cumpleaños_este_año:
                año_revolucion = hoy.year
            else:
                año_revolucion = hoy.year - 1
        else:  # preferencia_año == 'proximo'
            # Revolución solar del próximo cumpleaños
            if hoy >= cumpleaños_este_año:
                año_revolucion = hoy.year + 1
            else:
                año_revolucion = hoy.year
        
        return año_revolucion
        
    except Exception as e:
        print(f"Error calculando año revolución: {e}")
        return datetime.now().year

def generar_cartas_astrales_completas(datos_natales, archivos_unicos):
    """Generar cartas astrales completas (natal, progresiones, tránsitos)"""
    try:
        # Generar carta natal
        carta_natal = CartaAstralNatal(
            nombre=datos_natales['nombre'],
            fecha_nacimiento=datos_natales['fecha_nacimiento'],
            hora_nacimiento=datos_natales['hora_nacimiento'],
            lugar_nacimiento=datos_natales['lugar_nacimiento'],
            residencia_actual=datos_natales['residencia_actual']
        )
        
        carta_natal.generar_carta_completa(archivo_salida=archivos_unicos['carta_natal_img'])
        
        # Generar progresiones
        datos_progresiones = generar_progresiones(datos_natales, archivos_unicos['progresiones_img'])
        
        # Generar tránsitos
        datos_transitos = generar_transitos(datos_natales, archivos_unicos['transitos_img'])
        
        # Extraer datos para interpretación
        datos_completos = extraer_datos_para_interpretacion(carta_natal, datos_progresiones, datos_transitos)
        
        print("✅ Cartas astrales generadas correctamente")
        return True, datos_completos
        
    except Exception as e:
        print(f"❌ Error generando cartas astrales: {e}")
        return False, None

def generar_revoluciones_solares_completas(datos_natales, archivos_unicos, año_revolucion):
    """Generar revolución solar completa (5 cartas)"""
    try:
        # Generar carta natal base
        carta_natal = CartaAstralNatal(
            nombre=datos_natales['nombre'],
            fecha_nacimiento=datos_natales['fecha_nacimiento'],
            hora_nacimiento=datos_natales['hora_nacimiento'],
            lugar_nacimiento=datos_natales['lugar_nacimiento'],
            residencia_actual=datos_natales['residencia_actual']
        )
        
        carta_natal.generar_carta_completa(archivo_salida=archivos_unicos['carta_natal_img'])
        
        # Generar progresiones
        datos_progresiones = generar_progresiones(datos_natales, archivos_unicos['progresiones_img'])
        
        # Generar tránsitos
        datos_transitos = generar_transitos(datos_natales, archivos_unicos['transitos_img'])
        
        # Generar revolución solar sola
        datos_rev_sola = generar_revolucion_sola(datos_natales, archivos_unicos['revolucion_sola_img'], año_revolucion)
        
        # Generar revolución solar con natal
        datos_rev_natal = generar_revolucion_natal(datos_natales, archivos_unicos['revolucion_natal_img'], año_revolucion)
        
        # Extraer datos para interpretación
        datos_completos = extraer_datos_para_interpretacion(
            carta_natal, datos_progresiones, datos_transitos, 
            datos_rev_sola, datos_rev_natal, año_revolucion
        )
        
        print("✅ Revolución solar completa generada correctamente")
        return True, datos_completos
        
    except Exception as e:
        print(f"❌ Error generando revolución solar: {e}")
        return False, None

def extraer_datos_para_interpretacion(carta_natal, progresiones=None, transitos=None, rev_sola=None, rev_natal=None, año_revolucion=None):
    """Extraer datos relevantes para la interpretación IA"""
    try:
        datos = {
            'carta_natal': {
                'planetas': carta_natal.posiciones_planetas if hasattr(carta_natal, 'posiciones_planetas') else {},
                'casas': carta_natal.casas if hasattr(carta_natal, 'casas') else {},
                'aspectos': carta_natal.aspectos if hasattr(carta_natal, 'aspectos') else [],
                'signos': carta_natal.signos_planetas if hasattr(carta_natal, 'signos_planetas') else {}
            }
        }
        
        if progresiones:
            datos['progresiones'] = progresiones
        
        if transitos:
            datos['transitos'] = transitos
        
        if rev_sola:
            datos['revolucion_sola'] = rev_sola
            
        if rev_natal:
            datos['revolucion_natal'] = rev_natal
            
        if año_revolucion:
            datos['año_revolucion'] = año_revolucion
        
        return datos
        
    except Exception as e:
        print(f"❌ Error extrayendo datos: {e}")
        return {}

def detectar_servicio_humano_agendable(mensaje):
    """Detectar si el cliente solicita servicio humano que Sofia puede agendar"""
    mensaje_lower = mensaje.lower()
    
    # Palabras clave para astrólogo humano
    astrologo_keywords = [
        'astrólogo humano', 'astróloga humana', 'astrologo personal', 
        'consulta personal astrología', 'astrólogo real', 'persona real astrología'
    ]
    
    # Palabras clave para tarot humano  
    tarot_keywords = [
        'tarot humano', 'tarot personal', 'consulta tarot real',
        'tarotista', 'lectura tarot persona', 'tarot presencial'
    ]
    
    # Detectar tipo de servicio (SOLO los que maneja Sofía)
    for keyword in astrologo_keywords:
        if keyword in mensaje_lower:
            return 'astrologo_humano'
    
    for keyword in tarot_keywords:
        if keyword in mensaje_lower:
            return 'tarot_humano'
    
    return None

def responder_ia_contextual(mensaje, contexto, numero_telefono):
    """Responder usando IA contextual"""
    try:
        # Contexto del flujo
        if contexto.get('esperando_email'):
            return "Hola, soy Sofía, tu asistente astrológica. Para comenzar, necesito que me proporciones tu email, por favor."
        
        elif contexto.get('esperando_codigo'):
            return "Ahora necesito tu código de servicio. Debe tener el formato AI_123456 para carta astral, RS_123456 para revolución solar, etc."
        
        elif contexto.get('tipo_servicio') == 'carta_astral_ia':
            return "Necesito tus datos de nacimiento completos: fecha, hora exacta, ciudad y país de nacimiento, y tu residencia actual."
        
        elif contexto.get('tipo_servicio') == 'revolucion_solar_ia':
            if not contexto.get('preferencia_año'):
                return "Necesito tus datos de nacimiento completos: fecha, hora exacta, ciudad y país de nacimiento, y tu residencia actual. También dime si quieres la revolución solar del año actual o del próximo cumpleaños."
            else:
                return "Necesito tus datos de nacimiento completos: fecha, hora exacta, ciudad y país de nacimiento, y tu residencia actual."
        
        else:
            return "¿En qué puedo ayudarte hoy?"
            
    except Exception as e:
        print(f"Error en respuesta IA: {e}")
        return "¿En qué puedo ayudarte?"

def handle_sofia_webhook(data):
    """Handler principal de Sofía - LIMPIO (sin interferir con WooCommerce)"""
    try:
        # ✅ FIX ANTI-LOOP - AÑADIDO
        if not data or not isinstance(data, dict):
            return {"status": "ok"}
        
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "").strip()
        
        # SI NO HAY MENSAJE Y NO HAY SESSION, ES HEALTHCHECK
        if not mensaje_usuario and not session_id:
            print("🏥 HEALTHCHECK detectado - respondiendo silenciosamente")
            return {"status": "ok"}
        
        # SI MÉTODO NO ES POST, ES VALIDACIÓN  
        if request.method != 'POST':
            return {"status": "ok", "message": "Sofia webhook ready"}
        
        # SOLO CONTINUAR SI HAY CONTENIDO REAL
        if not mensaje_usuario or len(mensaje_usuario.strip()) < 2:
            print("⚠️ Request sin contenido real")
            return {"status": "ok"}
        
        # ✅ AQUÍ CONTINÚA TU LÓGICA ORIGINAL
        archivos_unicos = data.get("archivos_unicos", {})
        id_unico = data.get("id_unico")
        
        # EXTRAER NÚMERO DE TELÉFONO
        numero_telefono = obtener_numero_telefono_desde_vapi(data)
        
        print(f"=== WEBHOOK SOFÍA (AS CARTASTRAL) ===")
        print(f"Session ID: {session_id}")
        print(f"Número teléfono: {numero_telefono}")
        print(f"Mensaje: {mensaje_usuario}")
        
        # DEBUG: Reconocimiento de códigos
        if mensaje_usuario and len(mensaje_usuario) > 3:
            debug_reconocimiento_codigo(mensaje_usuario)

        # PASO 1: VERIFICAR RECONEXIÓN AUTOMÁTICA O SESIÓN ACTIVA
        sesion_activa = None
        if numero_telefono:
            # Verificar reconexión automática (corte reciente)
            sesion_reconexion = verificar_sesion_activa(numero_telefono)
            
            if sesion_reconexion:
                print(f"🔄 Reconexión automática detectada: {sesion_reconexion['codigo_servicio']}")
                return manejar_reconexion(sesion_reconexion, data)
            
            # Buscar sesión activa normal
            try:
                sesion_activa = seguimiento.buscar_sesion_activa(numero_telefono)
            except Exception as e:
                print(f"❌ Error buscando sesión activa: {e}")
                sesion_activa = None
        
        if sesion_activa:
            print(f"🔄 Sesión activa encontrada: {sesion_activa['codigo_servicio']}")
            
            # Cliente tiene sesión activa - continuar conversación
            tiempo_restante = datetime.fromisoformat(sesion_activa['fecha_expiracion']) - datetime.now()
            horas_restantes = int(tiempo_restante.total_seconds() / 3600)
            
            # Mensaje de bienvenida para cliente que regresa
            if sesion_activa['tipo_servicio'] == 'carta_astral_ia' and sesion_activa['puede_revolucion_solar']:
                mensaje_bienvenida = f"¡Hola de nuevo! Te quedan {horas_restantes} horas para seguir nuestra conversación. ¿Quieres continuar con tu carta astral o prefieres que te haga la revolución solar GRATIS?"
            else:
                mensaje_bienvenida = f"¡Hola de nuevo! Te quedan {horas_restantes} horas para seguir nuestra conversación. ¿En qué puedo ayudarte?"
            
            # Caso especial: sesión pendiente de fotos
            if sesion_activa.get('estado') == 'pendiente_fotos':
                if sesion_activa['tipo_servicio'] == 'lectura_manos_ia':
                    mensaje_bienvenida = f"¡Hola de nuevo! ¿Ya enviaste las fotos de tus manos por email?"
                elif sesion_activa['tipo_servicio'] == 'lectura_facial_ia':
                    mensaje_bienvenida = f"¡Hola de nuevo! ¿Ya enviaste las 3 fotos de tu rostro por email?"
                
                # Detectar confirmación de fotos
                confirmacion_patterns = ['sí', 'si', 'ya envié', 'ya mandé', 'ya las envié', 'enviadas', 'listo', 'hecho', 'palmas', 'mis palmas']
                confirmacion_fotos = any(pattern in mensaje_usuario.lower() for pattern in confirmacion_patterns)

                if confirmacion_fotos:
                    # Cambiar estado a fotos confirmadas
                    seguimiento.actualizar_estado_sesion(sesion_activa['id'], 'fotos_confirmadas')
                    
                    if sesion_activa['tipo_servicio'] == 'lectura_manos_ia':
                        return {"type": "speak", "text": "Perfecto. Ahora necesito que me digas tu nombre y si eres diestro o zurdo, por favor."}
                    elif sesion_activa['tipo_servicio'] == 'lectura_facial_ia':
                        return {"type": "speak", "text": "Perfecto. Ahora necesito que me digas tu nombre, por favor."}
                else:
                    return {"type": "speak", "text": mensaje_bienvenida}
        
            # Actualizar conversación
            seguimiento.actualizar_conversacion(sesion_activa['id'], {
                'tipo': 'cliente_regresa',
                'mensaje': mensaje_usuario
            })
            
            # TRANSFERIR DIRECTAMENTE AL ESPECIALISTA CON DATOS EXISTENTES
            especialistas = {
                'carta_astral_ia': 'asst_78f4bfbd-cf67-46cb-910d-c8f0f8adf3fc',
                'revolucion_solar_ia': 'asst_9513ec30-f231-4171-959c-26c8588d248e', 
                'sinastria_ia': 'asst_9960b33c-db72-4ebd-ae3e-69ce6f7e6660',
                'astrologia_horaria_ia': 'asst_d218cde4-d4e1-4943-8fd9-a1df9404ebd6',
                'psico_coaching_ia': 'asst_63a0f9b9-c5d5-4df6-ba6f-52d700b51275',
                'lectura_manos_ia': 'asst_8473d3ab-22a7-479c-ae34-427e992023de',
                'lectura_facial_ia': 'asst_9cae2faa-2a8e-498b-b8f4-ab7af65bf734',
                'grafologia_ia': 'asst_84c67029-8059-4066-a5ae-8532b99fd24c'
            }
            
            especialista = especialistas.get(sesion_activa['tipo_servicio'])
            
            if especialista:
                return {
                    "type": "transfer_call",
                    "transfer": {
                        "type": "assistant", 
                        "assistantId": especialista
                    },
                    "data_extra": {
                        "sesion_activa": sesion_activa,
                        "cliente_regresa": True,
                        "mensaje_bienvenida": mensaje_bienvenida
                    }
                }
            else:
                return {"type": "speak", "text": mensaje_bienvenida}

        # PASO 2: NUEVA SESIÓN - GESTIÓN DE CONTEXTO
        contexto_sesion = sessions.get(session_id, {})
        
        # MANEJAR AGENDAMIENTO DE CITAS HUMANAS CON BD
        if contexto_sesion.get('agendando_cita'):
            tipo_servicio_humano = contexto_sesion.get('tipo_servicio_humano')
            
            # Detectar horario elegido
            import re
            horario_match = re.search(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', mensaje_usuario)
            
            if horario_match and not contexto_sesion.get('horario_elegido'):
                horario_elegido = f"{horario_match.group(1)}:{horario_match.group(2)}-{horario_match.group(3)}:{horario_match.group(4)}"
                contexto_sesion['horario_elegido'] = horario_elegido
                sessions[session_id] = contexto_sesion
                
                servicio_nombre = "Astrólogo Personal" if tipo_servicio_humano == 'astrologo_humano' else "Tarot Personal"
                return {"type": "speak", "text": f"Perfecto, {horario_elegido} para {servicio_nombre}. Ahora necesito tu nombre completo y email para confirmar la cita."}
            
            # Recopilar datos para la cita
            elif contexto_sesion.get('horario_elegido'):
                datos_cita = contexto_sesion.get('datos_cita', {})
                
                # Detectar nombre
                if "me llamo" in mensaje_usuario.lower() or not datos_cita.get('nombre'):
                    if "me llamo" in mensaje_usuario.lower():
                        partes = mensaje_usuario.lower().split("me llamo")
                        if len(partes) > 1:
                            nombre = partes[1].strip().split(',')[0].split('y')[0].strip()
                            datos_cita['nombre'] = nombre.title()
                    else:
                        # Asumir que todo el mensaje es el nombre si no tiene "me llamo"
                        nombre_limpio = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', mensaje_usuario).strip()
                        if nombre_limpio:
                            datos_cita['nombre'] = nombre_limpio.title()
                
                # Detectar email
                email_detectado = detectar_email(mensaje_usuario)
                if email_detectado:
                    datos_cita['email'] = email_detectado
                
                # Añadir teléfono si disponible
                if numero_telefono:
                    datos_cita['telefono'] = numero_telefono
                
                contexto_sesion['datos_cita'] = datos_cita
                sessions[session_id] = contexto_sesion
                
                # Verificar si tenemos todos los datos
                if datos_cita.get('nombre') and datos_cita.get('email'):
                    # Confirmar cita usando BD
                    from datetime import datetime, timedelta
                    fecha_cita = datetime.now() + timedelta(days=1)
                    
                    exito, confirmacion = agendar_cita_humana_sofia(
                        datos_cita, 
                        tipo_servicio_humano, 
                        contexto_sesion['horario_elegido'],
                        fecha_cita,
                        contexto_sesion.get('codigo_servicio', '')
                    )
                    
                    if exito:
                        # Limpiar sesión
                        sessions.pop(session_id, None)
                        
                        return {"type": "speak", "text": f"¡Perfecto! Tu cita con {confirmacion['servicio']} está confirmada para {confirmacion['fecha']} a las {confirmacion['horario']}. Código de reserva: {confirmacion['codigo_reserva']}. Te enviaremos un recordatorio por email a {datos_cita['email']}. ¡Hasta entonces!"}
                    else:
                        return {"type": "speak", "text": "Disculpa, ha ocurrido un error al agendar tu cita. Por favor, inténtalo más tarde."}
                else:
                    # Pedir datos faltantes
                    if not datos_cita.get('nombre'):
                        return {"type": "speak", "text": "¿Cuál es tu nombre completo?"}
                    elif not datos_cita.get('email'):
                        return {"type": "speak", "text": "¿Cuál es tu email para enviarte la confirmación?"}
            
            # Continuar en flujo de agendamiento
            return {"type": "speak", "text": "¿Qué horario prefieres? Dime la hora exacta, por ejemplo: 11:00-12:00"}

        # DETECTAR SI SOLICITA SERVICIO HUMANO QUE SOFIA PUEDE AGENDAR
        servicio_humano_agendable = detectar_servicio_humano_agendable(mensaje_usuario)
        if servicio_humano_agendable and not contexto_sesion.get('agendando_cita'):
            contexto_sesion['agendando_cita'] = True
            contexto_sesion['tipo_servicio_humano'] = servicio_humano_agendable
            sessions[session_id] = contexto_sesion
            
            # Obtener horarios disponibles para mañana
            from datetime import datetime, timedelta
            mañana = datetime.now() + timedelta(days=1)
            horarios = obtener_horarios_disponibles_sofia(servicio_humano_agendable, mañana)
            
            servicio_nombre = "Astrólogo Personal" if servicio_humano_agendable == 'astrologo_humano' else "Tarot Personal"
            
            if horarios:
                horarios_texto = ", ".join(horarios[:5])  # Mostrar solo 5 primeros
                return {"type": "speak", "text": f"Perfecto, quieres una cita con nuestro {servicio_nombre}. Para mañana {mañana.strftime('%d/%m/%Y')} tengo disponible: {horarios_texto}. ¿Cuál prefieres? También necesitaré tu nombre y email."}
            else:
                return {"type": "speak", "text": f"Para {servicio_nombre}, no tengo horarios disponibles mañana. ¿Te interesa otro día de la semana?"}

# FLUJO MEJORADO: CÓDIGO PRIMERO → EMAIL AUTOMÁTICO
        
        # Detectar y validar código si se proporciona
        if not contexto_sesion.get('codigo_validado'):
            codigo_valido, tipo_servicio = validar_codigo_servicio(mensaje_usuario)
            
            if codigo_valido:
                print(f"🔍 DEBUG: Código válido recibido: {mensaje_usuario.upper().strip()}")
                
                # NUEVO: Buscar email asociado al código en WooCommerce
                try:
                    from main import buscar_email_por_codigo, marcar_codigo_usado
                    
                    email_asociado, tipo_woo = buscar_email_por_codigo(mensaje_usuario.upper().strip())
                    print(f"🔍 DEBUG: Email encontrado: {email_asociado}, Tipo: {tipo_woo}")
                    
                    if email_asociado:
                        # Código encontrado en WooCommerce - flujo automático
                        contexto_sesion['email'] = email_asociado
                        contexto_sesion['codigo_servicio'] = mensaje_usuario.upper().strip()
                        contexto_sesion['tipo_servicio'] = tipo_servicio
                        contexto_sesion['codigo_validado'] = True
                        contexto_sesion['datos_natales'] = {'email': email_asociado}
                        sessions[session_id] = contexto_sesion
                        
                        # Marcar código como usado
                        marcar_codigo_usado(mensaje_usuario.upper().strip())
                        print(f"✅ Código marcado como usado: {mensaje_usuario.upper().strip()}")
                        
                        # Mensaje de confirmación personalizado por servicio
                        if tipo_servicio == 'carta_astral_ia':
                            return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Necesito tus datos de nacimiento: fecha, hora, ciudad y país de nacimiento, y tu residencia actual. La sesión dura 40 minutos."}
                        elif tipo_servicio == 'revolucion_solar_ia':
                            return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Necesito tus datos de nacimiento: fecha, hora, ciudad y país de nacimiento, y tu residencia actual. También dime si quieres la revolución solar del año actual o del próximo cumpleaños. La sesión dura 50 minutos."}
                        elif tipo_servicio == 'sinastria_ia':
                            return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Necesito los datos de nacimiento de las 2 personas: fecha, hora, ciudad y país de nacimiento de ambos. La sesión dura 30 minutos."}
                        elif tipo_servicio == 'astrologia_horaria_ia':
                            return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Necesito tu nombre y tu pregunta específica. La sesión dura 15 minutos."}
                        elif tipo_servicio == 'lectura_manos_ia':
                            # Enviar email automático con instrucciones
                            email_enviado = enviar_email_instrucciones_fotos(email_asociado, 'Cliente', tipo_servicio)
                            if email_enviado:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Te he enviado instrucciones para subir las fotos de tus palmas. Revisa tu email, responde con las fotos y llama cuando las hayas enviado. La sesión dura 30 minutos."}
                            else:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Envía las fotos de tus palmas por email y dime tu nombre para continuar. La sesión dura 30 minutos."}
                        elif tipo_servicio == 'lectura_facial_ia':
                            # Enviar email automático con instrucciones
                            email_enviado = enviar_email_instrucciones_fotos(email_asociado, 'Cliente', tipo_servicio)
                            if email_enviado:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Te he enviado instrucciones para las 3 fotos necesarias. Revisa tu email, responde con las fotos y llama cuando las hayas enviado. La sesión dura 15 minutos."}
                            else:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Envía las 3 fotos de tu rostro por email y dime tu nombre para continuar. La sesión dura 15 minutos."}
                        elif tipo_servicio == 'psico_coaching_ia':
                            return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Dime tu nombre para empezar la sesión de psico-coaching. La sesión dura 45 minutos."}
                        elif tipo_servicio == 'grafologia_ia':
                            # Enviar email automático con instrucciones
                            email_enviado = enviar_email_instrucciones_fotos(email_asociado, 'Cliente', tipo_servicio)
                            if email_enviado:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Te he enviado instrucciones para tu muestra de escritura. Revisa tu email, responde con la foto de tu texto y llama cuando lo hayas enviado. La sesión dura 30 minutos."}
                            else:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Envía una muestra de tu escritura por email y dime tu nombre para continuar. La sesión dura 30 minutos."}
                        elif tipo_servicio == 'grafologia_ia':
                            # Enviar email automático con instrucciones
                            email_enviado = enviar_email_instrucciones_fotos(email_asociado, 'Cliente', tipo_servicio)
                            if email_enviado:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Te he enviado instrucciones para tu muestra de escritura. Revisa tu email, responde con la foto de tu texto y llama cuando lo hayas enviado. La sesión dura 30 minutos."}
                            else:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Envía una muestra de tu escritura por email y dime tu nombre para continuar. La sesión dura 30 minutos."}

                        
                        # SERVICIOS HUMANOS - INICIAR AGENDAMIENTO
                        elif tipo_servicio == 'astrologo_humano':
                            contexto_sesion['agendando_cita'] = True
                            contexto_sesion['tipo_servicio_humano'] = tipo_servicio
                            sessions[session_id] = contexto_sesion
                            
                            # Obtener horarios disponibles para mañana
                            from datetime import datetime, timedelta
                            mañana = datetime.now() + timedelta(days=1)
                            horarios = obtener_horarios_disponibles_sofia(tipo_servicio, mañana)
                            
                            if horarios:
                                horarios_texto = ", ".join(horarios[:5])
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Para Astrólogo Personal mañana {mañana.strftime('%d/%m/%Y')} tengo: {horarios_texto}. ¿Cuál prefieres? También necesitaré tu nombre."}
                            else:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Para Astrólogo Personal no tengo horarios mañana. ¿Te interesa otro día?"}
                        
                        elif tipo_servicio == 'tarot_humano':
                            contexto_sesion['agendando_cita'] = True
                            contexto_sesion['tipo_servicio_humano'] = tipo_servicio
                            sessions[session_id] = contexto_sesion
                            
                            # Obtener horarios disponibles para mañana
                            from datetime import datetime, timedelta
                            mañana = datetime.now() + timedelta(days=1)
                            horarios = obtener_horarios_disponibles_sofia(tipo_servicio, mañana)
                            
                            if horarios:
                                horarios_texto = ", ".join(horarios[:5])
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Para Tarot Personal mañana {mañana.strftime('%d/%m/%Y')} tengo: {horarios_texto}. ¿Cuál prefieres? También necesitaré tu nombre."}
                            else:
                                return {"type": "speak", "text": f"Perfecto, código confirmado para {email_asociado}. Para Tarot Personal no tengo horarios mañana. ¿Te interesa otro día?"}
                    
                    else:
                        # Código válido pero no encontrado en WooCommerce - flujo manual
                        print(f"⚠️ DEBUG: Código válido pero no en WooCommerce: {mensaje_usuario.upper().strip()}")
                        contexto_sesion['codigo_servicio'] = mensaje_usuario.upper().strip()
                        contexto_sesion['tipo_servicio'] = tipo_servicio
                        contexto_sesion['esperando_email'] = True
                        contexto_sesion['codigo_validado'] = True
                        sessions[session_id] = contexto_sesion
                        
                        return {"type": "speak", "text": f"Código {mensaje_usuario.upper().strip()} confirmado. Ahora necesito tu email para continuar, por favor."}
                        
                except ImportError:
                    print("⚠️ DEBUG: No se pudo importar función de búsqueda, usando flujo manual")
                    # Fallback al flujo manual
                    contexto_sesion['codigo_servicio'] = mensaje_usuario.upper().strip()
                    contexto_sesion['tipo_servicio'] = tipo_servicio
                    contexto_sesion['esperando_email'] = True
                    contexto_sesion['codigo_validado'] = True
                    sessions[session_id] = contexto_sesion
                    
                    return {"type": "speak", "text": f"Código {mensaje_usuario.upper().strip()} confirmado. Ahora necesito tu email, por favor."}
            
            else:
                # No es un código válido - pedir código
                return {"type": "speak", "text": "Hola, soy Sofía de AS Cartastral. Para comenzar, dime tu código de servicio. Debe tener formato AI_123456, RS_123456, etc."}
        
        # Si ya tiene código validado pero necesita email (flujo manual)
        if contexto_sesion.get('esperando_email') and contexto_sesion.get('codigo_validado'):
            email_detectado = detectar_email(mensaje_usuario)
            if email_detectado:
                contexto_sesion['email'] = email_detectado
                contexto_sesion['esperando_email'] = False
                contexto_sesion['datos_natales'] = {'email': email_detectado}
                sessions[session_id] = contexto_sesion
                
                tipo_servicio = contexto_sesion['tipo_servicio']
                if tipo_servicio == 'carta_astral_ia':
                    return {"type": "speak", "text": f"Perfecto, {email_detectado}. Ahora necesito tus datos de nacimiento: fecha, hora, ciudad y país de nacimiento, y tu residencia actual. La sesión dura 40 minutos."}
                # ... (resto de servicios igual)
                
            else:
                return {"type": "speak", "text": "No he detectado un email válido. Por favor, dime tu email claramente."}
            codigo_valido, tipo_servicio = validar_codigo_servicio(mensaje_usuario)
            
            if codigo_valido and contexto_sesion.get('email'):
                contexto_sesion['codigo_servicio'] = mensaje_usuario.upper().strip()
                # NUEVO: Marcar código de WooCommerce como usado
                try:
                    from main import marcar_codigo_usado
                    marcar_codigo_usado(mensaje_usuario.upper().strip())
                    print(f"✅ Código marcado como usado: {mensaje_usuario.upper().strip()}")
                except ImportError:
                    print("⚠️ No se pudo marcar código como usado (función no disponible)")
                except Exception as e:
                    print(f"⚠️ Error marcando código usado: {e}")
                contexto_sesion['tipo_servicio'] = tipo_servicio
                contexto_sesion['esperando_codigo'] = False
                contexto_sesion['datos_natales'] = {'email': contexto_sesion['email']}
                sessions[session_id] = contexto_sesion
                
                # Mensajes específicos por tipo de servicio
                if tipo_servicio == 'carta_astral_ia':
                    return {"type": "speak", "text": "Código confirmado para carta astral por IA. Ahora necesito tus datos de nacimiento: fecha, hora, ciudad y país de nacimiento, y tu residencia actual, por favor. La sesión dura 40 minutos."}
                elif tipo_servicio == 'revolucion_solar_ia':
                    return {"type": "speak", "text": "Código confirmado para revolución solar. Necesito tus datos de nacimiento: fecha, hora, ciudad y país de nacimiento, y tu residencia actual. También dime si quieres la revolución solar del año actual o del próximo cumpleaños. La sesión dura 50 minutos."}
                elif tipo_servicio == 'sinastria_ia':
                    return {"type": "speak", "text": "Código confirmado para sinastría. Necesito los datos de nacimiento de las 2 personas: fecha, hora, ciudad y país de nacimiento de ambos."}
                elif tipo_servicio == 'astrologia_horaria_ia':
                    return {"type": "speak", "text": "Código confirmado para astrología horaria. Necesito tu nombre y tu pregunta específica, por favor."}
                elif tipo_servicio == 'lectura_manos_ia':
                    # Enviar email automático con instrucciones
                    email_enviado = enviar_email_instrucciones_fotos(
                        contexto_sesion['email'], 
                        'Cliente',
                        tipo_servicio
                    )
                    
                    if email_enviado:
                        return {"type": "speak", "text": "Código confirmado para lectura de manos. Te he enviado un email con instrucciones para subir las fotos de tus palmas. Revisa tu email, responde con las fotos y llama cuando las hayas enviado. ¿De acuerdo?"}
                    else:
                        return {"type": "speak", "text": "Código confirmado para lectura de manos. Por favor, envía las fotos de tus palmas por email y dime tu nombre para continuar."}
                        
                elif tipo_servicio == 'lectura_facial_ia':
                    # Enviar email automático con instrucciones
                    email_enviado = enviar_email_instrucciones_fotos(
                        contexto_sesion['email'], 
                        'Cliente',
                        tipo_servicio
                    )
                    
                    if email_enviado:
                        return {"type": "speak", "text": "Código confirmado para lectura facial. Te he enviado un email con instrucciones para las 3 fotos necesarias. Revisa tu email, responde con las fotos y llama cuando las hayas enviado."}
                    else:
                        return {"type": "speak", "text": "Código confirmado para lectura facial. Por favor, envía las 3 fotos de tu rostro por email y dime tu nombre para continuar."}
                elif tipo_servicio == 'psico_coaching_ia':
                    return {"type": "speak", "text": "Código confirmado para psico-coaching. Dime tu nombre por favor."}
                
                # SERVICIOS HUMANOS - INICIAR AGENDAMIENTO
                elif tipo_servicio == 'astrologo_humano':
                    contexto_sesion['agendando_cita'] = True
                    contexto_sesion['tipo_servicio_humano'] = tipo_servicio
                    sessions[session_id] = contexto_sesion
                    
                    # Obtener horarios disponibles para mañana
                    from datetime import datetime, timedelta
                    mañana = datetime.now() + timedelta(days=1)
                    horarios = obtener_horarios_disponibles_sofia(tipo_servicio, mañana)
                    
                    if horarios:
                        horarios_texto = ", ".join(horarios[:5])
                        return {"type": "speak", "text": f"Código confirmado para Astrólogo Personal. Para mañana {mañana.strftime('%d/%m/%Y')} tengo disponible: {horarios_texto}. ¿Cuál prefieres? También necesitaré tu nombre y email para confirmar la cita."}
                    else:
                        return {"type": "speak", "text": "Código confirmado para Astrólogo Personal. No tengo horarios disponibles mañana. ¿Te interesa otro día de la semana?"}
                
                elif tipo_servicio == 'tarot_humano':
                    contexto_sesion['agendando_cita'] = True
                    contexto_sesion['tipo_servicio_humano'] = tipo_servicio
                    sessions[session_id] = contexto_sesion
                    
                    # Obtener horarios disponibles para mañana
                    from datetime import datetime, timedelta
                    mañana = datetime.now() + timedelta(days=1)
                    horarios = obtener_horarios_disponibles_sofia(tipo_servicio, mañana)
                    
                    if horarios:
                        horarios_texto = ", ".join(horarios[:5])
                        return {"type": "speak", "text": f"Código confirmado para Tarot Personal. Para mañana {mañana.strftime('%d/%m/%Y')} tengo disponible: {horarios_texto}. ¿Cuál prefieres? También necesitaré tu nombre y email para confirmar la cita."}
                    else:
                        return {"type": "speak", "text": "Código confirmado para Tarot Personal. No tengo horarios disponibles mañana. ¿Te interesa otro día de la semana?"}
                
                else:
                    return {"type": "speak", "text": f"Código confirmado para {tipo_servicio}. ¿Qué datos necesitas proporcionarme?"}

        # RECOPILAR DATOS NATALES
        if contexto_sesion.get('tipo_servicio') and not contexto_sesion.get('datos_completos'):
            datos_natales = contexto_sesion.get('datos_natales', {'email': contexto_sesion.get('email', '')})
            
            # Para revolución solar, detectar preferencia de año
            if contexto_sesion['tipo_servicio'] == 'revolucion_solar_ia' and not contexto_sesion.get('preferencia_año'):
                preferencia_año = detectar_preferencia_año(mensaje_usuario)
                if preferencia_año:
                    contexto_sesion['preferencia_año'] = preferencia_año
                    sessions[session_id] = contexto_sesion
                    año_str = "del año actual" if preferencia_año == 'actual' else "del próximo cumpleaños"
                    return {"type": "speak", "text": f"Perfecto, revolución solar {año_str}. Ahora necesito tus datos de nacimiento completos."}
            
            datos_natales, completos = completar_datos_natales(
                datos_natales, mensaje_usuario, contexto_sesion['tipo_servicio']
            )
            
            contexto_sesion['datos_natales'] = datos_natales
            sessions[session_id] = contexto_sesion
            
            if completos:
                print("🎯 Datos completos, generando cartas y registrando sesión...")
                
                # REGISTRAR SESIÓN EN SISTEMA DE SEGUIMIENTO
                if numero_telefono:
                    sesion_id_db, fecha_expiracion = seguimiento.registrar_nueva_sesion(
                        numero_telefono=numero_telefono,
                        codigo_servicio=contexto_sesion['codigo_servicio'],
                        tipo_servicio=contexto_sesion['tipo_servicio'],
                        email=datos_natales['email'],
                        datos_natales=datos_natales
                    )
                
                # Cambiar estado para servicios con fotos
                if contexto_sesion['tipo_servicio'] in ['lectura_manos_ia', 'lectura_facial_ia'] and sesion_id_db:
                    seguimiento.actualizar_estado_sesion(sesion_id_db, 'pendiente_fotos')
                    print(f"🔄 Estado cambiado a 'pendiente_fotos' para {contexto_sesion['tipo_servicio']}")
                
                # GENERAR CARTAS SEGÚN TIPO DE SERVICIO
                timestamp = int(time.time())
                
                if contexto_sesion['tipo_servicio'] == 'carta_astral_ia':
                    # DEFINIR ARCHIVOS ÚNICOS PARA CARTA ASTRAL
                    archivos_unicos = {
                        'carta_natal_img': f'static/carta_natal_test_{timestamp}.png',
                        'progresiones_img': f'static/progresiones_test_{timestamp}.png',
                        'transitos_img': f'static/transitos_test_{timestamp}.png'
                    }
                    
                    exito, datos_interpretacion = generar_cartas_astrales_completas(datos_natales, archivos_unicos)
                    
                elif contexto_sesion['tipo_servicio'] == 'revolucion_solar_ia':
                    # CALCULAR AÑO DE REVOLUCIÓN SOLAR
                    preferencia_año = contexto_sesion.get('preferencia_año', 'actual')
                    año_revolucion = calcular_año_revolucion_solar(datos_natales['fecha_nacimiento'], preferencia_año)
                    
                    # DEFINIR ARCHIVOS ÚNICOS PARA REVOLUCIÓN SOLAR (5 cartas)
                    archivos_unicos = {
                        'carta_natal_img': f'static/carta_natal_rs_{timestamp}.png',
                        'progresiones_img': f'static/progresiones_rs_{timestamp}.png',
                        'transitos_img': f'static/transitos_rs_{timestamp}.png',
                        'revolucion_sola_img': f'static/revolucion_sola_{timestamp}.png',
                        'revolucion_natal_img': f'static/revolucion_natal_{timestamp}.png'
                    }
                    
                    exito, datos_interpretacion = generar_revoluciones_solares_completas(datos_natales, archivos_unicos, año_revolucion)
                
                # Para otros servicios, usar funciones existentes
                else:
                    datos_interpretacion = {
                        'tipo_servicio': contexto_sesion['tipo_servicio'],
                        'datos_cliente': datos_natales
                    }
                
                # TRANSFERIR AL ESPECIALISTA
                especialistas = {
                    'carta_astral_ia': 'asst_78f4bfbd-cf67-46cb-910d-c8f0f8adf3fc',
                    'revolucion_solar_ia': 'asst_9513ec30-f231-4171-959c-26c8588d248e', 
                    'sinastria_ia': 'asst_9960b33c-db72-4ebd-ae3e-69ce6f7e6660',
                    'astrologia_horaria_ia': 'asst_d218cde4-d4e1-4943-8fd9-a1df9404ebd6',
                    'psico_coaching_ia': 'asst_63a0f9b9-c5d5-4df6-ba6f-52d700b51275',
                    'lectura_manos_ia': 'asst_8473d3ab-22a7-479c-ae34-427e992023de',
                    'lectura_facial_ia': 'asst_9cae2faa-2a8e-498b-b8f4-ab7af65bf734',
                    'grafologia_ia': 'asst_84c67029-8059-4066-a5ae-8532b99fd24c'
                }
                
                # BUSCAR FOTOS PARA SERVICIOS QUE LAS NECESITAN
                if contexto_sesion['tipo_servicio'] in ['lectura_manos_ia', 'lectura_facial_ia']:
                    email_cliente = datos_natales.get('email')
                    fotos_encontradas = buscar_fotos_cliente_email(email_cliente)
                    
                    if fotos_encontradas:
                        for i, foto in enumerate(fotos_encontradas):
                            if contexto_sesion['tipo_servicio'] == 'lectura_manos_ia':
                                if i == 0:
                                    archivos_unicos['mano_izquierda_img'] = foto['filepath']
                                elif i == 1:
                                    archivos_unicos['mano_derecha_img'] = foto['filepath']
                            elif contexto_sesion['tipo_servicio'] == 'lectura_facial_ia':
                                if i == 0:
                                    archivos_unicos['cara_frente_img'] = foto['filepath']
                                elif i == 1:
                                    archivos_unicos['cara_izquierda_img'] = foto['filepath']
                                elif i == 2:
                                    archivos_unicos['cara_derecha_img'] = foto['filepath']
                        
                        marcar_fotos_como_procesadas(email_cliente)
                        print(f"✅ Fotos encontradas para {email_cliente}: {len(fotos_encontradas)}")
                
                especialista = especialistas.get(contexto_sesion['tipo_servicio'])
                
                if especialista:
                    # Mensaje de recordatorio según tipo de servicio
                    if contexto_sesion['tipo_servicio'] == 'carta_astral_ia':
                        mensaje_final = "Perfecto. Te paso ahora con nuestra astróloga especialista. Recuerda que tienes 40 minutos de sesión y tiempo adicional para seguir la conversación desde este teléfono, y también puedes pedir revolución solar gratis. Un momento, por favor."
                    elif contexto_sesion['tipo_servicio'] == 'revolucion_solar_ia':
                        mensaje_final = "Perfecto. Te paso ahora con nuestra astróloga especialista en revolución solar. Recuerda que tienes 50 minutos de sesión y tiempo adicional para seguir la conversación desde este teléfono. Un momento, por favor."
                    elif contexto_sesion['tipo_servicio'] in ['sinastria_ia', 'lectura_manos_ia']:
                        duracion = DURACIONES_SERVICIO.get(contexto_sesion['tipo_servicio'], 30)
                        mensaje_final = f"Perfecto. Te paso ahora con nuestro especialista. Recuerda que tienes {duracion} minutos de sesión y tiempo adicional para seguir la conversación desde este teléfono. Un momento, por favor."
                    elif contexto_sesion['tipo_servicio'] == 'psico_coaching_ia':
                        mensaje_final = "Perfecto. Te paso ahora con nuestro coach. Recuerda que tienes 45 minutos de sesión y tiempo adicional para seguir la conversación desde este teléfono. Un momento, por favor."
                    else:
                        mensaje_final = "Perfecto. Te paso ahora con nuestro especialista. Un momento, por favor."
                    
                    # Limpiar sesión temporal
                    sessions.pop(session_id, None)
                    
                    return {
                        "type": "transfer_call",
                        "transfer": {
                            "type": "assistant",
                            "assistantId": especialista
                        },
                        "data_extra": {
                            "codigo_servicio": contexto_sesion['codigo_servicio'],
                            "datos_interpretacion": datos_interpretacion,
                            "session_id": session_id,
                            "numero_telefono": numero_telefono,
                            "sesion_db_id": sesion_id_db if numero_telefono else None
                        },
                        "speak_first": mensaje_final
                    }
                else:
                    return {"type": "speak", "text": "Servicio configurado correctamente. En breve te contactaremos."}
            else:
                # Continuar recopilando datos
                respuesta = responder_ia_contextual(mensaje_usuario, contexto_sesion, numero_telefono)
                return {"type": "speak", "text": respuesta}

        # FLUJO INICIAL: Pedir email primero
        if not contexto_sesion.get('email'):
            contexto_sesion['esperando_email'] = True
            sessions[session_id] = contexto_sesion
            respuesta = responder_ia_contextual(mensaje_usuario, contexto_sesion, numero_telefono)
            return {"type": "speak", "text": respuesta}

        # Fallback
        respuesta = responder_ia_contextual(mensaje_usuario, contexto_sesion, numero_telefono)
        return {"type": "speak", "text": respuesta}
        
    except Exception as e:
        print(f"❌ Error en handle_sofia_webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "ok"}  # ✅ CAMBIADO: Evitar loops en errores