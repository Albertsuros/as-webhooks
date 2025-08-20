import os
import yaml
import requests
from openai import OpenAI
from datetime import datetime
import json
import random

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Cache para reglas de grafología
_rules_cache = None

def cargar_reglas_grafologia():
    """Cargar reglas de grafología desde rules.yml"""
    global _rules_cache
    if _rules_cache is None:
        try:
            rules_path = os.path.join(os.path.dirname(__file__), '..', 'grafologia', 'rules.yml')
            with open(rules_path, 'r', encoding='utf-8') as f:
                _rules_cache = yaml.safe_load(f)
        except Exception as e:
            print(f"Error cargando rules.yml: {e}")
            _rules_cache = {}
    return _rules_cache

def analizar_escritura_tecnica(email_cliente):
    """Buscar imagen de escritura del cliente y analizarla técnicamente"""
    try:
        # Buscar fotos del cliente por email
        from email_photo_processor import buscar_fotos_cliente_email, marcar_fotos_como_procesadas
        
        fotos = buscar_fotos_cliente_email(email_cliente)
        if not fotos:
            return None, "No se encontraron muestras de escritura"
        
        # Usar la primera foto encontrada
        imagen_path = fotos[0]['filepath']
        
        # Llamar al API de grafología
        url = "http://localhost:5000/grafologia/analizar"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            analisis = response.json()
            marcar_fotos_como_procesadas(email_cliente)
            return analisis, imagen_path
        else:
            return None, f"Error en análisis: {response.status_code}"
            
    except Exception as e:
        print(f"Error en análisis técnico: {e}")
        return None, str(e)

def interpretar_dimension(dimension, score, reglas):
    """Interpretar una dimensión específica según su puntuación"""
    try:
        interpretaciones = reglas.get('interpretaciones_detalladas', {}).get(dimension, {})
        
        if score >= 0.6:
            nivel = 'alto'
        elif score >= 0.3:
            nivel = 'medio'
        else:
            nivel = 'bajo'
        
        return interpretaciones.get(nivel, {})
        
    except Exception as e:
        print(f"Error interpretando dimensión {dimension}: {e}")
        return {}

def detectar_perfil_especializado(scores, reglas):
    """Detectar si el cliente tiene un perfil especializado"""
    try:
        perfiles = reglas.get('perfiles_especializados', {})
        
        for nombre_perfil, perfil_info in perfiles.items():
            condiciones = perfil_info.get('condiciones', [])
            cumple_todas = True
            
            for condicion in condiciones:
                for dimension, criterio in condicion.items():
                    score_actual = scores.get(dimension, {}).get('score', 0)
                    
                    if ">=" in criterio:
                        umbral = float(criterio.replace(">=", "").strip())
                        if score_actual < umbral:
                            cumple_todas = False
                            break
                    elif "<=" in criterio:
                        umbral = float(criterio.replace("<=", "").strip())
                        if score_actual > umbral:
                            cumple_todas = False
                            break
                
                if not cumple_todas:
                    break
            
            if cumple_todas:
                return nombre_perfil, perfil_info
        
        return None, None
        
    except Exception as e:
        print(f"Error detectando perfil: {e}")
        return None, None

