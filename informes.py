"""
Sistema de generación de informes personalizados para AS Cartastral
Genera informes HTML y PDF para los 7 tipos de servicios IA
"""

import os
import pytz
from datetime import datetime
from playwright.sync_api import sync_playwright
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Template
import sys

# ========================================
# 🔧 FIX IMÁGENES - Búsqueda mejorada
# ========================================

def obtener_ruta_imagen_absoluta(nombre_imagen):
    """Obtener ruta accesible para Playwright/navegador - VERSIÓN MEJORADA FINAL"""
    import os
    import shutil
    
    print(f"🔍 Buscando imagen: {nombre_imagen}")
    
    # Si viene con path, extraer solo el nombre
    if '/' in nombre_imagen:
        nombre_imagen = os.path.basename(nombre_imagen)
    
    # Lista de directorios donde buscar (orden de prioridad)
    directorios_busqueda = [
        './static/img/',  # PRIMERO: Directorio protegido
        './img/',         # SEGUNDO: Directorio original
        '/app/img/',      # TERCERO: Railway absoluto
        '/app/static/img/', # CUARTO: Railway static
        './',             # QUINTO: Raíz
    ]
    
    # Buscar archivo en cada directorio
    for directorio in directorios_busqueda:
        if os.path.exists(directorio):
            ruta_completa = os.path.join(directorio, nombre_imagen)
            
            if os.path.exists(ruta_completa):
                print(f"✅ Imagen encontrada: {ruta_completa}")
                
                # Si está en img/ pero no en static/img/, copiarla para protegerla
                if directorio == './img/' and os.path.exists('./static/img/'):
                    try:
                        destino = f"./static/img/{nombre_imagen}"
                        if not os.path.exists(destino):
                            shutil.copy2(ruta_completa, destino)
                            print(f"🛡️ Imagen copiada a directorio protegido: {destino}")
                        return destino  # Usar la versión protegida
                    except Exception as e:
                        print(f"⚠️ No se pudo copiar, usando original: {e}")
                
                return ruta_completa
    
    # Si no se encuentra, crear placeholder y alertar
    print(f"❌ IMAGEN NO ENCONTRADA: {nombre_imagen}")
    return f"data:image/svg+xml;charset=UTF-8,%3csvg width='200' height='150' xmlns='http://www.w3.org/2000/svg'%3e%3crect width='200' height='150' fill='%23f0f0f0'/%3e%3ctext x='100' y='75' text-anchor='middle' font-size='12' fill='%23666'%3e{nombre_imagen}%3c/text%3e%3c/svg%3e"

def crear_placeholder_svg(nombre_imagen):
    """Crear placeholder SVG inline"""
    import base64
    
    if 'logo' in nombre_imagen.lower():
        svg_content = """<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
  <rect width="200" height="100" fill="#2c5aa0"/>
  <text x="100" y="35" font-family="Arial" font-size="18" fill="white" text-anchor="middle">AS</text>
  <text x="100" y="60" font-family="Arial" font-size="14" fill="#DAA520" text-anchor="middle">Cartastral</text>
</svg>"""
    else:
        svg_content = f"""<svg width="400" height="400" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="400" fill="#ff9800"/>
  <text x="200" y="180" font-family="Arial" font-size="16" fill="white" text-anchor="middle">Imagen disponible</text>
  <text x="200" y="220" font-family="Arial" font-size="12" fill="white" text-anchor="middle">{nombre_imagen}</text>
</svg>"""
    
    svg_b64 = base64.b64encode(svg_content.encode()).decode()
    return f"data:image/svg+xml;base64,{svg_b64}"

def corregir_rutas_imagenes_cartas(datos_template):
    """Corregir rutas de imágenes de cartas generadas"""
    import os
    
    campos_imagen = [
        'carta_natal_img', 'progresiones_img', 'transitos_img',
        'revolucion_img', 'revolucion_natal_img', 'sinastria_img',
        'carta_horaria_img', 'mano_derecha_img', 'mano_izquierda_img',
        'cara_frente_img', 'cara_izquierda_img', 'cara_derecha_img'
    ]
    
    for campo in campos_imagen:
        if campo in datos_template and datos_template[campo]:
            ruta_original = datos_template[campo]
            
            # Quitar file:// si existe
            if ruta_original.startswith('file://'):
                ruta_original = ruta_original.replace('file://', '')
            
            # Usar ruta absoluta si existe
            if os.path.exists(ruta_original):
                datos_template[campo] = os.path.abspath(ruta_original)
            else:
                nombre_archivo = os.path.basename(ruta_original)
                datos_template[campo] = obtener_ruta_imagen_absoluta(nombre_archivo)
    
    return datos_template

