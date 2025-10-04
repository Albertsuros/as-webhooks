"""
Sistema de generación de informes personalizados para AS Cartastral
Genera informes HTML y PDF para los 7 tipos de servicios IA
"""

import os
import pytz
from datetime import datetime
# from weasyprint import HTML # Comentado - importar dentro de funciones
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from jinja2 import Template

def obtener_portada_con_logo(tipo_servicio, nombre_cliente=''):
    """Generar portada con logo AS Cartastral + imagen del servicio"""
    
    # MAPEO CORREGIDO CON RUTAS Y EXTENSIONES REALES
    imagenes_servicios = {
        'carta_astral_ia': 'astrologia-3.JPG',
        'carta_natal': 'astrologia-3.JPG',
        'revolucion_solar_ia': 'Tarot y astrologia-5.JPG', 
        'revolucion_solar': 'Tarot y astrologia-5.JPG',
        'sinastria_ia': 'Sinastria.JPG',
        'sinastria': 'Sinastria.JPG',
        'astrologia_horaria_ia': 'astrologia-1.JPG',
        'astrol_horaria': 'astrologia-1.JPG',
        'lectura_manos_ia': 'Lectura-de-manos-p.jpg',
        'lectura_manos': 'Lectura-de-manos-p.jpg',
        'lectura_facial_ia': 'lectura facial.JPG',
        'lectura_facial': 'lectura facial.JPG',
        'psico_coaching_ia': 'coaching-4.JPG',
        'psico_coaching': 'coaching-4.JPG',
        'grafologia_ia': 'grafologia_2.jpeg',
        'grafologia': 'grafologia_2.jpeg'
    }
    
    # Títulos completos
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
        'psico_coaching': '🧠 SESIÓN DE PSICO-COACHING 🧠',
        'grafologia_ia': '✍️ ANÁLISIS GRAFOLÓGICO PERSONALIZADO ✍️',
        'grafologia': '✍️ ANÁLISIS GRAFOLÓGICO PERSONALIZADO ✍️'
    }
    
    imagen_servicio = imagenes_servicios.get(tipo_servicio, 'logo.JPG')
    titulo_servicio = titulos_servicios.get(tipo_servicio, '🌟 INFORME PERSONALIZADO 🌟')
    fecha_actual = datetime.now(pytz.timezone('Europe/Madrid')).strftime('%d de %B de %Y')
    
    return f"""
    <div class="portada">
        <div class="logo-header">
            <img src="file:///home/runner/workspace/flask-server/static/logo.JPG" ...>
            <span class="nombre-empresa">AS Cartastral</span>
        </div>
        <h1 class="titulo-principal">{titulo_servicio}</h1>
        <div class="imagen-servicio">
            <img src="file:///home/runner/workspace/flask-server/static/{imagen_servicio}" ...>
        </div>
        <h2 class="nombre-cliente">{{{{ nombre }}}}</h2>
        <h3 class="subtitulo">Tu análisis personalizado</h3>
        <div class="fecha-portada">
            <p>Generado el {fecha_actual}</p>
        </div>
    </div>
    """

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

