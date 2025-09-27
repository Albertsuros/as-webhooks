# informes.py - VERSIÓN COMPLETA con TODAS las funciones legacy
import os
import gc
from datetime import datetime
import pytz
from jinja2 import Template
from playwright.sync_api import sync_playwright
import matplotlib
matplotlib.use('Agg')
import traceback

def generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion=""):
    """Generar informe HTML - VERSIÓN BASE64"""
    try:
        print(f"📄 Generando HTML para AS Cartastral: {tipo_servicio}")
        
        if not archivos_unicos or not isinstance(archivos_unicos, dict):
            import uuid
            id_unico = str(uuid.uuid4())[:8]
            archivos_unicos = {
                'informe_html': f"templates/informe_{tipo_servicio}_{id_unico}.html",
                'es_producto_m': False,
                'imagenes_base64': {}
            }
        
        # TEMPLATE HTML SIMPLIFICADO PERO COMPLETO
        template_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ nombre }}}} - {tipo_servicio.replace('_', ' ').title()} - AS Cartastral</title>
    <style>
        body {{ font-family: 'Georgia', serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
        .header {{ text-align: center; border-bottom: 3px solid #667eea; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #667eea; font-size: 2.5em; margin: 0; }}
        .datos-personales {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
        .dato {{ font-weight: bold; color: #FFD700; }}
        .imagen-carta {{ margin: 40px 0; padding: 25px; border-left: 5px solid #667eea; background: #f8f9ff; border-radius: 12px; }}
        .imagen-carta h2 {{ color: #667eea; font-size: 1.8em; margin-bottom: 20px; text-align: center; }}
        .imagen-carta img {{ display: block; margin: 20px auto; max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); border: 3px solid #667eea; }}
        .aspectos-section {{ background: #f8f9ff; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #667eea; }}
        .aspectos-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 15px; }}
        .aspecto-item {{ background: white; padding: 12px 16px; border-radius: 8px; border: 1px solid #e0e6ed; display: flex; justify-content: space-between; align-items: center; }}
        .aspecto-planetas {{ font-weight: 500; color: #333; flex: 1; }}
        .aspecto-orbe {{ font-size: 0.85em; color: #666; background: #f0f2f5; padding: 4px 8px; border-radius: 6px; }}
        .section {{ margin: 30px 0; padding: 20px; background: #f8f9ff; border-radius: 10px; border-left: 4px solid #667eea; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 2px solid #667eea; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌟 {tipo_servicio.replace('_', ' ').title()} 🌟</h1>
            <h2>AS Cartastral - Análisis Astrológico</h2>
        </div>

        <div class="datos-personales">
            <h3>📋 Datos Personales</h3>
            <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
            <p><span class="dato">Email:</span> {{{{ email }}}}</p>
            {{% if fecha_nacimiento %}}<p><span class="dato">Fecha:</span> {{{{ fecha_nacimiento }}}}</p>{{% endif %}}
            {{% if hora_nacimiento %}}<p><span class="dato">Hora:</span> {{{{ hora_nacimiento }}}}</p>{{% endif %}}
            {{% if lugar_nacimiento %}}<p><span class="dato">Lugar:</span> {{{{ lugar_nacimiento }}}}</p>{{% endif %}}
        </div>

        <!-- CARTA NATAL -->
        {{% if imagenes_base64 and imagenes_base64.carta_natal %}}
        <div class="imagen-carta">
            <h2>🌅 Tu Carta Natal</h2>
            <img src="{{{{ imagenes_base64.carta_natal }}}}" alt="Carta Natal">
            <p>Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento.</p>
            
            {{% if aspectos_natales %}}
            <div class="aspectos-section">
                <h3>⭐ Aspectos Natales ({{{{ aspectos_natales|length }}}})</h3>
                <div class="aspectos-grid">
                    {{% for aspecto in aspectos_natales[:10] %}}
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{{{{ aspecto.planeta1 }}}} {{{{ aspecto.aspecto }}}} {{{{ aspecto.planeta2 }}}}</span>
                        <span class="aspecto-orbe">{{{{ "%.1f"|format(aspecto.orbe) }}}}°</span>
                    </div>
                    {{% endfor %}}
                    {{% if aspectos_natales|length > 10 %}}
                    <div style="grid-column: 1 / -1; text-align: center; color: #667eea; font-style: italic;">
                        + {{{{ aspectos_natales|length - 10 }}}} aspectos más...
                    </div>
                    {{% endif %}}
                </div>
            </div>
            {{% endif %}}
        </div>
        {{% endif %}}

        <!-- PROGRESIONES -->
        {{% if imagenes_base64 and imagenes_base64.progresiones %}}
        <div class="imagen-carta">
            <h2>📈 Progresiones Secundarias</h2>
            <img src="{{{{ imagenes_base64.progresiones }}}}" alt="Progresiones">
            
            {{% if aspectos_progresiones %}}
            <div class="aspectos-section">
                <h3>🌱 Aspectos de Progresión ({{{{ aspectos_progresiones|length }}}})</h3>
                <div class="aspectos-grid">
                    {{% for aspecto in aspectos_progresiones[:8] %}}
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{{{{ aspecto.planeta_progresion }}}} {{{{ aspecto.tipo }}}} {{{{ aspecto.planeta_natal }}}}</span>
                        <span class="aspecto-orbe">{{{{ "%.1f"|format(aspecto.orbe) }}}}°</span>
                    </div>
                    {{% endfor %}}
                </div>
            </div>
            {{% endif %}}
        </div>
        {{% endif %}}

        <!-- TRÁNSITOS -->
        {{% if imagenes_base64 and imagenes_base64.transitos %}}
        <div class="imagen-carta">
            <h2>🔄 Tránsitos Actuales</h2>
            <img src="{{{{ imagenes_base64.transitos }}}}" alt="Tránsitos">
            
            {{% if aspectos_transitos %}}
            <div class="aspectos-section">
                <h3>⚡ Aspectos de Tránsito ({{{{ aspectos_transitos|length }}}})</h3>
                <div class="aspectos-grid">
                    {{% for aspecto in aspectos_transitos[:8] %}}
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{{{{ aspecto.planeta_transito }}}} {{{{ aspecto.tipo }}}} {{{{ aspecto.planeta_natal }}}}</span>
                        <span class="aspecto-orbe">{{{{ "%.1f"|format(aspecto.orbe) }}}}°</span>
                    </div>
                    {{% endfor %}}
                </div>
            </div>
            {{% endif %}}
        </div>
        {{% endif %}}

        {{% if resumen_sesion %}}
        <div class="section">
            <h2>📞 Resumen de tu Sesión</h2>
            <div>{{{{ resumen_sesion }}}}</div>
        </div>
        {{% endif %}}

        <div class="footer">
            <p><strong>Generado:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
            <p><strong>AS Cartastral</strong> - Servicios Astrológicos IA</p>
        </div>
    </div>
</body>
</html>"""
        
        # Preparar datos para template
        zona = pytz.timezone('Europe/Madrid')
        ahora = datetime.now(zona)
        
        datos_template = {
            'nombre': datos_cliente.get('nombre', 'Cliente'),
            'email': datos_cliente.get('email', ''),
            'fecha_nacimiento': datos_cliente.get('fecha_nacimiento', ''),
            'hora_nacimiento': datos_cliente.get('hora_nacimiento', ''),
            'lugar_nacimiento': datos_cliente.get('lugar_nacimiento', ''),
            'fecha_generacion': ahora.strftime("%d/%m/%Y"),
            'hora_generacion': ahora.strftime("%H:%M:%S"),
            'resumen_sesion': resumen_sesion
        }
        
        # Añadir datos de aspectos si están disponibles
        for key in ['imagenes_base64', 'aspectos_natales', 'aspectos_progresiones', 'aspectos_transitos', 'posiciones_natales', 'estadisticas']:
            if key in archivos_unicos:
                datos_template[key] = archivos_unicos[key]
        
        # Renderizar template
        template = Template(template_html)
        html_content = template.render(**datos_template)
        
        # Guardar archivo HTML
        archivo_html = archivos_unicos.get('informe_html', f"templates/informe_{tipo_servicio}_temp.html")
        os.makedirs('templates', exist_ok=True)
        
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML generado: {archivo_html}")
        return archivo_html
        
    except Exception as e:
        print(f"❌ Error generando HTML: {e}")
        traceback.print_exc()
        return None

def convertir_html_a_pdf(archivo_html, archivo_pdf):
    """Convertir HTML a PDF usando Playwright"""
    try:
        print(f"🔄 Convirtiendo HTML a PDF: {archivo_html} -> {archivo_pdf}")
        
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            page.set_content(html_content)
            page.wait_for_load_state('networkidle')
            
            page.pdf(
                path=archivo_pdf,
                format='A4',
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                print_background=True,
                prefer_css_page_size=True
            )
            
            browser.close()
        
        if os.path.exists(archivo_pdf):
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            print(f"❌ PDF no se creó: {archivo_pdf}")
            return False
            
    except Exception as e:
        print(f"❌ Error convirtiendo a PDF: {e}")
        traceback.print_exc()
        return False

# =======================================================================
# FUNCIONES LEGACY REQUERIDAS POR OTROS ARCHIVOS
# =======================================================================

def generar_y_enviar_informe_desde_agente(datos_cliente, tipo_servicio, resumen_sesion="", archivos_cartas=None):
    """Función requerida por astrologa_cartastral.py"""
    try:
        print(f"📧 Generando informe desde agente: {tipo_servicio}")
        
        if not archivos_cartas:
            import uuid
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            id_unico = str(uuid.uuid4())[:8]
            archivos_cartas = {
                'informe_html': f"templates/informe_{tipo_servicio}_{id_unico}.html",
                'informe_pdf': f"informes/informe_{tipo_servicio}_{id_unico}.pdf",
                'timestamp': timestamp,
                'es_producto_m': False,
                'duracion_minutos': 40
            }
        
        # Generar HTML
        archivo_html = generar_informe_html(
            datos_cliente=datos_cliente,
            tipo_servicio=tipo_servicio,
            archivos_unicos=archivos_cartas,
            resumen_sesion=resumen_sesion
        )
        
        if not archivo_html:
            return {
                'success': False,
                'error': 'No se pudo generar el HTML',
                'archivo_html': None,
                'archivo_pdf': None
            }
        
        # Convertir a PDF
        archivo_pdf = archivos_cartas.get('informe_pdf', f"informes/informe_{tipo_servicio}_{archivos_cartas.get('timestamp', 'unknown')}.pdf")
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        pdf_generado = convertir_html_a_pdf(archivo_html, archivo_pdf)
        
        if pdf_generado:
            return {
                'success': True,
                'mensaje': f'Informe {tipo_servicio} generado correctamente',
                'archivo_html': archivo_html,
                'archivo_pdf': archivo_pdf,
                'tipo_servicio': tipo_servicio,
                'cliente': datos_cliente.get('nombre', 'Cliente'),
                'timestamp': archivos_cartas.get('timestamp'),
                'metodo': 'base64_system'
            }
        else:
            return {
                'success': False,
                'error': 'No se pudo generar el PDF',
                'archivo_html': archivo_html,
                'archivo_pdf': archivo_pdf
            }
            
    except Exception as e:
        print(f"❌ Error en generar_y_enviar_informe_desde_agente: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'archivo_html': None,
            'archivo_pdf': None,
            'traceback': traceback.format_exc()
        }

def procesar_y_enviar_informe(datos_cliente, tipo_servicio, datos_astrales=None, resumen_sesion=""):
    """Función requerida por main.py"""
    try:
        print(f"📋 Procesando informe: {tipo_servicio}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archivos_unicos = {
            'timestamp': timestamp,
            'es_producto_m': False,
            'duracion_minutos': 40,
            'informe_pdf': f"informes/informe_{tipo_servicio}_{timestamp}.pdf"
        }
        
        # Si se proporcionan datos astrales, añadirlos
        if datos_astrales:
            archivos_unicos.update(datos_astrales)
        
        # Usar la función principal
        resultado = generar_y_enviar_informe_desde_agente(
            datos_cliente=datos_cliente,
            tipo_servicio=tipo_servicio,
            resumen_sesion=resumen_sesion,
            archivos_cartas=archivos_unicos
        )
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error en procesar_y_enviar_informe: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def generar_informe_completo(datos_cliente, tipo_servicio, datos_astrales=None, resumen_sesion=""):
    """Función wrapper para compatibilidad"""
    return procesar_y_enviar_informe(datos_cliente, tipo_servicio, datos_astrales, resumen_sesion)

def crear_archivos_unicos_testing(tipo_servicio, timestamp=None):
    """Crear estructura de archivos para testing"""
    if not timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return {
        'timestamp': timestamp,
        'informe_html': f"templates/informe_{tipo_servicio}_{timestamp}.html",
        'informe_pdf': f"informes/informe_{tipo_servicio}_{timestamp}.pdf",
        'es_producto_m': False,
        'duracion_minutos': 40,
        'imagenes_base64': {}
    }

def obtener_ruta_imagen_absoluta(nombre_imagen):
    """Función legacy para compatibilidad"""
    ruta = f"./img/{nombre_imagen}"
    if os.path.exists(ruta):
        return os.path.abspath(ruta)
    else:
        return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y0ZjRmNCIvPjx0ZXh0IHg9IjE1MCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkltYWdlbiBubyBkaXNwb25pYmxlPC90ZXh0Pjwvc3ZnPg=="

def obtener_portada_con_logo(tipo_servicio, nombre):
    """Función legacy para compatibilidad"""
    return f"""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-radius: 10px; margin-bottom: 30px;">
        <h1 style="margin: 0; font-size: 2.5em;">AS Cartastral</h1>
        <h2 style="margin: 10px 0;">{tipo_servicio.replace('_', ' ').title()}</h2>
        <h3 style="margin: 0;">Para {nombre}</h3>
    </div>
    """

def enviar_informe_por_email(datos_cliente, archivo_pdf, tipo_servicio):
    """Función placeholder para envío de email"""
    try:
        if os.path.exists(archivo_pdf):
            return {
                'success': True,
                'mensaje': f'Informe {tipo_servicio} preparado para envío',
                'email': datos_cliente.get('email', ''),
                'archivo': archivo_pdf
            }
        else:
            return {
                'success': False,
                'error': 'Archivo PDF no encontrado'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Funciones adicionales que podrían ser necesarias
def obtener_template_html(tipo_servicio):
    """Obtener template HTML básico"""
    return "<!-- Template HTML básico -->"

def generar_solo_pdf(datos_cliente, especialidad, client_id=None):
    """Generar solo PDF sin otros procesamientos"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archivos_unicos = crear_archivos_unicos_testing(especialidad, timestamp)
        
        resultado = procesar_y_enviar_informe(
            datos_cliente=datos_cliente,
            tipo_servicio=especialidad,
            datos_astrales=archivos_unicos,
            resumen_sesion="PDF generado directamente"
        )
        
        return resultado
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
        
# =======================================================================
# 1. CORREGIR crear_archivos_unicos_testing en informes.py
# =======================================================================

# REEMPLAZAR en informes.py:
def crear_archivos_unicos_testing(tipo_servicio, timestamp=None):
    """Crear estructura de archivos para testing - CORREGIDO"""
    if not timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return {
        'timestamp': timestamp,
        'informe_html': f"templates/informe_{tipo_servicio}_{timestamp}.html",
        'informe_pdf': f"informes/informe_{tipo_servicio}_{timestamp}.pdf",
        'es_producto_m': False,
        'duracion_minutos': 40,
        'imagenes_base64': {}
    }

# =======================================================================
# 2. CONVERTIR HTML A PDF OPTIMIZADO PARA BASE64
# =======================================================================

# REEMPLAZAR en informes.py:
def convertir_html_a_pdf(archivo_html, archivo_pdf):
    """Convertir HTML a PDF - VERSIÓN OPTIMIZADA PARA BASE64"""
    try:
        print(f"🔄 Convirtiendo HTML a PDF optimizado: {archivo_html} -> {archivo_pdf}")
        
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        # Leer HTML
        with open(archivo_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # OPTIMIZACIÓN: Reducir calidad de imágenes base64 si son muy grandes
        if len(html_content) > 5000000:  # Si HTML > 5MB
            print("⚠️ HTML muy grande, optimizando imágenes...")
            # Buscar y reemplazar imágenes base64 muy grandes
            import re
            pattern = r'data:image/png;base64,([A-Za-z0-9+/=]{50000,})'
            matches = re.findall(pattern, html_content)
            print(f"🔍 Encontradas {len(matches)} imágenes grandes")
            
            # Por ahora, continuar con el HTML original
            # En el futuro podríamos comprimir las imágenes aquí
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--memory-pressure-off',
                    '--max_old_space_size=4096'
                ]
            )
            
            page = browser.new_page()
            
            # Configurar timeouts más largos para contenido pesado
            page.set_default_timeout(60000)  # 60 segundos
            
            # Cargar HTML con configuración optimizada
            page.set_content(html_content, wait_until='domcontentloaded')
            
            # Esperar que las imágenes base64 se procesen
            try:
                page.wait_for_load_state('networkidle', timeout=30000)
            except:
                print("⚠️ Timeout esperando networkidle, continuando...")
            
            # Generar PDF con configuración optimizada
            page.pdf(
                path=archivo_pdf,
                format='A4',
                margin={
                    'top': '1cm',
                    'right': '1cm', 
                    'bottom': '1cm',
                    'left': '1cm'
                },
                print_background=True,
                prefer_css_page_size=True,
                # Optimizaciones adicionales
                scale=0.8,  # Reducir escala para contenido más compacto
            )
            
            browser.close()
        
        if os.path.exists(archivo_pdf):
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado optimizado: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            print(f"❌ PDF no se creó: {archivo_pdf}")
            return False
            
    except Exception as e:
        print(f"❌ Error convirtiendo HTML a PDF optimizado: {e}")
        import traceback
        traceback.print_exc()
        return False