def obtener_template_anexo_medio_tiempo(tipo_servicio):
    """Templates para productos M (medio tiempo)"""
    
    css_anexo = """
    <style>
        body { font-family: 'Georgia', serif; margin: 40px 20px; line-height: 1.6; color: #333; }
        .encabezado-anexo { background: linear-gradient(135deg, #ff9800, #ffb74d); padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; border: 3px solid #f57c00; }
        .encabezado-anexo h1 { color: white; font-size: 24px; margin: 0 0 15px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
        .encabezado-anexo p { color: white; margin: 5px 0; font-weight: bold; }
        .badge-continuacion { background: #4caf50; color: white; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 10px; }
        h2 { font-size: 20px; margin-top: 30px; border-bottom: 2px solid #ff9800; padding-bottom: 8px; color: #f57c00; }
        .interpretacion { background: #fff8e1; padding: 20px; border-left: 4px solid #ff9800; margin: 20px 0; border-radius: 4px; }
        .resumen-sesion { background: #e8f5e8; padding: 25px; border-radius: 8px; margin: 30px 0; border-left: 4px solid #4caf50; }
        .footer { text-align: center; margin-top: 60px; padding: 20px; background: #f8f9fa; border-radius: 8px; font-size: 12px; color: #666; }
        .dato { font-weight: bold; color: #f57c00; }
    </style>
    """
    
    # Determinar detalles según tipo
    if tipo_servicio == 'carta_astral_ia_half':
        duracion, codigo, titulo = "20 minutos", "AIM", "CARTA ASTRAL"
    elif tipo_servicio == 'revolucion_solar_ia_half':
        duracion, codigo, titulo = "25 minutos", "RSM", "REVOLUCIÓN SOLAR"
    elif tipo_servicio == 'sinastria_ia_half':
        duracion, codigo, titulo = "15 minutos", "SIM", "SINASTRÍA"
    elif tipo_servicio == 'lectura_manos_ia_half':
        duracion, codigo, titulo = "15 minutos", "LMM", "LECTURA DE MANOS"
    elif tipo_servicio == 'psico_coaching_ia_half':
        duracion, codigo, titulo = "20 minutos", "PCM", "PSICO-COACHING"
    else:
        duracion, codigo, titulo = "Medio tiempo", "XXM", "SESIÓN"
    
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ANEXO - {titulo} Continuación - AS Cartastral</title>
    {css_anexo}
</head>
<body>
    <div class="encabezado-anexo">
        <h1>📋 ANEXO - CONTINUACIÓN {titulo}</h1>
        <p><strong>Cliente:</strong> {{{{ nombre }}}}</p>
        <p><strong>Email:</strong> {{{{ email }}}}</p>
        <p><strong>Duración:</strong> {duracion} (½ tiempo)</p>
        <p><strong>Fecha:</strong> {{{{ fecha_generacion }}}}</p>
        <div class="badge-continuacion">✨ SESIÓN DE SEGUIMIENTO</div>
    </div>

    <div class="resumen-sesion">
        <h2>📞 Continuación de tu Consulta</h2>
        <p><span class="dato">Código:</span> {codigo} - {titulo} IA (½ tiempo)</p>
        <p><span class="dato">Modalidad:</span> Sesión telefónica de seguimiento</p>
        
        {{{% if resumen_sesion %}}}
        <div class="interpretacion">
            {{{{ resumen_sesion }}}}
        </div>
        {{{% endif %}}}
    </div>

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
        <p><strong>Código de sesión:</strong> {codigo} - {titulo} IA (½ tiempo)</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
        <p><em>Este anexo complementa tu informe principal</em></p>
    </div>