def obtener_template_html(tipo_servicio):
    """Obtener template HTML según tipo de servicio"""
    
    import os
    dir_base = os.path.dirname(os.path.abspath(__file__))
    
    # Mapeo de imágenes
    imagenes_servicios = {
        'carta_astral_ia': 'astrologia-3.JPG',
        'carta_natal': 'astrologia-3.JPG',
        'revolucion_solar_ia': 'Tarot y astrologia-5.JPG', 
        'revolucion_solar': 'Tarot y astrologia-5.JPG',
        'sinastria_ia': 'Sinastria.JPG',
        'sinastria': 'Sinastria.JPG',
        'astrologia_horaria_ia': 'astrologia-1.JPG',
        'astrol_horaria': 'astrologia-1.JPG',
        'lectura_manos_ia': 'Lectura-de-manos-p.jpg',
        'lectura_manos': 'Lectura-de-manos-p.jpg',
        'lectura_facial_ia': 'lectura facial.JPG',
        'lectura_facial': 'lectura facial.JPG',
        'psico_coaching_ia': 'coaching-4.JPG',
        'psico_coaching': 'coaching-4.JPG',
        'grafologia_ia': 'grafologia_2.jpeg',
        'grafologia': 'grafologia_2.jpeg'
    }
    
    imagen_servicio = imagenes_servicios.get(tipo_servicio, 'logo.JPG')
    
    # CSS común para todos
    estilos_comunes = """
    <style>
        body {
            font-family: 'Georgia', serif;
            margin: 20px;
            line-height: 1.6;
            color: #333;
        }
        @page {
            margin: 1.5cm 1.5cm;
        }
        .portada {
            text-align: center;
            page-break-after: always;
            padding: 40px 0;
        }
        .logo-portada {
            width: 120px;
            height: auto;
            margin-bottom: 20px;
        }
        .imagen-especialidad {
            width: 300px;
            height: 300px;
            object-fit: cover;
            border-radius: 15px;
            margin: 30px auto;
            display: block;
            border: 3px solid #2c5aa0;
        }
        .portada h1 {
            font-size: 32px;
            color: #2c5aa0;
            margin: 20px 0;
        }
        .portada h2 {
            font-size: 24px;
            color: #666;
            font-weight: normal;
        }
        .seccion {
            margin: 40px 0;
            page-break-inside: avoid;
        }
        h2 {
            font-size: 22px;
            color: #2c5aa0;
            border-bottom: 2px solid #2c5aa0;
            padding-bottom: 8px;
            margin-top: 40px;
        }
        h3 {
            font-size: 18px;
            color: #666;
            margin-top: 20px;
        }
        .datos-natales {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .dato {
            font-weight: bold;
            color: #2c5aa0;
        }
        .carta-img {
            text-align: center;
            margin: 30px 0;
            page-break-inside: avoid;
        }
        .carta-img img {
            width: 100%;
            max-width: 600px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        .carta-img p {
            font-style: italic;
            color: #666;
            margin-top: 10px;
        }
        ul.planetas {
            column-count: 2;
            column-gap: 40px;
            list-style-type: none;
            padding: 0;
        }
        ul.planetas li {
            padding: 8px 0;
            border-bottom: 1px dotted #ddd;
        }
        .resumen-sesion {
            background: #e8f5e8;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #4caf50;
            margin: 30px 0;
        }
        .interpretacion {
            background: #fff8e1;
            padding: 15px;
            border-left: 4px solid #ff9800;
            margin: 15px 0;
            border-radius: 4px;
        }
        .footer {
            text-align: center;
            margin-top: 60px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 12px;
            color: #666;
        }
        @media print {
            .portada { page-break-after: always; }
            .seccion { page-break-inside: avoid; }
        }
    </style>
    """
    
    # CARTA ASTRAL
    if tipo_servicio in ['carta_astral_ia', 'carta_natal']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Carta Astral - AS Cartastral</title>
    {estilos_comunes}
    <style>

    </style>
    <style>
    ul.aspectos {{
        column-count: 2;
        column-gap: 30px;
        list-style-type: disc;
    }}
    </style>
    <style>
    ul.aspectos {{
        column-count: 2;
        column-gap: 30px;
    }}
    </style>
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>🌟 CARTA ASTRAL PERSONALIZADA 🌟</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Carta Astral" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Tu análisis personalizado</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>📊 Datos Natales</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    <p><span class="dato">Fecha de nacimiento:</span> {{{{ fecha_nacimiento }}}}</p>
    <p><span class="dato">Hora de nacimiento:</span> {{{{ hora_nacimiento }}}}</p>
    <p><span class="dato">Lugar de nacimiento:</span> {{{{ lugar_nacimiento }}}}, {{{{ pais_nacimiento or 'España' }}}}</p>
</div>

{{% if carta_natal_img %}}
<div class="seccion">
    <h2>🌍 Tu Carta Natal</h2>
    <div class="carta-img">
        <img src="file://{{{{ carta_natal_img }}}}" alt="Carta natal completa">
        <p>Tu mapa astrológico personal en el momento de tu nacimiento</p>
    </div>
</div>
{{% endif %}}

{{% if planetas %}}
<div class="seccion">
    <h2>🪐 Posiciones Planetarias Natales</h2>
    <ul class="planetas">
        {{% for planeta, datos in planetas.items() %}}
        <li><strong>{{{{ planeta }}}}:</strong> {{{{ datos.degree }}}} en {{{{ datos.sign }}}}{{% if datos.retrogrado %}} ℞{{% endif %}}</li>
        {{% endfor %}}
    </ul>
</div>
{{% endif %}}

{{% if retrogrados_natales %}}
<div class="seccion">
    <h3 style="color: #666; font-size: 18px;">↩️ Planetas Retrógrados Natales</h3>
    <p>{{{{ ', '.join(retrogrados_natales) }}}}</p>
</div>
{{% endif %}}

<div class="seccion">
    <h3 style="color: #666; font-size: 18px;">🔥💨💧🌍 Análisis de Elementos</h3>
    <p><strong>Fuego:</strong> 2 planetas | <strong>Tierra:</strong> 1 planeta | <strong>Aire:</strong> 3 planetas | <strong>Agua:</strong> 4 planetas</p>
</div>

{{% if aspectos_natales %}}
<div class="seccion" style="page-break-inside: avoid;">
    <h2>⚡ Aspectos Natales ({{{{ aspectos_natales|length }}}})</h2>
    <ul class="aspectos" style="margin: 5px 0; padding-left: 20px; line-height: 1.4;">
        {{% for aspecto in aspectos_natales %}}
        <li style="margin: 2px 0;">{{{{ aspecto['planeta1'] }}}} {{{{ aspecto['aspecto']|upper }}}} {{{{ aspecto['planeta2'] }}}} - {{{{ "%.2f"|format(aspecto['orbe']) }}}}°</li>
        {{% endfor %}}
    </ul>
</div>
{{% endif %}}