def generar_interpretacion_completa(analisis_tecnico, datos_cliente):
    """Generar interpretación completa usando reglas + IA"""
    try:
        reglas = cargar_reglas_grafologia()
        scores = analisis_tecnico.get('scores', {})
        
        # Interpretar cada dimensión
        interpretaciones = {}
        for dimension, data in scores.items():
            score = data.get('score', 0)
            interpretacion = interpretar_dimension(dimension, score, reglas)
            interpretaciones[dimension] = {
                'score': score,
                'nivel': 'alto' if score >= 0.6 else 'medio' if score >= 0.3 else 'bajo',
                'interpretacion': interpretacion
            }
        
        # Detectar perfil especializado
        perfil_especial, info_perfil = detectar_perfil_especializado(scores, reglas)
        
        # Generar resumen con IA
        prompt_ia = f"""
        Eres un grafólogo experto analizando esta escritura:
        
        PUNTUACIONES:
        {json.dumps(scores, indent=2)}
        
        CLIENTE: {datos_cliente.get('nombre', 'Cliente')}
        
        Genera una interpretación cálida y profesional de 150-200 palabras que:
        1. Resuma las características principales de su personalidad
        2. Destaque sus fortalezas únicas
        3. Sea positiva pero realista
        4. Use un tono cercano y empático
        
        No uses terminología técnica compleja, habla como si fuera una conversación personal.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_ia}],
            max_tokens=300
        )
        
        resumen_ia = response.choices[0].message.content
        
        return {
            'interpretaciones': interpretaciones,
            'perfil_especial': perfil_especial,
            'info_perfil': info_perfil,
            'resumen_personalizado': resumen_ia,
            'reglas': reglas
        }
        
    except Exception as e:
        print(f"Error generando interpretación: {e}")
        return None

def responder_pregunta_cliente(pregunta, interpretacion_completa, datos_cliente):
    """Responder preguntas específicas del cliente usando la interpretación"""
    try:
        reglas = interpretacion_completa.get('reglas', {})
        consultas = reglas.get('consultas_frecuentes', {})
        scores = {dim: data['score'] for dim, data in interpretacion_completa['interpretaciones'].items()}
        
        # Buscar respuesta en consultas frecuentes
        respuesta_base = ""
        pregunta_lower = pregunta.lower()
        
        if any(palabra in pregunta_lower for palabra in ['pareja', 'compatib', 'relacion']):
            respuesta_base = consultas.get('compatibilidad_pareja', {}).get('respuesta', '')
        elif any(palabra in pregunta_lower for palabra in ['trabajo', 'carrera', 'profesion']):
            respuesta_base = consultas.get('cambio_carrera', {}).get('respuesta', '')
        elif any(palabra in pregunta_lower for palabra in ['lider', 'jefe', 'mandar']):
            respuesta_base = consultas.get('liderazgo', {}).get('respuesta', '')
        elif any(palabra in pregunta_lower for palabra in ['amigos', 'social', 'gente']):
            respuesta_base = consultas.get('relaciones_sociales', {}).get('respuesta', '')
        
        # Personalizar con IA
        prompt_personalizacion = f"""
        PREGUNTA DEL CLIENTE: {pregunta}
        
        RESPUESTA BASE: {respuesta_base}
        
        PERFIL DEL CLIENTE:
        - Sociabilidad: {scores.get('sociabilidad', 0):.1f}
        - Autocontrol: {scores.get('autocontrol', 0):.1f}
        - Organización: {scores.get('organizacion', 0):.1f}
        - Detalle: {scores.get('detalle', 0):.1f}
        - Energía: {scores.get('energia', 0):.1f}
        - Emotividad: {scores.get('emotividad', 0):.1f}
        
        Personaliza la respuesta base específicamente para este cliente basándote en sus puntuaciones.
        Sé específico, cálido y práctico. Usa ejemplos concretos.
        Máximo 150 palabras.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_personalizacion}],
            max_tokens=250
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error respondiendo pregunta: {e}")
        return "Esa es una excelente pregunta. Basándome en tu escritura, puedo decirte que..."

def obtener_pregunta_exploratoria(tema, reglas):
    """Obtener pregunta exploratoria según el tema"""
    try:
        preguntas = reglas.get('preguntas_exploratorias', {}).get(tema, [])
        if preguntas:
            return random.choice(preguntas)
        return "¿Qué más te gustaría saber sobre tu personalidad?"
    except:
        return "¿Qué más te gustaría saber sobre tu personalidad?"

def generar_informe_final(interpretacion_completa, datos_cliente, imagen_path, resumen_sesion):
    """Generar informe PDF final"""
    try:
        from informes import generar_y_enviar_informe_desde_agente
        
        # Preparar datos para el informe
        scores = interpretacion_completa.get('interpretaciones', {})
        medidas = interpretacion_completa.get('medidas_tecnicas', {})
        
        data_informe = {
            'nombre': datos_cliente.get('nombre', 'Cliente'),
            'email': datos_cliente.get('email', ''),
            'codigo_servicio': datos_cliente.get('codigo_servicio', ''),
            'puntuaciones': scores,
            'medidas_tecnicas': medidas,
            'confianza': interpretacion_completa.get('confianza', 50),
            'archivos_unicos': {
                'muestra_escritura_img': imagen_path,
                'puntuaciones': scores,
                'medidas_tecnicas': medidas,
                'confianza': interpretacion_completa.get('confianza', 50)
            }
        }
        
        resultado = generar_y_enviar_informe_desde_agente(
            data_informe, 
            'grafologia_ia', 
            resumen_sesion
        )
        
        return resultado
        
    except Exception as e:
        print(f"Error generando informe: {e}")
        return False

