import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import json
import datetime
from flask import render_template_string
from informes import generar_y_enviar_informe_desde_agente

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions_astrologa = {}

def generar_informe_html_final(datos_interpretacion, conversacion_completa):
    """
    Generar informe HTML final con la interpretación completa
    """
    try:
        template_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Carta Astral Completa - {{ datos.datos_personales.nombre }}</title>
    <style>
        body { font-family: 'Georgia', serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .header { text-align: center; background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        .header h1 { margin: 0; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header h2 { margin: 10px 0 0 0; font-size: 1.8em; opacity: 0.9; }
        .seccion { margin: 25px 0; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .datos-natales { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); }
        .planetas { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
        .aspectos { background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); }
        .interpretacion { background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%); color: white; }
        .conversacion { background: linear-gradient(135deg, #f093fb 0%, #f5576c 50%, #4facfe 100%); color: white; }
        .carta-img { max-width: 100%; height: auto; margin: 15px 0; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .galeria-cartas { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .carta-item { text-align: center; }
        .carta-item h4 { margin: 10px 0; color: #333; }
        .planet-item, .aspect-item { background: rgba(255,255,255,0.8); margin: 5px 0; padding: 8px; border-radius: 5px; }
        .conversacion-text { line-height: 1.6; font-size: 1.1em; }
        .footer { text-align: center; margin-top: 40px; padding: 20px; background: #333; color: white; border-radius: 10px; }
        .highlight { background: rgba(255,255,0,0.3); padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>🌟 CARTA ASTRAL COMPLETA</h1>
            <h2>{{ datos.datos_personales.nombre }}</h2>
            <p>📅 {{ datos.datos_personales.fecha_nacimiento }} a las {{ datos.datos_personales.hora_nacimiento }}</p>
            <p>📍 {{ datos.datos_personales.lugar_nacimiento }}</p>
            <p><small>Generado el {{ datos.fecha_generacion }}</small></p>
        </div>
        
        <!-- DATOS NATALES -->
        <div class="seccion datos-natales">
            <h3>📋 Datos Natales</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <div><strong>📅 Fecha:</strong> {{ datos.datos_personales.fecha_nacimiento }}</div>
                <div><strong>🕐 Hora:</strong> {{ datos.datos_personales.hora_nacimiento }}</div>
                <div><strong>📍 Lugar:</strong> {{ datos.datos_personales.lugar_nacimiento }}</div>
                <div><strong>🏠 Residencia:</strong> {{ datos.datos_personales.residencia_actual }}</div>
            </div>
        </div>
        
        <!-- GALERÍA DE CARTAS -->
        <div class="seccion">
            <h3>🎨 Cartas Astrológicas</h3>
            <div class="galeria-cartas">
                {% if datos.imagenes.carta_natal %}
                <div class="carta-item">
                    <h4>🌟 Carta Natal</h4>
                    <img src="{{ datos.imagenes.carta_natal }}" alt="Carta Astral Natal" class="carta-img">
                    <p><small>Posiciones planetarias al momento de tu nacimiento</small></p>
                </div>
                {% endif %}
                
                {% if datos.imagenes.progresiones %}
                <div class="carta-item">
                    <h4>📈 Progresiones</h4>
                    <img src="{{ datos.imagenes.progresiones }}" alt="Progresiones" class="carta-img">
                    <p><small>Tu evolución personal a lo largo del tiempo</small></p>
                </div>
                {% endif %}
                
                {% if datos.imagenes.transitos %}
                <div class="carta-item">
                    <h4>🔄 Tránsitos Actuales</h4>
                    <img src="{{ datos.imagenes.transitos }}" alt="Tránsitos" class="carta-img">
                    <p><small>Influencias planetarias actuales</small></p>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- POSICIONES PLANETARIAS -->
        <div class="seccion planetas">
            <h3>🪐 Posiciones Planetarias</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                {% for planeta, posicion in datos.posiciones_planetarias.items() %}
                <div class="planet-item">
                    <strong>{{ planeta }}:</strong> {{ posicion }}
                </div>
                {% endfor %}
            </div>
            
            {% if datos.planetas_retrogrados %}
            <div style="margin-top: 15px; padding: 10px; background: rgba(255,0,0,0.1); border-radius: 5px;">
                <strong>🔄 Planetas Retrógrados:</strong> {{ datos.planetas_retrogrados|join(', ') }}
            </div>
            {% endif %}
        </div>
        
        <!-- ASPECTOS PRINCIPALES -->
        <div class="seccion aspectos">
            <h3>✨ Aspectos Principales ({{ datos.total_aspectos }} total)</h3>
            {% for aspecto in datos.aspectos_principales %}
            <div class="aspect-item">{{ aspecto }}</div>
            {% endfor %}
        </div>
        
        <!-- INTERPRETACIÓN PERSONALIZADA -->
        <div class="seccion interpretacion">
            <h3>🔮 Interpretación Astrológica Personalizada</h3>
            <div class="conversacion-text">
                {{ conversacion_completa|safe }}
            </div>
        </div>
        
        <!-- FOOTER -->
        <div class="footer">
            <h4>💫 AS Carta Astral</h4>
            <p>Interpretación astrológica personalizada generada con IA especializada</p>
            <p><small>© {{ datetime.now().year }} AS Carta Astral - Todos los derechos reservados</small></p>
        </div>
    </div>
</body>
</html>
        """
        
        # Renderizar con Jinja2
        from jinja2 import Template
        template = Template(template_html)
        
        html_content = template.render(
            datos=datos_interpretacion,
            conversacion_completa=conversacion_completa,
            datetime=datetime
        )
        
        return html_content
        
    except Exception as e:
        print(f"❌ Error generando informe HTML final: {e}")
        return None

def enviar_informe_por_email(datos_interpretacion, html_content, codigo_servicio):
    """
    Enviar informe final por email
    """
    try:
        nombre = datos_interpretacion['datos_personales']['nombre']
        email_destino = "cliente@ejemplo.com"  # PERSONALIZAR: obtener del código
        
        print(f"📧 Preparando envío de informe a: {email_destino}")
        
        # Datos para webhook de email
        email_data = {
            "destinatario": email_destino,
            "nombre": nombre,
            "codigo_servicio": codigo_servicio,
            "asunto": f"Tu Carta Astral Completa - {nombre}",
            "html_content": html_content,
            "fecha_generacion": datetime.datetime.now().isoformat()
        }
        
        # Enviar a Make webhook de email
        url_email = os.getenv("MAKE_WEBHOOK_EMAIL_ASTRAL")
        if url_email:
            response = requests.post(url_email, json=email_data, timeout=40)
            if response.status_code == 200:
                print("✅ Informe enviado por email exitosamente")
                return True
        
        print("⚠️ Sistema de email no configurado - informe generado localmente")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando informe por email: {e}")
        return False

def interpretar_carta_astral_ia(datos_interpretacion, pregunta_cliente=None):
    """
    Interpretación astrológica usando IA especializada
    """
    try:
        # Construir contexto astrológico
        nombre = datos_interpretacion['datos_personales']['nombre']
        planetas = datos_interpretacion['posiciones_planetarias']
        aspectos = datos_interpretacion['aspectos_principales']
        retrogrados = datos_interpretacion['planetas_retrogrados']
        
        contexto_astrologico = f"""
DATOS ASTROLÓGICOS DE {nombre}:

POSICIONES PLANETARIAS:
{chr(10).join([f"• {planeta}: {posicion}" for planeta, posicion in planetas.items()])}

ASPECTOS PRINCIPALES:
{chr(10).join([f"• {aspecto}" for aspecto in aspectos[:8]])}

PLANETAS RETRÓGRADOS: {', '.join(retrogrados) if retrogrados else 'Ninguno'}
        """
        
        if pregunta_cliente:
            prompt = f"""Eres una astróloga experta con 20 años de experiencia. Responde esta pregunta específica del cliente de forma clara y detallada:

{contexto_astrologico}

PREGUNTA DEL CLIENTE: {pregunta_cliente}

Responde de forma personalizada, mencionando los planetas y aspectos relevantes. Sé específica pero accesible."""
        else:
            prompt = f"""Eres una astróloga experta con 20 años de experiencia. Proporciona una interpretación completa y personalizada de esta carta astral:

{contexto_astrologico}

ESTRUCTURA TU INTERPRETACIÓN:
1. PERSONALIDAD GENERAL (4-5 párrafos): Rasgos principales, fortalezas, desafíos
2. VIDA ACTUAL Y FUTURO (4-5 párrafos): Tendencias actuales, oportunidades, recomendaciones
3. ASPECTOS DESTACADOS: Los 3 aspectos más importantes y su significado

Habla directamente al cliente, usa un tono cálido y profesional. Menciona planetas y signos específicos."""

        response = client.chat.completions.create(
            model="gpt-4",  # Usar GPT-4 para mejor interpretación
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.8
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Error en interpretación astrológica: {e}")
        return "Disculpa, ha ocurrido un error en la interpretación. Inténtalo más tarde."

def handle_astrologa_cartastral_webhook(data):
    """
    Handler de astróloga que solo interpreta datos ya procesados por Sofía
    """
    try:
        session_id = data.get("session_id")
        mensaje_usuario = data.get("text", "")
        
        # DATOS PROCESADOS POR SOFÍA
        codigo_servicio = data.get("codigo_servicio")
        datos_interpretacion = data.get("datos_interpretacion")
        
        print(f"=== WEBHOOK ASTRÓLOGA CARTA ASTRAL ===")
        print(f"Session ID: {session_id}")
        print(f"Mensaje: {mensaje_usuario}")
        print(f"Código: {codigo_servicio}")
        print(f"Tiene datos de interpretación: {bool(datos_interpretacion)}")

        if not session_id:
            return {"type": "speak", "text": "Error en la sesión. Por favor, inicia una nueva llamada."}

        # INICIALIZAR SESIÓN DE LA ASTRÓLOGA
        if session_id not in sessions_astrologa:
            sessions_astrologa[session_id] = {
                'datos_interpretacion': datos_interpretacion,
                'codigo_servicio': codigo_servicio,
                'conversacion': [],
                'interpretacion_inicial_dada': False
            }

        sesion = sessions_astrologa[session_id]

        # CASO 1: PRIMERA INTERACCIÓN - DAR INTERPRETACIÓN INICIAL
        if not sesion['interpretacion_inicial_dada'] and datos_interpretacion:
            print("🔮 Generando interpretación inicial...")
            
            nombre = datos_interpretacion['datos_personales']['nombre']
            interpretacion = interpretar_carta_astral_ia(datos_interpretacion)
            
            # Mensaje de bienvenida + interpretación
            mensaje_completo = f"Hola {nombre}, soy tu astróloga especialista. He analizado tu carta astral completa y aquí está tu interpretación personalizada:\n\n{interpretacion}\n\n¿Tienes alguna pregunta específica sobre tu carta astral?"
            
            sesion['conversacion'].append(f"ASTRÓLOGA: {mensaje_completo}")
            sesion['interpretacion_inicial_dada'] = True
            
            return {"type": "speak", "text": mensaje_completo}

        # CASO 2: PREGUNTAS ESPECÍFICAS DEL CLIENTE
        elif mensaje_usuario and datos_interpretacion:
            print("❓ Respondiendo pregunta específica del cliente...")
            
            interpretacion_especifica = interpretar_carta_astral_ia(
                datos_interpretacion, 
                pregunta_cliente=mensaje_usuario
            )
            
            sesion['conversacion'].append(f"CLIENTE: {mensaje_usuario}")
            sesion['conversacion'].append(f"ASTRÓLOGA: {interpretacion_especifica}")
            
            return {"type": "speak", "text": interpretacion_especifica}

        # CASO 3: FIN DE SESIÓN - GENERAR INFORME
        elif ("gracias" in mensaje_usuario.lower() or "adiós" in mensaje_usuario.lower() or 
              "hasta luego" in mensaje_usuario.lower() or "despedida" in mensaje_usuario.lower()):
            print("👋 Generando informe final de sesión...")
            
            # Generar resumen completo de toda la conversación
            conversacion_completa = "\n".join(sesion['conversacion'])
            resumen = f"Resumen completo de 40 minutos sobre carta astral: {conversacion_completa}"
            resultado = generar_y_enviar_informe_desde_agente(data, 'carta_astral_ia', resumen)
            
            return {"type": "speak", "text": "Gracias por tu consulta. He enviado tu informe completo por email. ¡Que tengas un día maravilloso!"}

        # CASO 4: SIN DATOS (ERROR) - Sin cambios
        else:
            return {"type": "speak", "text": "Disculpa, no tengo tus datos astrológicos..."}

    except Exception as e:
        print(f"❌ Error en handle_astrologa_cartastral_webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"type": "speak", "text": "Ha ocurrido un error en la interpretación. Por favor, inténtalo más tarde."}