{{% if progresiones_img %}}
<div class="seccion" style="page-break-inside: auto;">
    <h2>🔄 Progresiones Secundarias</h2>
    <div class="carta-img">
        <img src="file://{{{{ progresiones_img }}}}" alt="Progresiones secundarias">
        <p>Tu evolución astrológica actual</p>
    </div>
    
    {{% if planetas_progresados %}}
    <h3 style="color: #666; font-size: 18px; margin-top: 20px;">🪐 Posiciones Progresadas</h3>
    <ul class="planetas" style="margin-top: 10px;">
        {{% for planeta, datos in planetas_progresados.items() %}}
        <li><strong>{{{{ planeta }}}} (P):</strong> {{{{ datos.degree }}}} en {{{{ datos.sign }}}}{{% if datos.retrogrado %}} ℞{{% endif %}}</li>
        {{% endfor %}}
    </ul>
    {{% if retrogrados_progresados %}}
    <p style="margin-top: 10px;"><strong>↩️ Retrógrados:</strong> {{{{ ', '.join(retrogrados_progresados) }}}}</p>
    {{% endif %}}
    {{% endif %}}
</div>
{{% endif %}}

{{% if aspectos_progresados %}}
<div class="seccion" style="page-break-inside: avoid;">
    <h2>⚡ Aspectos Progresión-Natal ({{{{ aspectos_progresados|length }}}})</h2>
    <ul class="aspectos" style="margin: 5px 0; padding-left: 20px; line-height: 1.4;">
        {{% for aspecto in aspectos_progresados %}}
        <li style="margin: 2px 0;">{{{{ aspecto['planeta_progresion'] }}}} (P) {{{{ aspecto['tipo']|upper }}}} {{{{ aspecto['planeta_natal'] }}}} (N) - {{{{ "%.2f"|format(aspecto['orbe']) }}}}°</li>
        {{% endfor %}}
    </ul>
</div>
{{% endif %}}

{{% if transitos_img %}}
<div class="seccion" style="page-break-inside: auto;">
    <h2>🌊 Tránsitos Actuales</h2>
    <div class="carta-img">
        <img src="file://{{{{ transitos_img }}}}" alt="Tránsitos actuales">
        <p>Influencias planetarias presentes</p>
    </div>
    
    {{% if planetas_transitos %}}
    <h3 style="color: #666; font-size: 18px; margin-top: 20px;">🪐 Posiciones en Tránsito</h3>
    <ul class="planetas" style="margin-top: 10px;">
        {{% for planeta, datos in planetas_transitos.items() %}}
        <li><strong>{{{{ planeta }}}} (T):</strong> {{{{ datos.degree }}}} en {{{{ datos.sign }}}}{{% if datos.retrogrado %}} ℞{{% endif %}}</li>
        {{% endfor %}}
    </ul>
    {{% if retrogrados_transitos %}}
    <p style="margin-top: 10px;"><strong>↩️ Retrógrados:</strong> {{{{ ', '.join(retrogrados_transitos) }}}}</p>
    {{% endif %}}
    {{% endif %}}
</div>
{{% endif %}}

{{% if aspectos_transitos %}}
<div class="seccion" style="page-break-inside: auto;">
    <h2>⚡ Aspectos Tránsito-Natal ({{{{ aspectos_transitos|length }}}})</h2>
    <ul class="aspectos" style="margin: 5px 0; padding-left: 20px; line-height: 1.4;">
        {{% for aspecto in aspectos_transitos %}}
        <li style="margin: 2px 0;">{{{{ aspecto['planeta_transito'] }}}} (T) {{{{ aspecto['tipo']|upper }}}} {{{{ aspecto['planeta_natal'] }}}} (N) - {{{{ "%.2f"|format(aspecto['orbe']) }}}}°</li>
        {{% endfor %}}
    </ul>
</div>
{{% endif %}}

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 40 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>🌟 Conclusión</h2>
    <p>Tu carta astral es una guía para el autoconocimiento. Úsala para comprender tus patrones internos y tomar decisiones más conscientes en tu camino de crecimiento personal.</p>
</div>

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Carta Astral Completa con Progresiones y Tránsitos</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
</div>

