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

# ========================================
# 🔧 FIX IMÁGENES - Búsqueda mejorada
# ========================================

def obtener_ruta_imagen_absoluta(nombre_imagen):
    """Obtener ruta absoluta para imágenes con diferentes extensiones"""
    import os
    
    # Crear variaciones del nombre (jpg, JPG, jpeg, JPEG)
    nombre_base = os.path.splitext(nombre_imagen)[0]
    extensiones = ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']
    
    # Rutas donde buscar
    rutas_busqueda = [
        "./img/",
        "/app/img/", 
        "./static/",
        "/app/static/",
        "."  # Directorio raíz
    ]
    
    # Buscar con todas las combinaciones
    for ruta_base in rutas_busqueda:
        for ext in extensiones:
            archivo_completo = nombre_base + ext
            ruta_completa = os.path.join(ruta_base, archivo_completo)
            if os.path.exists(ruta_completa):
                print(f"✅ Imagen encontrada: {nombre_imagen} → {ruta_completa}")
                return os.path.abspath(ruta_completa)
    
    # Si no existe, crear placeholder
    print(f"⚠️ Imagen no encontrada: {nombre_imagen} - usando placeholder")
    return crear_placeholder_svg(nombre_imagen)

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
    """Generar portada con logo AS Cartastral + imagen del servicio - CORREGIDA"""
    
    # MAPEO IMÁGENES (mantenido igual)
    imagenes_servicios = {
        'carta_astral_ia': 'astrologia-3.jpg',
        'carta_natal': 'astrologia-3.jpg',
        'revolucion_solar_ia': 'Tarot y astrologia-5.jpg', 
        'revolucion_solar': 'Tarot y astrologia-5.jpg',
        'sinastria_ia': 'Sinastria.jpg',
        'sinastria': 'Sinastria.jpg',
        'astrologia_horaria_ia': 'astrologia-1.jpg',
        'astrol_horaria': 'astrologia-1.jpg',
        'lectura_manos_ia': 'Lectura-de-manos-p.jpg',
        'lectura_manos': 'Lectura-de-manos-p.jpg',
        'lectura_facial_ia': 'lectura facial.jpg',
        'lectura_facial': 'lectura facial.jpg',
        'psico_coaching_ia': 'coaching-4.jpg',
        'psico_coaching': 'coaching-4.jpg',
        'grafologia_ia': 'grafologia_2.jpeg',
        'grafologia': 'grafologia_2.jpeg'
    }
    
    titulos_servicios = {
        'carta_astral_ia': '🌟 CARTA ASTRAL PERSONALIZADA 🌟',
        'carta_natal': '🌟 CARTA ASTRAL PERSONALIZADA 🌟',
        'revolucion_solar_ia': '🌟 CARTA ASTRAL + REVOLUCIÓN SOLAR 🌟',
        'revolucion_solar': '🌟 CARTA ASTRAL + REVOLUCIÓN SOLAR 🌟',
        'sinastria_ia': '💕 SINASTRÍA ASTROLÓGICA 💕',
        'sinastria': '💕 SINASTRÍA ASTROLÓGICA 💕',
        'astrologia_horaria_ia': '⏰ ASTROLOGÍA HORARIA ⏰',
        'astrol_horaria': '⏰ ASTROLOGÍA HORARIA ⏰',
        'lectura_manos_ia': '👋 LECTURA DE MANOS PERSONALIZADA 👋',
        'lectura_manos': '👋 LECTURA DE MANOS PERSONALIZADA 👋',
        'lectura_facial_ia': '😊 LECTURA FACIAL PERSONALIZADA 😊',
        'lectura_facial': '😊 LECTURA FACIAL PERSONALIZADA 😊',
        'psico_coaching_ia': '🧠 SESIÓN DE PSICO-COACHING 🧠',
        'psico_coaching': '🧠 SESIÓN DE PSICO-COACHING 🧠'
    }
    
    # ✅ USAR BÚSQUEDA MEJORADA
    imagen_servicio = imagenes_servicios.get(tipo_servicio, 'logo.jpg')
    titulo_servicio = titulos_servicios.get(tipo_servicio, '🌟 INFORME PERSONALIZADO 🌟')
    
    ruta_logo = obtener_ruta_imagen_absoluta('logo.jpg')
    ruta_imagen_servicio = obtener_ruta_imagen_absoluta(imagen_servicio)
    
    return """
    <div class="portada">
        <div class="logo-header">
            <img src="{}" alt="AS Cartastral" class="logo-esquina">
            <span class="nombre-empresa">AS Cartastral</span>
        </div>
        
        <h1 class="titulo-principal">{}</h1>
        
        <div class="imagen-servicio">
            <img src="{}" alt="{}" class="imagen-central">
        </div>
        
        <h2 class="nombre-cliente">{}</h2>
        
        <h3 class="subtitulo">Tu análisis personalizado</h3>
        
        <div class="fecha-portada">
            <p>Generado el {}</p>
        </div>
    </div>
    """.format(
        ruta_logo,
        titulo_servicio, 
        ruta_imagen_servicio,
        tipo_servicio,
        nombre_cliente,
        datetime.now(pytz.timezone('Europe/Madrid')).strftime('%d de %B de %Y')
    )