class SesionGrafologia:
    """Clase para manejar el estado de la sesión de grafología"""
    
    def __init__(self, datos_cliente):
        self.datos_cliente = datos_cliente
        self.analisis_tecnico = None
        self.interpretacion = None
        self.imagen_path = None
        self.conversacion = []
        self.temas_explorados = set()
        self.inicio_sesion = datetime.now()
        
    def analizar_escritura(self):
        """Realizar análisis técnico de la escritura"""
        email = self.datos_cliente.get('email', '')
        self.analisis_tecnico, self.imagen_path = analizar_escritura_tecnica(email)
        
        if self.analisis_tecnico:
            self.interpretacion = generar_interpretacion_completa(self.analisis_tecnico, self.datos_cliente)
            return True
        return False
    
    def obtener_resumen_inicial(self):
        """Obtener resumen inicial de la personalidad"""
        if not self.interpretacion:
            return "Primero necesito analizar tu escritura."
        
        resumen = self.interpretacion.get('resumen_personalizado', '')
        perfil_especial = self.interpretacion.get('perfil_especial')
        
        if perfil_especial:
            info_perfil = self.interpretacion.get('info_perfil', {})
            descripcion_perfil = info_perfil.get('descripcion', '')
            resumen += f"\n\nTu perfil especial es: {perfil_especial.replace('_', ' ').title()}. {descripcion_perfil}"
        
        return resumen
    
    def explorar_dimension(self, dimension):
        """Explorar una dimensión específica en profundidad"""
        if dimension not in self.interpretacion.get('interpretaciones', {}):
            return "No tengo información sobre esa dimensión."
        
        data = self.interpretacion['interpretaciones'][dimension]
        interp = data.get('interpretacion', {})
        
        self.temas_explorados.add(dimension)
        
        respuesta = f"Sobre tu {dimension}:\n\n"
        
        if 'descripcion_general' in interp:
            respuesta += interp['descripcion_general'] + "\n\n"
        
        if 'caracteristicas_principales' in interp:
            respuesta += "Características principales:\n" + interp['caracteristicas_principales'] + "\n\n"
        
        if 'ejemplos_vida_cotidiana' in interp:
            respuesta += "En tu vida cotidiana:\n" + interp['ejemplos_vida_cotidiana']
        
        return respuesta
    
    def responder_pregunta(self, pregunta):
        """Responder pregunta específica del cliente"""
        self.conversacion.append(('cliente', pregunta))
        
        if not self.interpretacion:
            return "Primero necesito analizar tu escritura para poder responder."
        
        respuesta = responder_pregunta_cliente(pregunta, self.interpretacion, self.datos_cliente)
        self.conversacion.append(('grafologia', respuesta))
        
        return respuesta
    
    def sugerir_siguiente_tema(self):
        """Sugerir siguiente tema de exploración"""
        reglas = self.interpretacion.get('reglas', {})
        
        # Temas disponibles
        todos_temas = ['autoconocimiento', 'relaciones_pareja', 'carrera_profesional', 'desarrollo_personal', 'comunicacion']
        temas_restantes = [t for t in todos_temas if t not in self.temas_explorados]
        
        if temas_restantes:
            tema = random.choice(temas_restantes)
            pregunta = obtener_pregunta_exploratoria(tema, reglas)
            self.temas_explorados.add(tema)
            return pregunta
        
        return "¿Hay algo más específico sobre tu personalidad que te gustaría explorar?"
    
    def generar_resumen_sesion(self):
        """Generar resumen de toda la sesión"""
        duracion = datetime.now() - self.inicio_sesion
        minutos = int(duracion.total_seconds() / 60)
        
        resumen = f"Sesión de grafología de {minutos} minutos con {self.datos_cliente.get('nombre', 'Cliente')}.\n\n"
        
        if self.interpretacion:
            scores = self.interpretacion.get('interpretaciones', {})
            resumen += "PUNTUACIONES PRINCIPALES:\n"
            for dim, data in scores.items():
                score_pct = int(data['score'] * 100)
                resumen += f"- {dim.title()}: {score_pct}% ({data['nivel']})\n"
            
            perfil_especial = self.interpretacion.get('perfil_especial')
            if perfil_especial:
                resumen += f"\nPERFIL ESPECIALIZADO: {perfil_especial.replace('_', ' ').title()}\n"
            
            resumen += f"\nTEMAS EXPLORADOS: {', '.join(self.temas_explorados)}\n"
            
            if self.conversacion:
                resumen += "\nPUNTOS CLAVE DE LA CONVERSACIÓN:\n"
                for tipo, mensaje in self.conversacion[-6:]:  # Últimas 3 interacciones
                    if tipo == 'cliente':
                        resumen += f"- Cliente preguntó: {mensaje[:100]}...\n"
        
        return resumen
    
    def finalizar_y_enviar_informe(self):
        """Finalizar sesión y enviar informe"""
        resumen_sesion = self.generar_resumen_sesion()
        
        return generar_informe_final(
            self.interpretacion, 
            self.datos_cliente, 
            self.imagen_path, 
            resumen_sesion
        )