</body>
</html>
        """
    
    # REVOLUCIÓN SOLAR
    elif tipo_servicio in ['revolucion_solar_ia', 'revolucion_solar']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Revolución Solar - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>🌟 CARTA ASTRAL + REVOLUCIÓN SOLAR 🌟</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Revolución Solar" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Tu análisis personalizado</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>📊 Datos Natales</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    <p><span class="dato">Fecha de nacimiento:</span> {{{{ fecha_nacimiento }}}}</p>
    <p><span class="dato">Hora de nacimiento:</span> {{{{ hora_nacimiento }}}}</p>
    <p><span class="dato">Lugar de nacimiento:</span> {{{{ lugar_nacimiento }}}}, {{{{ pais_nacimiento or 'España' }}}}</p>
</div>

<div class="seccion">
    <h2>✨ Introducción</h2>
    <p>Bienvenido/a a tu análisis astrológico personalizado. Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento y su influencia en tu personalidad, talentos y destino.</p>
</div>

{{% if carta_natal_img %}}
<div class="seccion">
    <h2>🌍 Tu Carta Natal</h2>
    <div class="carta-img">
        <img src="file://{{{{ carta_natal_img }}}}" alt="Carta natal">
        <p>Tu mapa astrológico base</p>
    </div>
</div>
{{% endif %}}

{{% if revolucion_img %}}
<div class="seccion">
    <h2>🎂 Tu Revolución Solar</h2>
    <div class="carta-img">
        <img src="file://{{{{ revolucion_img }}}}" alt="Revolución solar">
        <p>Predicciones para tu nuevo año astrológico</p>
    </div>
</div>
{{% endif %}}

{{% if revolucion_natal_img %}}
<div class="seccion">
    <h2>🔄 Revolución Solar con Aspectos Natales</h2>
    <div class="carta-img">
        <img src="file://{{{{ revolucion_natal_img }}}}" alt="Revolución con aspectos natales">
        <p>Cómo interactúa tu nuevo año con tu naturaleza básica</p>
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>🔮 Predicciones para tu Nuevo Año</h2>
    <div class="interpretacion">
        <p>Tu revolución solar marca el inicio de un nuevo ciclo anual. Las configuraciones planetarias indican las principales tendencias y oportunidades para los próximos 12 meses.</p>
    </div>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 50 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Carta Astral + Revolución Solar</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
</div>

</body>
</html>
        """
    
    # SINASTRÍA
    elif tipo_servicio in ['sinastria_ia', 'sinastria']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Sinastría - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>💕 SINASTRÍA ASTROLÓGICA 💕</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Sinastría" class="imagen-especialidad">
    <h2>{{{{ nombre_persona1 }}}} & {{{{ nombre_persona2 }}}}</h2>
    <p style="color: #888;">Análisis de compatibilidad</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>📊 Datos de las Personas</h2>
    <div style="display: flex; gap: 40px;">
        <div style="flex: 1;">
            <h3>👤 Persona 1: {{{{ nombre_persona1 }}}}</h3>
            <p><span class="dato">Fecha:</span> {{{{ fecha_persona1 }}}}</p>
            <p><span class="dato">Hora:</span> {{{{ hora_persona1 }}}}</p>
            <p><span class="dato">Lugar:</span> {{{{ lugar_persona1 }}}}</p>
        </div>
        <div style="flex: 1;">
            <h3>👤 Persona 2: {{{{ nombre_persona2 }}}}</h3>
            <p><span class="dato">Fecha:</span> {{{{ fecha_persona2 }}}}</p>
            <p><span class="dato">Hora:</span> {{{{ hora_persona2 }}}}</p>
            <p><span class="dato">Lugar:</span> {{{{ lugar_persona2 }}}}</p>
        </div>
    </div>
    <p><span class="dato">Email de contacto:</span> {{{{ email }}}}</p>
</div>

{{% if sinastria_img %}}
<div class="seccion">
    <h2>💞 Carta de Sinastría</h2>
    <div class="carta-img">
        <img src="file://{{{{ sinastria_img }}}}" alt="Carta de sinastría">
        <p>Aspectos planetarios entre ambas cartas natales</p>
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>💝 Análisis de Compatibilidad</h2>
    <div class="interpretacion">
        <p>La sinastría analiza cómo interactúan vuestras energías astrológicas, revelando fortalezas, desafíos y el potencial de vuestra relación.</p>
    </div>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 30 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Sinastría Astrológica</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
</div>

</body>
</html>
        """
    
    # ASTROLOGÍA HORARIA
    elif tipo_servicio in ['astrologia_horaria_ia', 'astrol_horaria']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Astrología Horaria - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>⏰ ASTROLOGÍA HORARIA ⏰</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Horaria" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Respuestas a tu pregunta</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>❓ Datos de la Consulta</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    <p><span class="dato">Fecha de la pregunta:</span> {{{{ fecha_pregunta }}}}</p>
    <p><span class="dato">Hora de la pregunta:</span> {{{{ hora_pregunta }}}}</p>
    <p><span class="dato">Lugar de la pregunta:</span> {{{{ lugar_pregunta }}}}</p>
    <div class="interpretacion">
        <p><strong>Tu pregunta:</strong> {{{{ pregunta }}}}</p>
    </div>
</div>

{{% if carta_horaria_img %}}
<div class="seccion">
    <h2>🎯 Carta Horaria</h2>
    <div class="carta-img">
        <img src="file://{{{{ carta_horaria_img }}}}" alt="Carta horaria">
        <p>Mapa astrológico del momento de tu pregunta</p>
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>🔮 Respuesta Astrológica</h2>
    <div class="interpretacion">
        <p>La astrología horaria utiliza el momento exacto en que formulas tu pregunta para encontrar respuestas en las configuraciones planetarias.</p>
    </div>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 15 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Astrología Horaria</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
</div>

</body>
</html>
        """
    
    # LECTURA DE MANOS
    elif tipo_servicio in ['lectura_manos_ia', 'lectura_manos']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Lectura de Manos - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>👋 LECTURA DE MANOS PERSONALIZADA 👋</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Manos" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Análisis quiromántico</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>✋ Datos de la Lectura</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    <p><span class="dato">Dominancia:</span> {{{{ dominancia or 'No especificada' }}}}</p>