# ========================================
# ACTUALIZAR ESTILOS CON LOGO DORADO E ITALICS
# ========================================

def obtener_estilos_portada_mejorada():
    """Estilos CSS para la nueva portada con logo e imagen"""
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
    }
    
    /* LOGO EN ESQUINA SUPERIOR */
    .logo-header {
        position: absolute;
        top: 20px;
        left: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .logo-esquina {
        height: 4cm;  /* 4cm de altura como solicitaste */
        width: auto;
        object-fit: contain;
    }
    
    .nombre-empresa {
        font-size: 24px;
        font-weight: bold;
        color: #DAA520;  /* Color dorado */
        font-family: 'Georgia', serif;
        font-style: italic;  /* Italic como solicitaste */
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    /* TÍTULO PRINCIPAL */
    .titulo-principal {
        font-size: 32px;
        margin: 120px 0 40px 0;  /* Más espacio por logo más grande */
        color: #2c5aa0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    /* IMAGEN CENTRAL DEL SERVICIO */
    .imagen-servicio {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 40px 0;
    }
    
    .imagen-central {
        width: 14cm;  /* 14x14 cm como solicitaste */
        height: 14cm;
        object-fit: cover;  /* Cambié a cover para que llene el espacio */
        border: 3px solid #2c5aa0;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        background: white;
        padding: 10px;
    }
    
    /* NOMBRE DEL CLIENTE */
    .nombre-cliente {
        font-size: 28px;
        color: #333;
        margin: 20px 0;
        font-weight: normal;
    }
    
    /* SUBTÍTULO */
    .subtitulo {
        font-size: 18px;
        color: #666;
        font-style: italic;
        margin: 10px 0;
    }
    
    /* FECHA EN PORTADA */
    .fecha-portada {
        margin-top: 40px;
        font-size: 14px;
        color: #888;
    }
    
    @media print {
        .portada {
            page-break-after: always;
        }
        .imagen-central {
            width: 14cm;
            height: 14cm;
        }
        .logo-esquina {
            height: 4cm;
        }
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

# ========================================
# 2. MODIFICAR LA FUNCIÓN obtener_template_html() EXISTENTE (línea 66 aprox)
# ========================================

# REEMPLAZAR TODO EL base_style POR ESTO:
def obtener_template_html(tipo_servicio):
    """Obtener template HTML según tipo de servicio"""
    
    # ✅ PRODUCTOS M (MEDIO TIEMPO) - NUEVOS
    productos_medio_tiempo = [
        'carta_astral_ia_half', 'revolucion_solar_ia_half', 'sinastria_ia_half',
        'lectura_manos_ia_half', 'psico_coaching_ia_half'
    ]
    
    # Si es producto M, usar template de anexo
    if tipo_servicio in productos_medio_tiempo:
        return obtener_template_anexo_medio_tiempo(tipo_servicio)
    
    # Template base común para todos - ACTUALIZADO CON NUEVOS ESTILOS
    base_style = f"""
    <style>
        body {{
            font-family: 'Georgia', serif;
            margin: 40px 20px;
            line-height: 1.6;
            color: #333;
        }}
        
        {obtener_estilos_portada_mejorada()}
        
        h1 {{
            font-size: 26px;
            text-align: center;
            margin-top: 40px;
            color: #2c5aa0;
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
        .carta-img {{
            text-align: center;
            margin: 30px 0;
            page-break-inside: avoid;
        }}
        .carta-img img {{
            width: 100%;
            max-width: 600px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .section {{
            margin-top: 30px;
            page-break-inside: avoid;
        }}
        .datos-natales {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .interpretacion {{
            background: #fff8e1;
            padding: 15px;
            border-left: 4px solid #ff9800;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .resumen-sesion {{
            background: #e8f5e8;
            padding: 20px;
            border-radius: 8px;
            margin: 30px 0;
            border-left: 4px solid #4caf50;
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
        ul.planetas {{
            column-count: 2;
            column-gap: 40px;
            list-style-type: none;
            padding: 0;
        }}
        ul.planetas li {{
            padding: 5px 0;
            border-bottom: 1px dotted #ddd;
        }}
        @media print {{
            body {{ margin: 20px; }}
            .portada {{ page-break-after: always; }}
            .carta-img {{ page-break-inside: avoid; }}
        }}
    </style>
    """
    
    if tipo_servicio in ['carta_astral_ia', 'carta_natal']:
        return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Carta Astral - AS Cartastral</title>
    <style>
        body { 
            font-family: 'Georgia', serif; 
            margin: 40px; 
            line-height: 1.6; 
            color: #333;
        }
        .portada { 
            text-align: center; 
            margin-bottom: 30px; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .datos-natales { 
            background: #f8f9fa; 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .section { 
            margin: 30px 0; 
            padding: 15px;
        }
        .carta-img { 
            text-align: center; 
            margin: 30px 0; 
        }
        .carta-img img { 
            max-width: 100%; 
            border-radius: 8px; 
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .footer { 
            margin-top: 50px; 
            font-size: 0.9em; 
            color: #666; 
            text-align: center;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }
        .dato { 
            font-weight: bold; 
            color: #667eea; 
        }
        .interpretacion {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .planetas li {
            margin: 5px 0;
            padding: 5px;
            background: #f1f3f4;
            border-radius: 3px;
        }
        .resumen-sesion {
            background: #e8f4fd;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        h1, h2 { color: #667eea; }
        @media print {
            body { margin: 20px; }
            .portada { background: #667eea !important; }
        }
    </style>
</head>
<body>
    <div class="portada">
        <h1>🌟 CARTA ASTRAL PERSONALIZADA 🌟</h1>
        <h2>{{ nombre }}</h2>
        <p>AS Cartastral - Servicios Astrológicos Personalizados</p>
    </div>

    <div class="datos-natales">
        <h2>📊 Datos Natales</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de nacimiento:</span> {{ fecha_nacimiento }}</p>
        <p><span class="dato">Hora de nacimiento:</span> {{ hora_nacimiento }}</p>
        <p><span class="dato">Lugar de nacimiento:</span> {{ lugar_nacimiento }}</p>
    </div>

    {% if carta_natal_img %}
    <div class="carta-img">
        <h2>🌍 Tu Carta Natal</h2>
        <img src="file://{{ carta_natal_img }}" alt="Carta natal completa">
        <p><em>Tu mapa astrológico personal en el momento de tu nacimiento</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>✨ Introducción</h2>
        <div class="interpretacion">
            <p>Bienvenido/a a tu análisis astrológico personalizado. Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento y su influencia en tu personalidad, talentos y destino.</p>
        </div>
    </div>

    {% if planetas %}
    <div class="section">
        <h2>🪐 Posiciones Planetarias</h2>
        <ul class="planetas">
            {% for planeta, datos in planetas.items() %}
            <li><strong>{{ planeta|capitalize }}:</strong> {{ datos.degree|round(2) }}° en {{ datos.sign }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if progresiones_img %}
    <div class="carta-img">
        <h2>🔄 Progresiones Secundarias</h2>
        <img src="file://{{ progresiones_img }}" alt="Progresiones secundarias">
        <p><em>Tu evolución astrológica actual</em></p>
    </div>
    {% endif %}

    {% if transitos_img %}
    <div class="carta-img">
        <h2>🌊 Tránsitos Actuales</h2>
        <img src="file://{{ transitos_img }}" alt="Tránsitos actuales">
        <p><em>Influencias planetarias presentes</em></p>
    </div>
    {% endif %}

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 40 minutos</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="section">
        <h2>🌟 Conclusión</h2>
        <div class="interpretacion">
            <p>Tu carta astral es una guía para el autoconocimiento. Úsala para comprender tus patrones internos y tomar decisiones más conscientes en tu camino de crecimiento personal.</p>
        </div>
    </div>

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Carta Astral Completa con Progresiones y Tránsitos</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""
        
    elif tipo_servicio in ['revolucion_solar_ia', 'revolucion_solar']:
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Carta Astral + Revolución Solar - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('revolucion_solar_ia', '{{ nombre }}')}

    <div class="datos-natales">
        <h2>📊 Datos Natales</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de nacimiento:</span> {{ fecha_nacimiento }}</p>
        <p><span class="dato">Hora de nacimiento:</span> {{ hora_nacimiento }}</p>
        <p><span class="dato">Lugar de nacimiento:</span> {{ lugar_nacimiento }}, {{ pais_nacimiento or 'España' }}</p>
    </div>

    {% if carta_natal_img %}
    <div class="carta-img">
        <h2>🌍 Tu Carta Natal</h2>
        <img src="file://{{ carta_natal_img }}" alt="Carta natal">
        <p><em>Tu mapa astrológico base</em></p>
    </div>
    {% endif %}

    {% if revolucion_img %}
    <div class="carta-img">
        <h2>🎂 Tu Revolución Solar</h2>
        <img src="file://{{ revolucion_img }}" alt="Revolución solar">
        <p><em>Predicciones para tu nuevo año astrológico</em></p>
    </div>
    {% endif %}

    {% if revolucion_natal_img %}
    <div class="carta-img">
        <h2>🔄 Revolución Solar con Aspectos Natales</h2>
        <img src="file://{{ revolucion_natal_img }}" alt="Revolución con aspectos natales">
        <p><em>Cómo interactúa tu nuevo año con tu naturaleza básica</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>🔮 Predicciones para tu Nuevo Año</h2>
        <div class="interpretacion">
            <p>Tu revolución solar marca el inicio de un nuevo ciclo anual. Las configuraciones planetarias indican las principales tendencias y oportunidades para los próximos 12 meses.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 50 minutos</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Carta Astral + Revolución Solar</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>
        """
        
    elif tipo_servicio in ['sinastria_ia', 'sinastria']:
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Sinastría - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('sinastria_ia', '{{ nombre_persona1 }} & {{ nombre_persona2 }}')}

    <div class="datos-natales">
        <h2>📊 Datos de las Personas</h2>
        <div style="display: flex; gap: 40px;">
            <div style="flex: 1;">
                <h3>👤 Persona 1: {{ nombre_persona1 }}</h3>
                <p><span class="dato">Fecha:</span> {{ fecha_persona1 }}</p>
                <p><span class="dato">Hora:</span> {{ hora_persona1 }}</p>
                <p><span class="dato">Lugar:</span> {{ lugar_persona1 }}</p>
            </div>
            <div style="flex: 1;">
                <h3>👤 Persona 2: {{ nombre_persona2 }}</h3>
                <p><span class="dato">Fecha:</span> {{ fecha_persona2 }}</p>
                <p><span class="dato">Hora:</span> {{ hora_persona2 }}</p>
                <p><span class="dato">Lugar:</span> {{ lugar_persona2 }}</p>
            </div>
        </div>
        <p><span class="dato">Email de contacto:</span> {{ email }}</p>
    </div>

    {% if sinastria_img %}
    <div class="carta-img">
        <h2>💞 Carta de Sinastría</h2>
        <img src="file://{{ sinastria_img }}" alt="Carta de sinastría">
        <p><em>Aspectos planetarios entre ambas cartas natales</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>💝 Análisis de Compatibilidad</h2>
        <div class="interpretacion">
            <p>La sinastría analiza cómo interactúan vuestras energías astrológicas, revelando fortalezas, desafíos y el potencial de vuestra relación.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 30 minutos</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Sinastría Astrológica</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>
        """
        
    elif tipo_servicio in ['astrologia_horaria_ia', 'astrol_horaria']:
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Astrología Horaria - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('astrologia_horaria_ia', '{{ nombre }}')}

    <div class="datos-natales">
        <h2>❓ Datos de la Consulta</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de la pregunta:</span> {{ fecha_pregunta }}</p>
        <p><span class="dato">Hora de la pregunta:</span> {{ hora_pregunta }}</p>
        <p><span class="dato">Lugar de la pregunta:</span> {{ lugar_pregunta }}</p>
        <div class="interpretacion">
            <p><strong>Tu pregunta:</strong> {{ pregunta }}</p>
        </div>
    </div>

    {% if carta_horaria_img %}
    <div class="carta-img">
        <h2>🎯 Carta Horaria</h2>
        <img src="file://{{ carta_horaria_img }}" alt="Carta horaria">
        <p><em>Mapa astrológico del momento de tu pregunta</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>🔮 Respuesta Astrológica</h2>
        <div class="interpretacion">
            <p>La astrología horaria utiliza el momento exacto en que formulas tu pregunta para encontrar respuestas en las configuraciones planetarias.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 15 minutos</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Astrología Horaria</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>
        """
        
    elif tipo_servicio in ['lectura_manos_ia', 'lectura_manos']:
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Lectura de Manos - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('lectura_manos_ia', '{{ nombre }}')}

    <div class="datos-natales">
        <h2>✋ Datos de la Lectura</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Dominancia:</span> {{ dominancia or 'No especificada' }}</p>
    </div>

    {% if mano_derecha_img %}
    <div class="carta-img">
        <h2>🤚 Mano Derecha</h2>
        <img src="file://{{ mano_derecha_img }}" alt="Mano derecha">
        <p><em>Mano derecha - Representa tu futuro y lo que construyes</em></p>
    </div>
    {% endif %}

    {% if mano_izquierda_img %}
    <div class="carta-img">
        <h2>🤚 Mano Izquierda</h2>
        <img src="file://{{ mano_izquierda_img }}" alt="Mano izquierda">
        <p><em>Mano izquierda - Representa tu pasado y naturaleza innata</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>🔍 Análisis Quiromántico</h2>
        <div class="interpretacion">
            <p>La lectura de manos revela aspectos de tu personalidad, talentos naturales, y tendencias de vida a través de las líneas, montes y formas de tus palmas.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 30 minutos</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Lectura de Manos (Quiromancia)</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>
        """
        
    elif tipo_servicio in ['lectura_facial_ia', 'lectura_facial']:
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Lectura Facial - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('lectura_facial_ia', '{{ nombre }}')}

    <div class="datos-natales">
        <h2>👤 Datos de la Lectura</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
    </div>

    {% if cara_frente_img %}
    <div class="carta-img">
        <h2>👤 Vista Frontal</h2>
        <img src="file://{{ cara_frente_img }}" alt="Cara frontal">
        <p><em>Vista frontal - Análisis de proporciones y simetría</em></p>
    </div>
    {% endif %}

    {% if cara_izquierda_img %}
    <div class="carta-img">
        <h2>👤 Perfil Izquierdo (45°)</h2>
        <img src="file://{{ cara_izquierda_img }}" alt="Perfil izquierdo">
        <p><em>Perfil izquierdo - Análisis del lado emocional</em></p>
    </div>
    {% endif %}

    {% if cara_derecha_img %}
    <div class="carta-img">
        <h2>👤 Perfil Derecho (45°)</h2>
        <img src="file://{{ cara_derecha_img }}" alt="Perfil derecho">
        <p><em>Perfil derecho - Análisis del lado racional</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>🔍 Análisis Fisiognómico</h2>
        <div class="interpretacion">
            <p>La lectura facial estudia las características de tu rostro para revelar rasgos de personalidad, tendencias emocionales y patrones de comportamiento.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 15 minutos</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Lectura Facial (Fisiognomía)</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>
        """
        
    elif tipo_servicio in ['psico_coaching_ia', 'psico_coaching']:
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Psico-Coaching - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('psico_coaching_ia', '{{ nombre }}')}

    <div class="datos-natales">
        <h2>👤 Datos del Cliente</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de la sesión:</span> {{ fecha_generacion }}</p>
    </div>

    <div class="section">
        <h2>🎯 Objetivos de la Sesión</h2>
        <div class="interpretacion">
            <p>El psico-coaching combina técnicas psicológicas y de coaching para ayudarte a identificar patrones, superar obstáculos y desarrollar estrategias para tu crecimiento personal.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión de Coaching</h2>
        <p><strong>Duración:</strong> 45 minutos</p>
        <p><strong>Seguimiento disponible:</strong> 3 meses</p>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="section">
        <h2>📋 Plan de Acción</h2>
        <div class="interpretacion">
            <p>Basándome en nuestra conversación, te recomiendo seguir trabajando en las áreas identificadas y aplicar las estrategias discutidas durante nuestra sesión.</p>
        </div>
    </div>

    <div class="section">
        <h2>🔄 Próximos Pasos</h2>
        <div class="interpretacion">
            <p>Recuerda que tienes 3 meses de seguimiento disponible. Puedes contactar nuevamente para continuar trabajando en tu desarrollo personal y resolver cualquier duda que surja.</p>
        </div>
    </div>

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Sesión de Psico-Coaching</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios de Desarrollo Personal</p>
    </div>
</body>
</html>
        """
        
    elif tipo_servicio in ['grafologia_ia', 'grafologia']:
        return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Informe de Análisis Grafológico - AS Cartastral</title>
        {{ base_style }}
    </head>
    <body>
        {{{{{{obtener_portada_con_logo_corregida('grafologia_ia', '{{ nombre }}')}

        <div class="datos-natales">
            <h2>📝 Datos del Análisis</h2>
            <p><span class="dato">Nombre:</span> {{ nombre }}</p>
            <p><span class="dato">Email:</span> {{ email }}</p>
            <p><span class="dato">Muestra analizada:</span> Escritura manuscrita</p>
            <p><span class="dato">Confianza del análisis:</span> {{ confianza }}%</p>
        </div>

        {% if muestra_escritura_img %}
        <div class="carta-img">
            <h2>✍️ Tu Muestra de Escritura</h2>
            <img src="file://{{ muestra_escritura_img }}" alt="Muestra de escritura analizada">
            <p><em>Muestra de escritura analizada para el informe</em></p>
        </div>
        {% endif %}

        <div class="section">
            <h2>🔍 Análisis de Personalidad</h2>
            <div class="interpretacion">
                <p>Tu escritura revela aspectos fascinantes de tu personalidad. Cada trazo, inclinación y presión nos habla de características únicas de tu forma de ser.</p>
            </div>
        </div>

        {% if puntuaciones %}
        <div class="section">
            <h2>📊 Perfil Grafológico</h2>
            {% for dimension, datos in puntuaciones.items() %}
            <div class="datos-natales" style="margin: 15px 0;">
                <h3>{{ dimension|title }}: {{ (datos.score * 100)|round }}%</h3>
                <div style="background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden;">
                    <div style="background: #2c5aa0; height: 100%; width: {{ (datos.score * 100)|round }}%; border-radius: 10px;"></div>
                </div>
                <ul style="margin-top: 10px;">
                    {% for texto in datos.textos %}
                    <li>{{ texto }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="section">
            <h2>🎯 Características Principales</h2>
            <div class="interpretacion">
                <p><strong>Sociabilidad:</strong> Tu forma de relacionarte con otros se refleja en el espaciado y márgenes de tu escritura.</p>
                <p><strong>Autocontrol:</strong> La regularidad de tu trazo indica tu nivel de autodominio emocional.</p>
                <p><strong>Energía:</strong> La presión de tu escritura revela tu vitalidad y determinación.</p>
                <p><strong>Organización:</strong> La estructura de tu texto muestra tu capacidad organizativa.</p>
            </div>
        </div>

        {% if medidas_tecnicas %}
        <div class="section">
            <h2>📏 Medidas Técnicas</h2>
            <div class="datos-natales">
                <p><span class="dato">Inclinación:</span> {{ medidas_tecnicas.inclinacion_grados }}°</p>
                <p><span class="dato">Presión del trazo:</span> {{ medidas_tecnicas.contraste_med }} puntos</p>
                <p><span class="dato">Grosor promedio:</span> {{ medidas_tecnicas.grosor_trazo_px }} píxeles</p>
                <p><span class="dato">Regularidad:</span> {{ medidas_tecnicas.regularidad_tamano }} puntos</p>
            </div>
        </div>
        {% endif %}

        {% if resumen_sesion %}
        <div class="resumen-sesion">
            <h2>📞 Resumen de tu Sesión Telefónica</h2>
            <p><strong>Duración:</strong> 30 minutos</p>
            <div class="interpretacion">
                {{ resumen_sesion }}
            </div>
        </div>
        {% endif %}

        <div class="section">
            <h2>✨ Recomendaciones</h2>
            <div class="interpretacion">
                <p>Basándome en tu análisis grafológico, te recomiendo trabajar en potenciar tus fortalezas naturales y ser consciente de las áreas donde puedes desarrollarte más.</p>
                <p>Recuerda que la grafología es una herramienta de autoconocimiento que te ayuda a comprender mejor tu personalidad y patrones de comportamiento.</p>
            </div>
        </div>

        <div class="footer">
            <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
            <p><strong>Tipo de análisis:</strong> Análisis Grafológico Personalizado</p>
            <p><strong>Generado por:</strong> AS Cartastral - Servicios de Análisis de Personalidad</p>
        </div>
    </body>
    </html>
            """
    
    # Template por defecto si no se encuentra el tipo
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Personalizado - AS Cartastral</title>
    {{ base_style }}
</head>
<body>
    {{{{{{obtener_portada_con_logo_corregida('carta_astral_ia', '{{ nombre }}')}
    <div class="datos-natales">
        <h2>📊 Datos del Cliente</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
    </div>
    {% if resumen_sesion %}
    <div class="resumen-sesion">
        <h2>📞 Resumen de tu Sesión</h2>
        <div class="interpretacion">{{ resumen_sesion }}</div>
    </div>
    {% endif %}
    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Generado por:</strong> AS Cartastral</p>
    </div>
</body>
</html>
    """

def generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion=None):
    """Generar informe HTML personalizado según el tipo de servicio"""
    try:
        # Obtener fecha y hora de generación
        zona = pytz.timezone('Europe/Madrid')
        ahora = datetime.now(zona)
        fecha_generacion = ahora.strftime("%d/%m/%Y")
        hora_generacion = ahora.strftime("%H:%M:%S")
        
        # Preparar datos base
        datos_template = {
            'nombre': datos_cliente.get('nombre', 'Cliente'),
            'email': datos_cliente.get('email', ''),
            'fecha_generacion': fecha_generacion,
            'hora_generacion': hora_generacion,
            'resumen_sesion': resumen_sesion
        }
        
        # Datos específicos según tipo de servicio
        if tipo_servicio in ['carta_astral_ia', 'carta_natal']:
            datos_template.update({
                'fecha_nacimiento': datos_cliente.get('fecha_nacimiento', ''),
                'hora_nacimiento': datos_cliente.get('hora_nacimiento', ''),
                'lugar_nacimiento': datos_cliente.get('lugar_nacimiento', ''),
                'pais_nacimiento': datos_cliente.get('pais_nacimiento', 'España'),
                'planetas': datos_cliente.get('planetas', {}),
                'carta_natal_img': archivos_unicos.get('carta_natal_img'),
                'progresiones_img': archivos_unicos.get('progresiones_img'),
                'transitos_img': archivos_unicos.get('transitos_img')
            })
            
        elif tipo_servicio in ['revolucion_solar_ia', 'revolucion_solar']:
            datos_template.update({
                'fecha_nacimiento': datos_cliente.get('fecha_nacimiento', ''),
                'hora_nacimiento': datos_cliente.get('hora_nacimiento', ''),
                'lugar_nacimiento': datos_cliente.get('lugar_nacimiento', ''),
                'pais_nacimiento': datos_cliente.get('pais_nacimiento', 'España'),
                'carta_natal_img': archivos_unicos.get('carta_natal_img'),
                'revolucion_img': archivos_unicos.get('revolucion_img'),
                'revolucion_natal_img': archivos_unicos.get('revolucion_natal_img'),
                'progresiones_img': archivos_unicos.get('progresiones_img'),
                'transitos_img': archivos_unicos.get('transitos_img')
            })
            
        elif tipo_servicio in ['sinastria_ia', 'sinastria']:
            datos_template.update({
                'nombre_persona1': datos_cliente.get('nombre_persona1', 'Persona 1'),
                'nombre_persona2': datos_cliente.get('nombre_persona2', 'Persona 2'),
                'fecha_persona1': datos_cliente.get('fecha_persona1', ''),
                'hora_persona1': datos_cliente.get('hora_persona1', ''),
                'lugar_persona1': datos_cliente.get('lugar_persona1', ''),
                'fecha_persona2': datos_cliente.get('fecha_persona2', ''),
                'hora_persona2': datos_cliente.get('hora_persona2', ''),
                'lugar_persona2': datos_cliente.get('lugar_persona2', ''),
                'sinastria_img': archivos_unicos.get('sinastria_img')
            })
            
        elif tipo_servicio in ['astrologia_horaria_ia', 'astrol_horaria']:
            datos_template.update({
                'fecha_pregunta': datos_cliente.get('fecha_pregunta', ''),
                'hora_pregunta': datos_cliente.get('hora_pregunta', ''),
                'lugar_pregunta': datos_cliente.get('lugar_pregunta', ''),
                'pregunta': datos_cliente.get('pregunta', ''),
                'carta_horaria_img': archivos_unicos.get('carta_horaria_img')
            })
            
        elif tipo_servicio in ['lectura_manos_ia', 'lectura_manos']:
            datos_template.update({
                'dominancia': datos_cliente.get('dominancia', ''),
                'mano_derecha_img': archivos_unicos.get('mano_derecha_img'),
                'mano_izquierda_img': archivos_unicos.get('mano_izquierda_img')
            })
            
        elif tipo_servicio in ['lectura_facial_ia', 'lectura_facial']:
            datos_template.update({
                'cara_frente_img': archivos_unicos.get('cara_frente_img'),
                'cara_izquierda_img': archivos_unicos.get('cara_izquierda_img'),
                'cara_derecha_img': archivos_unicos.get('cara_derecha_img')
            })
            
        elif tipo_servicio in ['grafologia_ia', 'grafologia']:
            datos_template.update({
                'confianza': archivos_unicos.get('confianza', 50),
                'muestra_escritura_img': archivos_unicos.get('muestra_escritura_img'),
                'puntuaciones': archivos_unicos.get('puntuaciones', {}),
                'medidas_tecnicas': archivos_unicos.get('medidas_tecnicas', {})
            })
        
        # Obtener template HTML
        template_html = obtener_template_html(tipo_servicio)
        
        # ✅ CORREGIR RUTAS DE IMÁGENES
        datos_template = corregir_rutas_imagenes_cartas(datos_template)
        
        # Renderizar template
        template = Template(template_html)
        html_content = template.render(**datos_template)
        
        # Generar nombre de archivo único
        nombre_base = generar_nombre_archivo_unico(tipo_servicio, datos_cliente.get('codigo_servicio', ''))
        archivo_html = f"templates/informe_{nombre_base}.html"
        
        # Crear directorio si no existe
        os.makedirs('templates', exist_ok=True)
        
        # Guardar archivo HTML
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Informe HTML generado: {archivo_html}")
        return archivo_html
        
    except Exception as e:
        print(f"❌ Error generando informe HTML: {e}")
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