# Cache de sesiones activas
sesiones_activas = {}

def handle_grafologia_webhook(data):
    """Handler principal del agente de Grafología"""
    try:
        mensaje_usuario = data.get("text", "").strip()
        session_data = data.get("data_extra", {})
        session_id = data.get("session_id", "default")
        
        # Extraer datos del cliente
        datos_cliente = {
            'nombre': session_data.get('datos_interpretacion', {}).get('datos_cliente', {}).get('nombre', 
                     session_data.get('sesion_activa', {}).get('datos_natales', {}).get('nombre', 'Cliente')),
            'email': session_data.get('datos_interpretacion', {}).get('datos_cliente', {}).get('email',
                    session_data.get('sesion_activa', {}).get('datos_natales', {}).get('email', '')),
            'codigo_servicio': session_data.get('codigo_servicio', '')
        }
        
        # Obtener o crear sesión
        if session_id not in sesiones_activas:
            sesiones_activas[session_id] = SesionGrafologia(datos_cliente)
        
        sesion = sesiones_activas[session_id]
        
        # FLUJO DE CONVERSACIÓN
        
        # 1. INICIO - Análisis automático
        if not sesion.analisis_tecnico and not mensaje_usuario:
            if sesion.analizar_escritura():
                resumen = sesion.obtener_resumen_inicial()
                return {
                    "type": "speak",
                    "text": f"¡Hola {datos_cliente.get('nombre', '')}! He analizado tu escritura y hay cosas fascinantes que contarte.\n\n{resumen}\n\n¿Qué te parece este análisis? ¿Hay algo que te llama especialmente la atención?"
                }
            else:
                return {
                    "type": "speak",
                    "text": f"Hola {datos_cliente.get('nombre', '')}. Para hacer tu análisis grafológico, necesito que me confirmes que ya enviaste tu muestra de escritura por email. ¿La enviaste?"
                }
        
        # 2. CONFIRMACIÓN DE FOTOS
        if not sesion.analisis_tecnico and mensaje_usuario:
            confirmacion_patterns = ['sí', 'si', 'ya envié', 'ya mandé', 'ya las envié', 'enviadas', 'listo', 'hecho']
            if any(pattern in mensaje_usuario.lower() for pattern in confirmacion_patterns):
                if sesion.analizar_escritura():
                    resumen = sesion.obtener_resumen_inicial()
                    return {
                        "type": "speak",
                        "text": f"Perfecto. He analizado tu escritura y hay cosas muy interesantes que revelarte.\n\n{resumen}\n\n¿Qué opinas de este análisis inicial?"
                    }
                else:
                    return {
                        "type": "speak",
                        "text": "No he podido encontrar tu muestra de escritura. ¿Podrías verificar que la enviaste al email correcto? Mientras tanto, cuéntame, ¿qué aspectos de tu personalidad te gustaría conocer mejor?"
                    }
            else:
                return {
                    "type": "speak",
                    "text": "Te he enviado instrucciones por email sobre cómo mandar tu muestra de escritura. Una vez que la envíes, podremos continuar con tu análisis. ¿Tienes alguna pregunta sobre el proceso?"
                }
        
        # 3. CONVERSACIÓN ACTIVA
        if sesion.analisis_tecnico and mensaje_usuario:
            
            # Detectar si quiere explorar dimensión específica
            dimensiones = ['sociabilidad', 'autocontrol', 'organizacion', 'detalle', 'energia', 'emotividad']
            dimension_detectada = None
            
            for dim in dimensiones:
                if dim in mensaje_usuario.lower() or any(palabra in mensaje_usuario.lower() 
                    for palabra in [dim, dim.replace('organizacion', 'organización')]):
                    dimension_detectada = dim
                    break
            
            # Palabras clave para dimensiones
            if 'social' in mensaje_usuario.lower() or 'gente' in mensaje_usuario.lower():
                dimension_detectada = 'sociabilidad'
            elif 'control' in mensaje_usuario.lower() or 'tranquil' in mensaje_usuario.lower():
                dimension_detectada = 'autocontrol'
            elif 'orden' in mensaje_usuario.lower() or 'organiz' in mensaje_usuario.lower():
                dimension_detectada = 'organizacion'
            elif 'detall' in mensaje_usuario.lower() or 'precis' in mensaje_usuario.lower():
                dimension_detectada = 'detalle'
            elif 'energi' in mensaje_usuario.lower() or 'vital' in mensaje_usuario.lower():
                dimension_detectada = 'energia'
            elif 'emocion' in mensaje_usuario.lower() or 'sentimi' in mensaje_usuario.lower():
                dimension_detectada = 'emotividad'
            
            if dimension_detectada:
                respuesta = sesion.explorar_dimension(dimension_detectada)
                pregunta_siguiente = sesion.sugerir_siguiente_tema()
                return {
                    "type": "speak",
                    "text": f"{respuesta}\n\n{pregunta_siguiente}"
                }
            
            # Detectar si quiere finalizar
            finalizacion_patterns = ['terminar', 'acabar', 'finalizar', 'informe', 'resumen', 'listo', 'suficiente']
            if any(pattern in mensaje_usuario.lower() for pattern in finalizacion_patterns):
                resultado_informe = sesion.finalizar_y_enviar_informe()
                
                if resultado_informe:
                    return {
                        "type": "speak",
                        "text": f"Ha sido un placer analizar tu escritura, {datos_cliente.get('nombre', '')}. Te he enviado tu informe completo por email con todo lo que hemos hablado y mucho más detalle. ¡Espero que te sea muy útil para tu autoconocimiento! ¿Tienes alguna última pregunta?"
                    }
                else:
                    return {
                        "type": "speak",
                        "text": "He preparado tu análisis completo. Si tienes alguna última pregunta sobre tu personalidad, este es un buen momento para hacerla."
                    }
            
            # Respuesta general a preguntas
            respuesta = sesion.responder_pregunta(mensaje_usuario)
            
            # Sugerir siguiente tema si no se ha explorado mucho
            if len(sesion.temas_explorados) < 3:
                siguiente_pregunta = sesion.sugerir_siguiente_tema()
                respuesta += f"\n\n{siguiente_pregunta}"
            else:
                respuesta += "\n\n¿Te gustaría que profundicemos en algún aspecto específico o prefieres que te genere tu informe completo?"
            
            return {
                "type": "speak",
                "text": respuesta
            }
        
        # 4. RESPUESTA GENERAL
        return {
            "type": "speak",
            "text": f"Hola {datos_cliente.get('nombre', '')}, soy tu especialista en grafología. Estoy aquí para analizar tu escritura y revelarte aspectos fascinantes de tu personalidad. ¿Ya enviaste tu muestra de escritura por email?"
        }
        
    except Exception as e:
        print(f"❌ Error en grafología webhook: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "speak", 
            "text": "Disculpa, ha ocurrido un error técnico. ¿Podrías repetir tu pregunta sobre grafología?"
        }
    
    finally:
        # Limpiar sesiones viejas (más de 2 horas)
        try:
            ahora = datetime.now()
            sesiones_a_eliminar = []
            for sid, sesion in sesiones_activas.items():
                if (ahora - sesion.inicio_sesion).total_seconds() > 7200:  # 2 horas
                    sesiones_a_eliminar.append(sid)
            
            for sid in sesiones_a_eliminar:
                del sesiones_activas[sid]
        except:
            pass