</div>

{{% if mano_derecha_img %}}
<div class="seccion">
    <h2>🤚 Mano Derecha</h2>
    <div class="carta-img">
        <img src="file://{{{{ mano_derecha_img }}}}" alt="Mano derecha">
        <p>Mano derecha - Representa tu futuro y lo que construyes</p>
    </div>
</div>
{{% endif %}}

{{% if mano_izquierda_img %}}
<div class="seccion">
    <h2>🤚 Mano Izquierda</h2>
    <div class="carta-img">
        <img src="file://{{{{ mano_izquierda_img }}}}" alt="Mano izquierda">
        <p>Mano izquierda - Representa tu pasado y naturaleza innata</p>
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>🔍 Análisis Quiromántico</h2>
    <div class="interpretacion">
        <p>La lectura de manos revela aspectos de tu personalidad, talentos naturales, y tendencias de vida a través de las líneas, montes y formas de tus palmas.</p>
    </div>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 30 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Lectura de Manos (Quiromancia)</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
</div>

</body>
</html>
        """
    
    # LECTURA FACIAL
    elif tipo_servicio in ['lectura_facial_ia', 'lectura_facial']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Lectura Facial - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>😊 LECTURA FACIAL PERSONALIZADA 😊</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Facial" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Análisis fisiognómico</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>👤 Datos de la Lectura</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
</div>

{{% if cara_frente_img %}}
<div class="seccion">
    <h2>👤 Vista Frontal</h2>
    <div class="carta-img">
        <img src="file://{{{{ cara_frente_img }}}}" alt="Cara frontal">
        <p>Vista frontal - Análisis de proporciones y simetría</p>
    </div>
</div>
{{% endif %}}

{{% if cara_izquierda_img %}}
<div class="seccion">
    <h2>👤 Perfil Izquierdo (45°)</h2>
    <div class="carta-img">
        <img src="file://{{{{ cara_izquierda_img }}}}" alt="Perfil izquierdo">
        <p>Perfil izquierdo - Análisis del lado emocional</p>
    </div>
</div>
{{% endif %}}

{{% if cara_derecha_img %}}
<div class="seccion">
    <h2>👤 Perfil Derecho (45°)</h2>
    <div class="carta-img">
        <img src="file://{{{{ cara_derecha_img }}}}" alt="Perfil derecho">
        <p>Perfil derecho - Análisis del lado racional</p>
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>🔍 Análisis Fisiognómico</h2>
    <div class="interpretacion">
        <p>La lectura facial estudia las características de tu rostro para revelar rasgos de personalidad, tendencias emocionales y patrones de comportamiento.</p>
    </div>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 15 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Lectura Facial (Fisiognomía)</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
</div>

</body>
</html>
        """
    
    # PSICO-COACHING
    elif tipo_servicio in ['psico_coaching_ia', 'psico_coaching']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Psico-Coaching - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>🧠 SESIÓN DE PSICO-COACHING 🧠</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Coaching" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Desarrollo personal</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>👤 Datos del Cliente</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    <p><span class="dato">Fecha de la sesión:</span> {{{{ fecha_generacion }}}}</p>
</div>

<div class="seccion">
    <h2>🎯 Objetivos de la Sesión</h2>
    <div class="interpretacion">
        <p>El psico-coaching combina técnicas psicológicas y de coaching para ayudarte a identificar patrones, superar obstáculos y desarrollar estrategias para tu crecimiento personal.</p>
    </div>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión de Coaching</h2>
    <p><strong>Duración:</strong> 45 minutos</p>
    <p><strong>Seguimiento disponible:</strong> 3 meses</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>📋 Plan de Acción</h2>
    <div class="interpretacion">
        <p>Basándome en nuestra conversación, te recomiendo seguir trabajando en las áreas identificadas y aplicar las estrategias discutidas durante nuestra sesión.</p>
    </div>
</div>

<div class="seccion">
    <h2>🔄 Próximos Pasos</h2>
    <div class="interpretacion">
        <p>Recuerda que tienes 3 meses de seguimiento disponible. Puedes contactar nuevamente para continuar trabajando en tu desarrollo personal y resolver cualquier duda que surja.</p>
    </div>
</div>

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Sesión de Psico-Coaching</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios de Desarrollo Personal</p>
</div>