</body>
</html>"""

def obtener_portada_con_logo(tipo_servicio, nombre_cliente):
    """Generar portada con logo AS Cartastral + imagen del servicio - VERSIÓN FINAL"""
    
    # DICCIONARIO CON EXTENSIONES CORRECTAS (.JPG)
    imagenes_servicios = {
        # CARTA ASTRAL
        'carta_astral_ia': 'astrologia-3.JPG',
        'carta_natal': 'astrologia-3.JPG', 
        'carta_astral_ia_half': 'astrologia-3.JPG',  # ✅ PRODUCTO M
        
        # REVOLUCIÓN SOLAR
        'revolucion_solar_ia': 'Tarot y astrologia-5.JPG',
        'revolucion_solar': 'Tarot y astrologia-5.JPG',
        'revolucion_solar_ia_half': 'Tarot y astrologia-5.JPG',  # ✅ PRODUCTO M
        
        # SINASTRÍA  
        'sinastria_ia': 'Sinastria.JPG',
        'sinastria': 'Sinastria.JPG',
        'sinastria_ia_half': 'Sinastria.JPG',  # ✅ PRODUCTO M
        
        # ASTROLOGÍA HORARIA
        'astrologia_horaria_ia': 'astrologia-1.JPG',
        'astrol_horaria': 'astrologia-1.JPG',
        
        # LECTURA DE MANOS
        'lectura_manos_ia': 'Lectura-de-manos-p.jpg',
        'lectura_manos': 'Lectura-de-manos-p.jpg', 
        'lectura_manos_ia_half': 'Lectura-de-manos-p.jpg',  # ✅ PRODUCTO M
        
        # LECTURA FACIAL
        'lectura_facial_ia': 'lectura facial.JPG',
        'lectura_facial': 'lectura facial.JPG',
        
        # PSICO-COACHING
        'psico_coaching_ia': 'coaching-4.JPG',
        'psico_coaching': 'coaching-4.JPG',
        'psico_coaching_ia_half': 'coaching-4.JPG',  # ✅ PRODUCTO M
        
        # GRAFOLOGÍA
        'grafologia_ia': 'grafologia_2.jpeg',
        'grafologia': 'grafologia_2.jpeg'
    }
    
    titulos_servicios = {
        'carta_astral_ia': '🌟 CARTA ASTRAL PERSONALIZADA 🌟',
        'carta_natal': '🌟 CARTA ASTRAL PERSONALIZADA 🌟',
        'carta_astral_ia_half': '🌟 CARTA ASTRAL - CONTINUACIÓN 🌟',
        
        'revolucion_solar_ia': '🌟 CARTA ASTRAL + REVOLUCIÓN SOLAR 🌟',
        'revolucion_solar': '🌟 CARTA ASTRAL + REVOLUCIÓN SOLAR 🌟', 
        'revolucion_solar_ia_half': '🌟 REVOLUCIÓN SOLAR - CONTINUACIÓN 🌟',
        
        'sinastria_ia': '💕 SINASTRÍA ASTROLÓGICA 💕',
        'sinastria': '💕 SINASTRÍA ASTROLÓGICA 💕',
        'sinastria_ia_half': '💕 SINASTRÍA - CONTINUACIÓN 💕',
        
        'astrologia_horaria_ia': '⏰ ASTROLOGÍA HORARIA ⏰',
        'astrol_horaria': '⏰ ASTROLOGÍA HORARIA ⏰',
        
        'lectura_manos_ia': '🤚 LECTURA DE MANOS PERSONALIZADA 🤚',
        'lectura_manos': '🤚 LECTURA DE MANOS PERSONALIZADA 🤚',
        'lectura_manos_ia_half': '🤚 LECTURA DE MANOS - CONTINUACIÓN 🤚',
        
        'lectura_facial_ia': '😊 LECTURA FACIAL PERSONALIZADA 😊',
        'lectura_facial': '😊 LECTURA FACIAL PERSONALIZADA 😊',
        
        'psico_coaching_ia': '🧠 SESIÓN DE PSICO-COACHING 🧠',
        'psico_coaching': '🧠 SESIÓN DE PSICO-COACHING 🧠',
        'psico_coaching_ia_half': '🧠 PSICO-COACHING - CONTINUACIÓN 🧠',
        
        'grafologia_ia': '✍️ ANÁLISIS GRAFOLÓGICO ✍️',
        'grafologia': '✍️ ANÁLISIS GRAFOLÓGICO ✍️'
    }
    
    # Obtener los valores del diccionario
    imagen_servicio = imagenes_servicios.get(tipo_servicio, 'astrologia-3.JPG')
    titulo_servicio = titulos_servicios.get(tipo_servicio, '🌟 INFORME PERSONALIZADO 🌟')
    
    # Obtener las rutas usando la función mejorada
    ruta_logo = obtener_ruta_imagen_absoluta('logo.JPG')
    ruta_imagen_servicio = obtener_ruta_imagen_absoluta(imagen_servicio)
    
    # HTML con diseño dorado y elegante
    return f"""
    <div class="portada">
        <div class="marco-dorado-superior"></div>
        <div class="marco-dorado-lateral"></div>
        
        <div class="logo-header">
            <img src="{ruta_logo}" alt="AS Cartastral" class="logo-esquina">
            <span class="nombre-empresa">AS Cartastral</span>
        </div>
        
        <h1 class="titulo-principal">{titulo_servicio}</h1>
        
        <div class="imagen-servicio">
            <img src="{ruta_imagen_servicio}" alt="{tipo_servicio}" class="imagen-central">
        </div>
        
        <h2 class="nombre-cliente">{nombre_cliente}</h2>
        
        <h3 class="subtitulo">Tu análisis personalizado</h3>
        
        <div class="fecha-portada">
            <p>Generado el {datetime.now(pytz.timezone('Europe/Madrid')).strftime('%d de %B de %Y')}</p>
        </div>
    </div>
    """

# ========================================
# ACTUALIZAR ESTILOS CON LOGO DORADO E ITALICS
# ========================================

def obtener_estilos_portada_mejorada():
    """Estilos CSS para portada con marcos dorados y diseño elegante"""
    return """
    .portada {
        text-align: center;
        margin-top: 30px;
        page-break-after: always;
        position: relative;
        min-height: 90vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 40px 20px;
    }
    
    /* MARCOS DORADOS DECORATIVOS */
    .marco-dorado-superior {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 8px;
        background: linear-gradient(90deg, #DAA520, #FFD700, #DAA520);
        box-shadow: 0 2px 4px rgba(218, 165, 32, 0.3);
    }
    
    .marco-dorado-lateral {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 8px;
        background: linear-gradient(180deg, #DAA520, #FFD700, #DAA520);
        box-shadow: 2px 0 4px rgba(218, 165, 32, 0.3);
    }
    
    /* LOGO EN ESQUINA SUPERIOR */
    .logo-header {
        position: absolute;
        top: 30px;
        left: 30px;
        display: flex;
        align-items: center;
        gap: 15px;
        z-index: 10;
    }
    
    .logo-esquina {
        height: 4cm;
        width: auto;
        object-fit: contain;
        border: 2px solid #DAA520;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .nombre-empresa {
        font-size: 24px;
        font-weight: bold;
        color: #DAA520;
        font-family: 'Georgia', serif;
        font-style: italic;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    /* TÍTULO PRINCIPAL */
    .titulo-principal {
        font-size: 32px;
        margin: 120px 0 40px 0;
        color: #2c5aa0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        font-weight: bold;
    }
    
    /* IMAGEN CENTRAL DEL SERVICIO */
    .imagen-servicio {
        margin: 40px 0;
        display: flex;
        justify-content: center;
    }
    
    .imagen-central {
        max-width: 8cm;
        max-height: 6cm;
        object-fit: contain;
        border: 3px solid #DAA520;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        background: white;
        padding: 10px;
    }
    
    /* NOMBRE DEL CLIENTE */
    .nombre-cliente {
        font-size: 28px;
        color: #DAA520;
        font-weight: bold;
        margin: 30px 0 20px 0;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    /* SUBTÍTULO */
    .subtitulo {
        font-size: 18px;
        color: #666;
        font-style: italic;
        margin-bottom: 40px;
    }
    
    /* FECHA */
    .fecha-portada {
        font-size: 16px;
        color: #2c5aa0;
        font-weight: bold;
        margin-top: auto;
    }
    """

def generar_nombre_archivo_unico(tipo_servicio, codigo_cliente):
    """Generar nombre único para archivos"""
    timestamp = datetime.now(pytz.timezone('Europe/Madrid')).strftime("%Y%m%d%H%M%S")
    
    prefijos = {
        'carta_astral_ia': 'AI',
        'carta_natal': 'AI',  # Alias
        'revolucion_solar_ia': 'RS', 
        'revolucion_solar': 'RS',  # Alias
        'sinastria_ia': 'SI',
        'sinastria': 'SI',  # Alias
        'astrologia_horaria_ia': 'AH',
        'astrol_horaria': 'AH',  # Alias
        'psico_coaching_ia': 'PC',
        'psico_coaching': 'PC',  # Alias
        'lectura_manos_ia': 'LM',
        'lectura_manos': 'LM',  # Alias
        'lectura_facial_ia': 'LF',
        'lectura_facial': 'LF',  # Alias
        'grafologia_ia': 'GR',
        'grafologia': 'GR'  # Alias
    }
    
    prefijo = prefijos.get(tipo_servicio, 'AI')
    numero = codigo_cliente[-4:] if len(codigo_cliente) >= 4 else '0001'
    
    return f"{prefijo}_{numero}_{timestamp}"

def obtener_template_html(tipo_servicio):
    """Obtener template HTML según tipo de servicio - CON PRODUCTOS M"""
    
    # 🔥 DEBUG CRÍTICO
    print(f"🔥 obtener_template_html EJECUTÁNDOSE - tipo: {tipo_servicio}")
    
    # ✅ PRODUCTOS M (MEDIO TIEMPO) - IMPLEMENTADOS
    productos_medio_tiempo = [
        'carta_astral_ia_half', 'revolucion_solar_ia_half', 'sinastria_ia_half',
        'lectura_manos_ia_half', 'psico_coaching_ia_half'
    ]
    
    # Si es producto M, usar template de anexo
    if tipo_servicio in productos_medio_tiempo:
        print(f"✅ PRODUCTO M DETECTADO: {tipo_servicio} → Usando template anexo")
        return obtener_template_anexo_medio_tiempo(tipo_servicio)
    
    # Template base común para todos - ACTUALIZADO CON NUEVOS ESTILOS
    base_style = f"""
    <style>
        body {{
            font-family: 'Georgia', serif;
            margin: 40px 20px;
            line-height: 1.6;
            color: #333;
            background: #fafafa;
        }}
        
        {obtener_estilos_portada_mejorada()}
        
        h1 {{
            font-size: 26px;
            text-align: center;
            margin-top: 40px;
            color: #2c5aa0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }}
        h2 {{
            font-size: 22px;
            margin-top: 30px;
            border-bottom: 2px solid #2c5aa0;
            padding-bottom: 8px;
            color: #2c5aa0;
        }}
        h3 {{
            font-size: 18px;
            color: #666;
            margin-top: 25px;
        }}
        .dato {{
            font-weight: bold;
            color: #2c5aa0;
        }}
        .interpretacion {{
            background: #f8f9fa;
            padding: 20px;
            border-left: 4px solid #2c5aa0;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            margin-top: 60px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 12px;
            color: #666;
        }}
        .imagen-carta {{
            text-align: center;
            margin: 30px 0;
        }}
        .imagen-carta img {{
            max-width: 100%;
            height: auto;
            border: 2px solid #2c5aa0;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .section {{
            margin-bottom: 40px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
    """

    # TEMPLATES ESPECÍFICOS POR SERVICIO (VERSIÓN NORMAL - NO PRODUCTOS M)
    
    if tipo_servicio in ['carta_astral_ia', 'carta_natal']:
        return base_style + """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ nombre }} - Carta Astral Personalizada - AS Cartastral</title>
</head>
<body>
    {{ obtener_portada_con_logo(tipo_servicio, nombre) }}
    
    <div class="section">
        <h1>🌟 TU CARTA ASTRAL PERSONALIZADA 🌟</h1>
        <p><span class="dato">Cliente:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de nacimiento:</span> {{ fecha_nacimiento }}</p>
        <p><span class="dato">Hora de nacimiento:</span> {{ hora_nacimiento }}</p>
        <p><span class="dato">Lugar de nacimiento:</span> {{ lugar_nacimiento }}</p>
    </div>

    {% if carta_natal_img %}
    <div class="imagen-carta">
        <h2>🗺️ Tu Carta Natal</h2>
        <img src="{{ carta_natal_img }}" alt="Carta Natal" style="max-width: 100%; height: auto;">
        <p>Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento.</p>
    </div>
    {% endif %}

    {% if progresiones_img %}
    <div class="imagen-carta">
        <h2>📈 Progresiones Secundarias</h2>
        <img src="{{ progresiones_img }}" alt="Progresiones" style="max-width: 100%; height: auto;">
    </div>
    {% endif %}

    {% if transitos_img %}
    <div class="imagen-carta">
        <h2>🌊 Tránsitos Actuales</h2>
        <img src="{{ transitos_img }}" alt="Tránsitos" style="max-width: 100%; height: auto;">
    </div>
    {% endif %}

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 40 minutos</p>
        <div class="interpretacion">{{ resumen_sesion }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""

    elif tipo_servicio in ['revolucion_solar_ia', 'revolucion_solar']:
        return base_style + """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ nombre }} - Revolución Solar - AS Cartastral</title>
</head>
<body>
    {{ obtener_portada_con_logo(tipo_servicio, nombre) }}
    
    <div class="section">
        <h1>🌟 CARTA ASTRAL + REVOLUCIÓN SOLAR 🌟</h1>
        <p><span class="dato">Cliente:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de nacimiento:</span> {{ fecha_nacimiento }}</p>
        <p><span class="dato">Hora de nacimiento:</span> {{ hora_nacimiento }}</p>
        <p><span class="dato">Lugar de nacimiento:</span> {{ lugar_nacimiento }}</p>
    </div>

    {% if carta_natal_img %}
    <div class="imagen-carta">
        <h2>🗺️ Tu Carta Natal</h2>
        <img src="{{ carta_natal_img }}" alt="Carta Natal">
    </div>
    {% endif %}

    {% if revolucion_solar_img %}
    <div class="imagen-carta">
        <h2>☀️ Tu Revolución Solar</h2>
        <img src="{{ revolucion_solar_img }}" alt="Revolución Solar">
        <p>Predicciones y tendencias para el año que viene.</p>
    </div>
    {% endif %}

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <div class="interpretacion">{{ resumen_sesion }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""

    elif tipo_servicio in ['sinastria_ia', 'sinastria']:
        return base_style + """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ nombre }} - Sinastría Astrológica - AS Cartastral</title>
</head>
<body>
    {{ obtener_portada_con_logo(tipo_servicio, nombre) }}
    
    <div class="section">
        <h1>💕 SINASTRÍA ASTROLÓGICA 💕</h1>
        <p><span class="dato">Cliente:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
    </div>

    {% if sinastria_img %}
    <div class="imagen-carta">
        <h2>💞 Análisis de Compatibilidad</h2>
        <img src="{{ sinastria_img }}" alt="Sinastría">
        <p>Análisis astrológico de la relación entre ambas personas.</p>
    </div>
    {% endif %}

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <div class="interpretacion">{{ resumen_sesion }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""

    elif tipo_servicio in ['psico_coaching_ia', 'psico_coaching']:
        return base_style + """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ nombre }} - Sesión de Psico-Coaching - AS Cartastral</title>
</head>
<body>
    {{ obtener_portada_con_logo(tipo_servicio, nombre) }}
    
    <div class="section">
        <h1>🧠 SESIÓN DE PSICO-COACHING 🧠</h1>
        <p><span class="dato">Cliente:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
    </div>

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión</h2>
        <p><strong>Duración:</strong> 40 minutos</p>
        <div class="interpretacion">{{ resumen_sesion }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios de Psico-Coaching IA</p>
    </div>
</body>
</html>"""

    elif tipo_servicio in ['lectura_manos_ia', 'lectura_manos']:
        return base_style + """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ nombre }} - Lectura de Manos - AS Cartastral</title>
</head>
<body>
    {{ obtener_portada_con_logo(tipo_servicio, nombre) }}
    
    <div class="section">
        <h1>🤚 LECTURA DE MANOS PERSONALIZADA 🤚</h1>
        <p><span class="dato">Cliente:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
    </div>

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión</h2>
        <div class="interpretacion">{{ resumen_sesion }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generación }} a las {{ hora_generación }}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""

    # Para otros servicios (grafología, lectura facial, astrología horaria)
    else:
        return base_style + f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{{{ nombre }}}} - {tipo_servicio.replace('_', ' ').title()} - AS Cartastral</title>
</head>
<body>
    {{{{ obtener_portada_con_logo(tipo_servicio, nombre) }}}}
    
    <div class="section">
        <h1>✨ {tipo_servicio.replace('_', ' ').upper()} ✨</h1>
        <p><span class="dato">Cliente:</span> {{{{ nombre }}}}</p>
        <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    </div>

    {{% if resumen_sesion %}}
    <div class="section">
        <h2>📞 Resumen de tu Sesión</h2>
        <div class="interpretacion">{{{{ resumen_sesion }}}}</div>
    </div>
    {{% endif %}}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""

# ========================================
# 🔥 FIX DEFINITIVO - REEMPLAZAR EN informes.py
# ========================================

def generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion=""):
    """FUNCIÓN DEFINITIVA - Reemplaza la función rota"""
    from datetime import datetime
    import pytz
    import os
    
    try:
        print(f"🔥 DEFINITIVO: Generando HTML para {tipo_servicio}")
        
        # Detectar si es producto M
        es_producto_m = tipo_servicio.endswith('_half')
        
        # Datos básicos
        fecha_actual = datetime.now(pytz.timezone('Europe/Madrid'))
        fecha_generacion = fecha_actual.strftime('%d de %B de %Y')
        hora_generacion = fecha_actual.strftime('%H:%M')
        
        if es_producto_m:
            # TEMPLATE ANEXO (SIN PORTADA)
            html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ANEXO - {datos_cliente.get('nombre', 'Cliente')} - AS Cartastral</title>
    <style>
        body {{ font-family: Georgia, serif; margin: 30px; line-height: 1.6; color: #333; background: #fafafa; }}
        .encabezado-anexo {{ background: linear-gradient(135deg, #f57c00, #ff9800); color: white; padding: 25px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
        .encabezado-anexo h1 {{ color: white; font-size: 24px; margin: 0 0 15px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }}
        .badge-continuacion {{ background: #4caf50; color: white; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 10px; }}
        h2 {{ font-size: 20px; margin-top: 30px; border-bottom: 2px solid #ff9800; padding-bottom: 8px; color: #f57c00; }}
        .interpretacion {{ background: #fff8e1; padding: 20px; border-left: 4px solid #ff9800; margin: 20px 0; border-radius: 4px; }}
        .footer {{ text-align: center; margin-top: 60px; padding: 20px; background: #f8f9fa; border-radius: 8px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="encabezado-anexo">
        <h1>📋 ANEXO - CONTINUACIÓN {tipo_servicio.replace('_half', '').replace('_', ' ').upper()}</h1>
        <p><strong>Cliente:</strong> {datos_cliente.get('nombre', 'Cliente')}</p>
        <p><strong>Email:</strong> {datos_cliente.get('email', 'email@test.com')}</p>
        <p><strong>Duración:</strong> {archivos_unicos.get('duracion_minutos', 20)} minutos (½ tiempo)</p>
        <div class="badge-continuacion">✨ SESIÓN DE SEGUIMIENTO</div>
    </div>

    <div class="interpretacion">
        <h2>📞 Continuación de tu Consulta</h2>
        <p>Esta es la continuación de tu sesión anterior, con análisis adicional personalizado.</p>
        {f'<div>{resumen_sesion}</div>' if resumen_sesion else '<p>Contenido de la sesión de seguimiento.</p>'}
    </div>

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {fecha_generacion} a las {hora_generacion}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
        <p><em>Este anexo complementa tu informe principal</em></p>
    </div>
</body>
</html>"""
        else:
            # TEMPLATE COMPLETO (CON PORTADA DORADA)
            html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{datos_cliente.get('nombre', 'Cliente')} - {tipo_servicio.replace('_', ' ').title()} - AS Cartastral</title>
    <style>
        body {{ font-family: Georgia, serif; margin: 30px; line-height: 1.6; color: #333; background: #fafafa; }}
        
        .portada {{ 
            text-align: center; margin: 30px 0; page-break-after: always; position: relative; 
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 40px 20px; border-radius: 10px;
            border-top: 8px solid #DAA520; border-left: 8px solid #DAA520; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .logo-header {{ position: absolute; top: 20px; left: 20px; display: flex; align-items: center; gap: 15px; }}
        .logo-esquina {{ width: 60px; height: 60px; background: #DAA520; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; border-radius: 8px; }}
        .nombre-empresa {{ font-size: 20px; font-weight: bold; color: #DAA520; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }}
        
        .titulo-principal {{ font-size: 28px; margin: 80px 0 30px 0; color: #2c5aa0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }}
        .nombre-cliente {{ font-size: 24px; color: #DAA520; font-weight: bold; margin: 20px 0; text-transform: uppercase; }}
        .subtitulo {{ font-size: 16px; color: #666; font-style: italic; }}
        
        h1 {{ font-size: 24px; text-align: center; margin: 40px 0 20px 0; color: #2c5aa0; }}
        h2 {{ font-size: 20px; margin-top: 30px; border-bottom: 2px solid #2c5aa0; padding-bottom: 8px; color: #2c5aa0; }}
        .dato {{ font-weight: bold; color: #2c5aa0; }}
        .interpretacion {{ background: #f8f9fa; padding: 20px; border-left: 4px solid #2c5aa0; margin: 20px 0; border-radius: 4px; }}
        .footer {{ text-align: center; margin-top: 60px; padding: 20px; background: #f8f9fa; border-radius: 8px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="portada">
        <div class="logo-header">
            <div class="logo-esquina">AS</div>
            <span class="nombre-empresa">AS Cartastral</span>
        </div>
        
        <h1 class="titulo-principal">🌟 {tipo_servicio.replace('_', ' ').upper()} 🌟</h1>
        <h2 class="nombre-cliente">{datos_cliente.get('nombre', 'Cliente')}</h2>
        <h3 class="subtitulo">Tu análisis personalizado</h3>
        
        <div style="margin-top: 40px;">
            <p>Generado el {fecha_generacion}</p>
        </div>
    </div>
    
    <div style="background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1>✨ {tipo_servicio.replace('_', ' ').upper()} ✨</h1>
        <p><span class="dato">Cliente:</span> {datos_cliente.get('nombre', 'Cliente')}</p>
        <p><span class="dato">Email:</span> {datos_cliente.get('email', 'email@test.com')}</p>
        <p><span class="dato">Fecha de nacimiento:</span> {datos_cliente.get('fecha_nacimiento', 'No especificada')}</p>
        <p><span class="dato">Hora de nacimiento:</span> {datos_cliente.get('hora_nacimiento', 'No especificada')}</p>
        <p><span class="dato">Lugar de nacimiento:</span> {datos_cliente.get('lugar_nacimiento', 'No especificado')}</p>
    </div>

    {f'<div class="interpretacion"><h2>📞 Resumen de tu Sesión</h2><div>{resumen_sesion}</div></div>' if resumen_sesion else ''}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {fecha_generacion} a las {hora_generacion}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""
        
        # Guardar archivo HTML
        archivo_html = archivos_unicos.get('informe_html', f"templates/definitivo_{tipo_servicio}_{datos_cliente.get('codigo_servicio', 'test')}.html")
        
        os.makedirs('templates', exist_ok=True)
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ DEFINITIVO: HTML guardado en {archivo_html}")
        return archivo_html
        
    except Exception as e:
        print(f"❌ DEFINITIVO ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def convertir_html_a_pdf(archivo_html, archivo_pdf):
    """Convertir HTML a PDF usando Playwright"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Leer el archivo HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Establecer el contenido HTML
            page.set_content(html_content)
            
            # Generar PDF
            page.pdf(
                path=archivo_pdf,
                format='A4',
                margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'},
                print_background=True
            )
            
            browser.close()
            
        print(f"✅ PDF generado: {archivo_pdf}")
        return True
        
    except Exception as e:
        print(f"❌ Error con Playwright: {e}")
        return False

def enviar_informe_por_email(email_cliente, archivo_pdf, tipo_servicio, nombre_cliente="Cliente"):
    """Enviar informe por email"""
    try:
        # Configuración email
        email_sender = os.getenv("EMAIL_SENDER")
        email_password = os.getenv("EMAIL_PASSWORD")
        
        if not email_sender or not email_password:
            print("❌ Credenciales de email no configuradas")
            return False
        
        # Determinar nombre del servicio
        nombres_servicios = {
            'carta_astral_ia': 'Carta Astral',
            'carta_natal': 'Carta Astral',
            'revolucion_solar_ia': 'Carta Astral + Revolución Solar',
            'revolucion_solar': 'Carta Astral + Revolución Solar',
            'sinastria_ia': 'Sinastría Astrológica',
            'sinastria': 'Sinastría Astrológica',
            'astrologia_horaria_ia': 'Astrología Horaria',
            'astrol_horaria': 'Astrología Horaria',
            'lectura_manos_ia': 'Lectura de Manos',
            'lectura_manos': 'Lectura de Manos',
            'lectura_facial_ia': 'Lectura Facial',
            'lectura_facial': 'Lectura Facial',
            'psico_coaching_ia': 'Psico-Coaching',
            'psico_coaching': 'Psico-Coaching',
            'grafologia_ia': 'Análisis Grafológico',
            'grafologia': 'Análisis Grafológico'
        }
        
        nombre_servicio = nombres_servicios.get(tipo_servicio, 'Informe Personalizado')
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = email_sender
        msg['To'] = email_cliente
        msg['Subject'] = f"Tu informe de {nombre_servicio} - AS Cartastral"
        
        # Cuerpo del email
        cuerpo = f"""
Estimado/a {nombre_cliente},

Te enviamos tu informe personalizado de {nombre_servicio} que has solicitado.

Este informe contiene:
✨ Análisis detallado basado en tu sesión telefónica
📊 Gráficos e imágenes personalizadas 
📝 Resumen completo de todo lo tratado durante la consulta
🔮 Interpretaciones y recomendaciones específicas para ti

Fecha de generación: {datetime.now(pytz.timezone('Europe/Madrid')).strftime('%d/%m/%Y %H:%M')}

Esperamos que este análisis te sea de gran utilidad para tu crecimiento personal.

Si tienes alguna duda sobre tu informe, no dudes en contactarnos.

Saludos cordiales,
Equipo AS Cartastral
📧 Email: {email_sender}
🌐 Web: AS Cartastral - Servicios Astrológicos Personalizados

---
Nota: Este informe es confidencial y está destinado únicamente para el uso personal del destinatario.
        """
        
        msg.attach(MIMEText(cuerpo, 'plain'))
        
        # Adjuntar archivo
        if os.path.exists(archivo_pdf):
            with open(archivo_pdf, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                
                # Generar nombre de archivo para el email
                timestamp = datetime.now().strftime('%Y%m%d')
                prefijo = generar_nombre_archivo_unico(tipo_servicio, '').split('_')[0]
                nombre_archivo = f"Informe_{nombre_servicio.replace(' ', '_')}_{timestamp}.pdf"
                
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {nombre_archivo}'
                )
                msg.attach(part)
        
        # Enviar email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_sender, email_password)
        text = msg.as_string()
        server.sendmail(email_sender, email_cliente, text)
        server.quit()
        
        print(f"✅ Informe de {nombre_servicio} enviado por email a: {email_cliente}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        import traceback
        traceback.print_exc()
        return False

def procesar_y_enviar_informe(datos_cliente, tipo_servicio, archivos_unicos=None, resumen_sesion=""):
    """Generar informe HTML y convertir a PDF"""
    try:
        print(f"🔄 Generando informe para {datos_cliente.get('nombre', 'Cliente')} - {tipo_servicio}")
        
        # Generar HTML
        archivo_html = generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion)
        
        if not archivo_html:
            print("❌ Error generando HTML")
            return None
        
        # Generar PDF
        nombre_base = generar_nombre_archivo_unico(tipo_servicio, datos_cliente.get('codigo_servicio', ''))
        archivo_pdf = f"informes/{nombre_base}.pdf"
        
        # Crear directorio si no existe
        os.makedirs('informes', exist_ok=True)
        
        exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
        
        if exito_pdf:
            # Enviar por email
            exito_email = enviar_informe_por_email(
                datos_cliente['email'], 
                archivo_pdf, 
                tipo_servicio, 
                datos_cliente.get('nombre', 'Cliente')
            )
            
            if exito_email:
                print(f"✅ Informe completo enviado: {archivo_pdf}")
                return archivo_pdf
            else:
                print("❌ Error enviando email")
                return archivo_pdf  # PDF generado pero email falló
        else:
            print("❌ Error generando PDF")
            return None
        
    except Exception as e:
        print(f"❌ Error en procesar_y_enviar_informe: {e}")
        import traceback
        traceback.print_exc()
        return None

# Función de utilidad para llamar desde los agentes
def generar_y_enviar_informe_desde_agente(data, tipo_servicio, resumen_conversacion=None):
    """
    Función simplificada para llamar desde los agentes especialistas
    
    Args:
        data: Datos del webhook que contiene información del cliente
        tipo_servicio: Tipo de servicio (carta_astral_ia, sinastria_ia, etc.)
        resumen_conversacion: Resumen de lo hablado en la sesión telefónica
    """
    try:
        # Extraer datos del cliente
        datos_cliente = {
            'nombre': data.get('nombre', 'Cliente'),
            'email': data.get('email', ''),
            'codigo_servicio': data.get('codigo_servicio', ''),
            # Datos astrológicos si existen
            'fecha_nacimiento': data.get('fecha_nacimiento', ''),
            'hora_nacimiento': data.get('hora_nacimiento', ''),
            'lugar_nacimiento': data.get('lugar_nacimiento', ''),
            'pais_nacimiento': data.get('pais_nacimiento', 'España'),
            'planetas': data.get('planetas', {}),
            # Datos específicos de sinastría
            'nombre_persona1': data.get('nombre_persona1', ''),
            'nombre_persona2': data.get('nombre_persona2', ''),
            'fecha_persona1': data.get('fecha_persona1', ''),
            'hora_persona1': data.get('hora_persona1', ''),
            'lugar_persona1': data.get('lugar_persona1', ''),
            'fecha_persona2': data.get('fecha_persona2', ''),
            'hora_persona2': data.get('hora_persona2', ''),
            'lugar_persona2': data.get('lugar_persona2', ''),
            # Datos de astrología horaria
            'fecha_pregunta': data.get('fecha_pregunta', ''),
            'hora_pregunta': data.get('hora_pregunta', ''),
            'lugar_pregunta': data.get('lugar_pregunta', ''),
            'pregunta': data.get('pregunta', ''),
            # Datos de lectura de manos
            'dominancia': data.get('dominancia', '')
        }
        
        # Archivos únicos (imágenes generadas)
        archivos_unicos = data.get('archivos_unicos', {})
        
        # Procesar y enviar informe
        resultado = procesar_y_enviar_informe(
            datos_cliente, 
            tipo_servicio, 
            archivos_unicos, 
            resumen_conversacion
        )
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error en generar_y_enviar_informe_desde_agente: {e}")
        import traceback
        traceback.print_exc()
        return False
        
def obtener_template_anexo_medio_tiempo(tipo_servicio):
    """Template para productos M (medio tiempo) - NUEVOS PRODUCTOS"""
    from datetime import datetime
    import pytz
    
    # CSS específico para anexos
    css_anexo = """
    <style>
        body { font-family: 'Georgia', serif; margin: 40px 20px; line-height: 1.6; color: #333; background: #fafafa; }
        .encabezado-anexo { background: linear-gradient(135deg, #f57c00, #ff9800); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; border: 3px solid #f57c00; }
        .encabezado-anexo h1 { color: white; font-size: 24px; margin: 0 0 15px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
        .encabezado-anexo p { color: white; margin: 5px 0; font-weight: bold; }
        .badge-continuacion { background: #4caf50; color: white; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 10px; }
        h2 { font-size: 20px; margin-top: 30px; border-bottom: 2px solid #ff9800; padding-bottom: 8px; color: #f57c00; }
        .interpretacion { background: #fff8e1; padding: 20px; border-left: 4px solid #ff9800; margin: 20px 0; border-radius: 4px; }
        .resumen-sesion { background: #e8f5e8; padding: 25px; border-radius: 8px; margin: 30px 0; border-left: 4px solid #4caf50; }
        .footer { text-align: center; margin-top: 60px; padding: 20px; background: #f8f9fa; border-radius: 8px; font-size: 12px; color: #666; }
        .dato { font-weight: bold; color: #f57c00; }
    </style>
    """
    
    # Configuración específica por producto M
    config_productos = {
        'carta_astral_ia_half': {'duracion': '20 minutos', 'codigo': 'AIM', 'titulo': 'CARTA ASTRAL'},
        'revolucion_solar_ia_half': {'duracion': '25 minutos', 'codigo': 'RSM', 'titulo': 'REVOLUCIÓN SOLAR'},  
        'sinastria_ia_half': {'duracion': '15 minutos', 'codigo': 'SIM', 'titulo': 'SINASTRÍA'},
        'lectura_manos_ia_half': {'duracion': '15 minutos', 'codigo': 'LMM', 'titulo': 'LECTURA DE MANOS'},
        'psico_coaching_ia_half': {'duracion': '20 minutos', 'codigo': 'PCM', 'titulo': 'PSICO-COACHING'}
    }
    
    config = config_productos.get(tipo_servicio, {'duracion': 'Medio tiempo', 'codigo': 'XXM', 'titulo': 'SESIÓN'})
    
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ANEXO - {config['titulo']} Continuación - AS Cartastral</title>
    {css_anexo}
</head>
<body>
    <div class="encabezado-anexo">
        <h1>📋 ANEXO - CONTINUACIÓN {config['titulo']}</h1>
        <p><strong>Cliente:</strong> {{{{ nombre }}}}</p>
        <p><strong>Email:</strong> {{{{ email }}}}</p>
        <p><strong>Duración:</strong> {config['duracion']} (½ tiempo)</p>
        <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}}</p>
        <div class="badge-continuacion">✨ SESIÓN DE SEGUIMIENTO</div>
    </div>

    <div class="resumen-sesion">
        <h2>📞 Continuación de tu Consulta</h2>
        <p><span class="dato">Código:</span> {config['codigo']} - {config['titulo']} IA (½ tiempo)</p>
        <p><span class="dato">Modalidad:</span> Sesión telefónica de seguimiento</p>
        
        {{% if resumen_sesion %}}
        <div class="interpretacion">
            {{{{ resumen_sesion }}}}
        </div>
        {{% endif %}}
    </div>

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
        <p><strong>Código de sesión:</strong> {config['codigo']} - {config['titulo']} IA (½ tiempo)</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
        <p><em>Este anexo complementa tu informe principal</em></p>
    </div>
</body>
</html>"""

if __name__ == "__main__":
    # Ejemplo de uso para testing
    datos_test = {
        'nombre': 'Albert Test',
        'email': 'test@example.com',
        'codigo_servicio': 'AI_123456',
        'fecha_nacimiento': '15/07/1985',
        'hora_nacimiento': '08:00',
        'lugar_nacimiento': 'Barcelona',
        'pais_nacimiento': 'España'
    }
    
    archivos_test = {
        'carta_natal_img': 'static/carta_natal_test.png',
        'progresiones_img': 'static/progresiones_test.png',
        'transitos_img': 'static/transitos_test.png'
    }
    
    resumen_test = "Durante nuestra sesión de 40 minutos hablamos sobre tu carta astral y las principales influencias planetarias en tu vida."
    
    resultado = procesar_y_enviar_informe(datos_test, 'carta_astral_ia', archivos_test, resumen_test)
    print(f"Resultado del test: {resultado}")