</body>
</html>
        """
    
    # GRAFOLOGÍA
    elif tipo_servicio in ['grafologia_ia', 'grafologia']:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Análisis Grafológico - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>✍️ ANÁLISIS GRAFOLÓGICO PERSONALIZADO ✍️</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Grafología" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Análisis de personalidad</p>
    <p style="color: #888; font-size: 14px;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>📝 Datos del Análisis</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
    <p><span class="dato">Muestra analizada:</span> Escritura manuscrita</p>
    <p><span class="dato">Confianza del análisis:</span> {{{{ confianza }}}}%</p>
</div>

{{% if muestra_escritura_img %}}
<div class="seccion">
    <h2>✍️ Tu Muestra de Escritura</h2>
    <div class="carta-img">
        <img src="file://{{{{ muestra_escritura_img }}}}" alt="Muestra de escritura">
        <p>Muestra de escritura analizada para el informe</p>
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>🔍 Análisis de Personalidad</h2>
    <div class="interpretacion">
        <p>Tu escritura revela aspectos fascinantes de tu personalidad. Cada trazo, inclinación y presión nos habla de características únicas de tu forma de ser.</p>
    </div>
</div>

{{% if puntuaciones %}}
<div class="seccion">
    <h2>📊 Perfil Grafológico</h2>
    {{% for dimension, datos in puntuaciones.items() %}}
    <div class="datos-natales" style="margin: 15px 0;">
        <h3>{{{{ dimension|title }}}}: {{{{ (datos.score * 100)|round }}}}%</h3>
        <div style="background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden;">
            <div style="background: #2c5aa0; height: 100%; width: {{{{ (datos.score * 100)|round }}}}%; border-radius: 10px;"></div>
        </div>
        <ul style="margin-top: 10px;">
            {{% for texto in datos.textos %}}
            <li>{{{{ texto }}}}</li>
            {{% endfor %}}
        </ul>
    </div>
    {{% endfor %}}
</div>
{{% endif %}}

<div class="seccion">
    <h2>🎯 Características Principales</h2>
    <div class="interpretacion">
        <p><strong>Sociabilidad:</strong> Tu forma de relacionarte con otros se refleja en el espaciado y márgenes de tu escritura.</p>
        <p><strong>Autocontrol:</strong> La regularidad de tu trazo indica tu nivel de autodominio emocional.</p>
        <p><strong>Energía:</strong> La presión de tu escritura revela tu vitalidad y determinación.</p>
        <p><strong>Organización:</strong> La estructura de tu texto muestra tu capacidad organizativa.</p>
    </div>
</div>

{{% if medidas_tecnicas %}}
<div class="seccion">
    <h2>📏 Medidas Técnicas</h2>
    <div class="datos-natales">
        <p><span class="dato">Inclinación:</span> {{{{ medidas_tecnicas.inclinacion_grados }}}}°</p>
        <p><span class="dato">Presión del trazo:</span> {{{{ medidas_tecnicas.contraste_med }}}} puntos</p>
        <p><span class="dato">Grosor promedio:</span> {{{{ medidas_tecnicas.grosor_trazo_px }}}} píxeles</p>
        <p><span class="dato">Regularidad:</span> {{{{ medidas_tecnicas.regularidad_tamano }}}} puntos</p>
    </div>
</div>
{{% endif %}}

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Resumen de tu Sesión Telefónica</h2>
    <p><strong>Duración:</strong> 30 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="seccion">
    <h2>✨ Recomendaciones</h2>
    <div class="interpretacion">
        <p>Basándome en tu análisis grafológico, te recomiendo trabajar en potenciar tus fortalezas naturales y ser consciente de las áreas donde puedes desarrollarte más.</p>
        <p>Recuerda que la grafología es una herramienta de autoconocimiento que te ayuda a comprender mejor tu personalidad y patrones de comportamiento.</p>
    </div>
</div>

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Análisis Grafológico Personalizado</p>
    <p><strong>Generado por:</strong> AS Cartastral - Servicios de Análisis de Personalidad</p>
</div>

</body>
</html>
        """
    
    # EXTENSIONES MEDIO TIEMPO (sin portada)
    elif tipo_servicio.endswith('_half'):
        # Determinar el tipo base
        tipo_base = tipo_servicio.replace('_half', '')
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Extensión de Sesión - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="seccion">
    <h2>🔄 Extensión de Sesión</h2>
    <p><strong>Continuación de tu análisis</strong></p>
    <p style="color: #888;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>📞 Contenido de la Extensión</h2>
    <p><strong>Duración adicional:</strong> 20 minutos</p>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Tipo de análisis:</strong> Extensión de sesión</p>
    <p><strong>Generado por:</strong> AS Cartastral</p>
</div>

</body>
</html>
        """
    
    # Template por defecto
    else:
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Personalizado - AS Cartastral</title>
    {estilos_comunes}
</head>
<body>

<div class="portada">
    <img src="file://{dir_base}/static/logo.JPG" alt="AS Cartastral" class="logo-portada">
    <h1>INFORME PERSONALIZADO</h1>
    <img src="file://{dir_base}/static/{imagen_servicio}" alt="Servicio" class="imagen-especialidad">
    <h2>{{{{ nombre }}}}</h2>
    <p style="color: #888;">Generado el {{{{ fecha_generacion }}}}</p>
</div>

<div class="datos-natales">
    <h2>Datos del Cliente</h2>
    <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
    <p><span class="dato">Email:</span> {{{{ email }}}}</p>
</div>

{{% if resumen_sesion %}}
<div class="resumen-sesion">
    <h2>Resumen de tu Sesión</h2>
    <div style="margin-top: 15px;">
        {{{{ resumen_sesion }}}}
    </div>
</div>
{{% endif %}}

<div class="footer">
    <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
    <p><strong>Generado por:</strong> AS Cartastral</p>
</div>

</body>
</html>
        """

def generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion=None, datos_interpretacion=None):
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
            # Función para convertir grados decimales a sexagesimales
            def decimal_a_sexagesimal(grado_decimal):
                grados = int(grado_decimal)
                minutos = int((grado_decimal - grados) * 60)
                return f"{grados}°{minutos:02d}'"
            
            # Función para calcular signo
            def grado_a_signo(grado_abs):
                signos = ['Aries', 'Tauro', 'Géminis', 'Cáncer', 'Leo', 'Virgo', 
                         'Libra', 'Escorpio', 'Sagitario', 'Capricornio', 'Acuario', 'Piscis']
                grado_norm = grado_abs % 360
                idx = int(grado_norm / 30)
                grado_en_signo = grado_norm % 30
                return signos[idx], grado_en_signo
            
            # Inicializar variables
            planetas_dict = {}
            aspectos_natales = []
            retrogrados_natales = []
            aspectos_progresados = []
            planetas_progresados = {}
            retrogrados_progresados = []
            aspectos_transitos = []
            planetas_transitos = {}
            retrogrados_transitos = []
            
            # DATOS NATALES
            if datos_interpretacion and 'carta_natal' in datos_interpretacion:
                posiciones = datos_interpretacion['carta_natal'].get('posiciones', {})
                aspectos_natales = datos_interpretacion['carta_natal'].get('aspectos', [])
                
                for planeta, datos_planeta in posiciones.items():
                    if 'grado' in datos_planeta:
                        grado_abs = datos_planeta['grado']
                        signo, grado_en_signo = grado_a_signo(grado_abs)
                        planetas_dict[planeta] = {
                            'degree': decimal_a_sexagesimal(grado_en_signo),
                            'sign': signo,
                            'retrogrado': datos_planeta.get('retrogrado', False)
                        }
                        if datos_planeta.get('retrogrado'):
                            retrogrados_natales.append(planeta)
            
            # PROGRESIONES
            planetas_progresados = {}
            retrogrados_progresados = []
            if datos_interpretacion and 'progresiones' in datos_interpretacion:
                aspectos_progresados = datos_interpretacion['progresiones'].get('aspectos', [])
                pos_prog = datos_interpretacion['progresiones'].get('posiciones_progresadas', {})
                
                for planeta, datos_planeta in pos_prog.items():
                    if 'grado' in datos_planeta:
                        grado_abs = datos_planeta['grado']
                        signo, grado_en_signo = grado_a_signo(grado_abs)
                        planetas_progresados[planeta] = {
                            'degree': decimal_a_sexagesimal(grado_en_signo),
                            'sign': signo,
                            'retrogrado': datos_planeta.get('retrogrado', False)
                        }
                        if datos_planeta.get('retrogrado'):
                            retrogrados_progresados.append(planeta)
                            
            datos_template.update({
                'fecha_nacimiento': datos_cliente.get('fecha_nacimiento', ''),
                'hora_nacimiento': datos_cliente.get('hora_nacimiento', ''),
                'lugar_nacimiento': datos_cliente.get('lugar_nacimiento', ''),
                'pais_nacimiento': datos_cliente.get('pais_nacimiento', 'España'),
                'planetas': planetas_dict,
                'aspectos_natales': aspectos_natales,
                'retrogrados_natales': retrogrados_natales,
                'aspectos_progresados': aspectos_progresados,
                'planetas_progresados': planetas_progresados,  # AÑADIR ESTA LÍNEA
                'retrogrados_progresados': retrogrados_progresados,  # AÑADIR ESTA LÍNEA
                'aspectos_transitos': aspectos_transitos,
                'planetas_transitos': planetas_transitos,  # AÑADIR ESTA LÍNEA
                'retrogrados_transitos': retrogrados_transitos,  # AÑADIR ESTA LÍNEA
                'carta_natal_img': os.path.abspath(archivos_unicos.get('carta_natal_img', '')) if archivos_unicos.get('carta_natal_img') else None,
                'progresiones_img': os.path.abspath(archivos_unicos.get('progresiones_img', '')) if archivos_unicos.get('progresiones_img') else None,
                'transitos_img': os.path.abspath(archivos_unicos.get('transitos_img', '')) if archivos_unicos.get('transitos_img') else None
            })
            
            # TRÁNSITOS
            planetas_transitos = {}
            retrogrados_transitos = []
            if datos_interpretacion and 'transitos' in datos_interpretacion:
                aspectos_transitos = datos_interpretacion['transitos'].get('aspectos', [])
                pos_trans = datos_interpretacion['transitos'].get('posiciones_transito', {})
                
                for planeta, datos_planeta in pos_trans.items():
                    if 'grado' in datos_planeta:
                        grado_abs = datos_planeta['grado']
                        signo, grado_en_signo = grado_a_signo(grado_abs)
                        planetas_transitos[planeta] = {
                            'degree': decimal_a_sexagesimal(grado_en_signo),
                            'sign': signo,
                            'retrogrado': datos_planeta.get('retrogrado', False)
                        }
                        if datos_planeta.get('retrogrado'):
                            retrogrados_transitos.append(planeta)
            
            datos_template.update({
                'fecha_nacimiento': datos_cliente.get('fecha_nacimiento', ''),
                'hora_nacimiento': datos_cliente.get('hora_nacimiento', ''),
                'lugar_nacimiento': datos_cliente.get('lugar_nacimiento', ''),
                'pais_nacimiento': datos_cliente.get('pais_nacimiento', 'España'),
                'planetas': planetas_dict,
                'aspectos_natales': aspectos_natales,
                'retrogrados_natales': retrogrados_natales,
                'aspectos_progresados': aspectos_progresados,
                'planetas_progresados': planetas_progresados,  # AÑADIR ESTA LÍNEA
                'retrogrados_progresados': retrogrados_progresados,  # AÑADIR ESTA LÍNEA
                'aspectos_transitos': aspectos_transitos,
                'planetas_transitos': planetas_transitos,  # AÑADIR ESTA LÍNEA
                'retrogrados_transitos': retrogrados_transitos,  # AÑADIR ESTA LÍNEA
                'carta_natal_img': os.path.abspath(archivos_unicos.get('carta_natal_img', '')) if archivos_unicos.get('carta_natal_img') else None,
                'progresiones_img': os.path.abspath(archivos_unicos.get('progresiones_img', '')) if archivos_unicos.get('progresiones_img') else None,
                'transitos_img': os.path.abspath(archivos_unicos.get('transitos_img', '')) if archivos_unicos.get('transitos_img') else None
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

def convertir_html_a_pdf_weasyprint(archivo_html, archivo_pdf):
    """
    Convertir HTML a PDF usando WeasyPrint (más robusto que Playwright)
    WeasyPrint maneja mejor las imágenes base64 grandes
    """
    try:
        import os
        
        print(f"📄 Convirtiendo con WeasyPrint: {archivo_html} -> {archivo_pdf}")
        
        # Crear directorio de salida
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        # Import explícito para evitar conflictos con ReportLab
        from weasyprint import HTML as WeasyHTML
        
        # Convertir HTML a PDF
        WeasyHTML(filename=archivo_html).write_pdf(archivo_pdf)
        
        if os.path.exists(archivo_pdf) and os.path.getsize(archivo_pdf) > 1000:
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado con WeasyPrint: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error en WeasyPrint: {e}")
        import traceback
        traceback.print_exc()
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

def procesar_y_enviar_informe(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion=None, datos_interpretacion=None):
    """Función principal que coordina todo el proceso de generación y envío"""
    try:
        print(f"🎯 Procesando informe {tipo_servicio} para: {datos_cliente.get('email', 'Cliente')}")
        
        # 1. Generar HTML
        # Generar cartas primero si es un servicio astrológico
        datos_interpretacion = None
        if tipo_servicio in ['carta_astral_ia', 'revolucion_solar_ia']:
            from agents.sofia import generar_cartas_astrales_completas
            exito, datos_interpretacion = generar_cartas_astrales_completas(datos_cliente, archivos_unicos)
            if not exito:
                print("⚠️ Error generando cartas, continuando sin datos astrológicos")

        archivo_html = generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion, datos_interpretacion)
        if not archivo_html:
            print("❌ Error generando HTML")
            return False
        
        # 2. Convertir a PDF
        archivo_pdf = archivo_html.replace('templates/', 'informes/').replace('.html', '.pdf')
        resultado_pdf = convertir_html_a_pdf_weasyprint(archivo_html, archivo_pdf)
        if not resultado_pdf:
            print("❌ Error generando PDF")
            return False
        
        # Usar el resultado (puede ser PDF o HTML fallback)
        archivo_final = archivo_pdf if resultado_pdf == True else resultado_pdf
        
        # 3. Enviar por email
        email_cliente = datos_cliente.get('email')
        if email_cliente:
            nombre_cliente = datos_cliente.get('nombre', 'Cliente')
            exito_email = enviar_informe_por_email(email_cliente, archivo_final, tipo_servicio, nombre_cliente)
            if exito_email:
                print(f"✅ Proceso completo: Informe {tipo_servicio} enviado a {email_cliente}")
                return True
            else:
                print(f"⚠️ Informe generado pero no enviado: {archivo_final}")
                return archivo_final
        else:
            print(f"⚠️ No hay email del cliente. Informe guardado: {archivo_final}")
            return archivo_final
            
    except Exception as e:
        print(f"❌ Error en proceso completo: {e}")
        import traceback
        traceback.print_exc()
        return False

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