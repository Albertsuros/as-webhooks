# informes.py - VERSIÓN COMPLETA ACTUALIZADA para BASE64

import os
import gc
from datetime import datetime
import pytz
from jinja2 import Template
from playwright.sync_api import sync_playwright
import matplotlib
matplotlib.use('Agg')

def generar_informe_html(datos_cliente, tipo_servicio, archivos_unicos, resumen_sesion=""):
    """
    Generar informe HTML - VERSIÓN ACTUALIZADA PARA BASE64
    Ahora usa imagenes_base64 en lugar de archivos
    """
    from datetime import datetime
    import pytz
    import os
    from jinja2 import Template
    
    try:
        print(f"📄 Generando HTML para AS Cartastral: {tipo_servicio}")
        
        # Si archivos_unicos está vacío o es None, crear estructura básica
        if not archivos_unicos or not isinstance(archivos_unicos, dict):
            import uuid
            id_unico = str(uuid.uuid4())[:8]
            archivos_unicos = {
                'informe_html': f"templates/informe_{tipo_servicio}_{id_unico}.html",
                'es_producto_m': False,
                'imagenes_base64': {}
            }
        
        # TEMPLATE HTML COMPLETO CON BASE64 Y ASPECTOS
        template_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{{{ nombre }}}} - {tipo_servicio.replace('_', ' ').title()} - AS Cartastral</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .datos-personales {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .datos-personales h3 {{
            margin: 0 0 15px 0;
            text-align: center;
        }}
        .dato {{
            font-weight: bold;
            color: #FFD700;
        }}
        .imagen-carta {{
            margin: 40px 0;
            padding: 25px;
            border-left: 5px solid #667eea;
            background: linear-gradient(90deg, #f8f9ff 0%, #ffffff 100%);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .imagen-carta h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            text-align: center;
            border-bottom: 2px solid #e8f4f8;
            padding-bottom: 10px;
        }}
        .imagen-carta img {{
            display: block;
            margin: 20px auto;
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            border: 3px solid #667eea;
        }}
        .aspectos-section {{
            background: #f8f9ff;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}
        .aspectos-section h3 {{
            color: #667eea;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        .aspectos-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        .aspecto-item {{
            background: white;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #e0e6ed;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
        }}
        .aspecto-item:hover {{
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
            border-color: #667eea;
        }}
        .aspecto-planetas {{
            font-weight: 500;
            color: #333;
            flex: 1;
        }}
        .aspecto-orbe {{
            font-size: 0.85em;
            color: #666;
            background: #f0f2f5;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 500;
        }}
        .mas-aspectos {{
            grid-column: 1 / -1;
            text-align: center;
            color: #667eea;
            font-style: italic;
            padding: 10px;
            background: #e8f4f8;
            border-radius: 6px;
        }}
        .posiciones-section {{
            background: #fff8e1;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid #ff9800;
        }}
        .posiciones-section h3 {{
            color: #e65100;
            margin-top: 0;
            margin-bottom: 15px;
        }}
        .planetas-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        .planeta-item {{
            background: white;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid #ffcc80;
        }}
        .planeta-nombre {{
            font-weight: bold;
            color: #e65100;
        }}
        .planeta-posicion {{
            margin-left: 8px;
            color: #333;
        }}
        .planeta-casa {{
            font-size: 0.8em;
            color: #666;
            margin-left: 8px;
        }}
        .interpretacion {{
            background: #f8f9ff;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid #764ba2;
        }}
        .interpretacion h3 {{
            color: #764ba2;
            margin-top: 0;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9ff;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #667eea;
            color: #666;
            font-style: italic;
        }}
        .estadisticas {{
            background: #e8f5e8;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #4caf50;
        }}
        .estadisticas h4 {{
            color: #2e7d32;
            margin-top: 0;
        }}
        .estadisticas p {{
            margin: 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <h1>🌟 {tipo_servicio.replace('_', ' ').title()} 🌟</h1>
            <h2>Análisis Astrológico Personalizado - AS Cartastral</h2>
        </div>

        <!-- DATOS PERSONALES -->
        <div class="datos-personales">
            <h3>📋 Datos Personales</h3>
            <p><span class="dato">Nombre:</span> {{{{ nombre }}}}</p>
            <p><span class="dato">Email:</span> {{{{ email }}}}</p>
            {{% if fecha_nacimiento %}}<p><span class="dato">Fecha de nacimiento:</span> {{{{ fecha_nacimiento }}}}</p>{{% endif %}}
            {{% if hora_nacimiento %}}<p><span class="dato">Hora de nacimiento:</span> {{{{ hora_nacimiento }}}}</p>{{% endif %}}
            {{% if lugar_nacimiento %}}<p><span class="dato">Lugar de nacimiento:</span> {{{{ lugar_nacimiento }}}}</p>{{% endif %}}
        </div>

        <!-- CARTA NATAL -->
        {{% if imagenes_base64 and imagenes_base64.carta_natal %}}
        <div class="imagen-carta">
            <h2>🌅 Tu Carta Natal</h2>
            <img src="{{{{ imagenes_base64.carta_natal }}}}" alt="Carta Natal">
            <p>Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento.</p>
            
            <!-- ASPECTOS NATALES -->
            {{% if aspectos_natales %}}
            <div class="aspectos-section">
                <h3>⭐ Aspectos Natales ({{{{ aspectos_natales|length }}}})</h3>
                <div class="aspectos-grid">
                    {{% for aspecto in aspectos_natales[:12] %}}
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{{{{ aspecto.planeta1 }}}} {{{{ aspecto.aspecto }}}} {{{{ aspecto.planeta2 }}}}</span>
                        <span class="aspecto-orbe">{{{{ "%.1f"|format(aspecto.orbe) }}}}°</span>
                    </div>
                    {{% endfor %}}
                    {{% if aspectos_natales|length > 12 %}}
                    <div class="mas-aspectos">+ {{{{ aspectos_natales|length - 12 }}}} aspectos más...</div>
                    {{% endif %}}
                </div>
            </div>
            {{% endif %}}

            <!-- POSICIONES PLANETARIAS -->
            {{% if posiciones_natales %}}
            <div class="posiciones-section">
                <h3>🪐 Posiciones Planetarias</h3>
                <div class="planetas-grid">
                    {{% for planeta, datos in posiciones_natales.items() %}}
                    <div class="planeta-item">
                        <span class="planeta-nombre">{{{{ planeta }}}}</span>
                        <span class="planeta-posicion">{{{{ datos.signo if datos.signo else 'N/A' }}}} {{{{ "%.1f"|format(datos.grado) if datos.grado else 'N/A' }}}}°</span>
                        {{% if datos.casa %}}<span class="planeta-casa">Casa {{{{ datos.casa }}}}</span>{{% endif %}}
                    </div>
                    {{% endfor %}}
                </div>
            </div>
            {{% endif %}}
        </div>
        {{% endif %}}

        <!-- PROGRESIONES -->
        {{% if imagenes_base64 and imagenes_base64.progresiones %}}
        <div class="imagen-carta">
            <h2>📈 Progresiones Secundarias</h2>
            <img src="{{{{ imagenes_base64.progresiones }}}}" alt="Progresiones Secundarias">
            <p>Las progresiones muestran tu evolución personal interna.</p>
            
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
                    {{% if aspectos_progresiones|length > 8 %}}
                    <div class="mas-aspectos">+ {{{{ aspectos_progresiones|length - 8 }}}} aspectos más...</div>
                    {{% endif %}}
                </div>
            </div>
            {{% endif %}}
        </div>
        {{% endif %}}

        <!-- TRÁNSITOS -->
        {{% if imagenes_base64 and imagenes_base64.transitos %}}
        <div class="imagen-carta">
            <h2>🔄 Tránsitos Actuales</h2>
            <img src="{{{{ imagenes_base64.transitos }}}}" alt="Tránsitos Actuales">
            <p>Los tránsitos planetarios actuales muestran las energías que están influyendo en tu vida ahora.</p>
            
            {{% if aspectos_transitos %}}
            <div class="aspectos-section">
                <h3>⚡ Aspectos de Tránsito Activos ({{{{ aspectos_transitos|length }}}})</h3>
                <div class="aspectos-grid">
                    {{% for aspecto in aspectos_transitos[:10] %}}
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{{{{ aspecto.planeta_transito }}}} {{{{ aspecto.tipo }}}} {{{{ aspecto.planeta_natal }}}}</span>
                        <span class="aspecto-orbe">{{{{ "%.1f"|format(aspecto.orbe) }}}}°</span>
                    </div>
                    {{% endfor %}}
                    {{% if aspectos_transitos|length > 10 %}}
                    <div class="mas-aspectos">+ {{{{ aspectos_transitos|length - 10 }}}} aspectos más...</div>
                    {{% endif %}}
                </div>
            </div>

            <!-- ESTADÍSTICAS DE TRÁNSITOS -->
            {{% if estadisticas %}}
            <div class="estadisticas">
                <h4>🌟 Resumen de Influencias Actuales</h4>
                <p><strong>📊 Total de aspectos activos:</strong> {{{{ estadisticas.total_aspectos_transitos }}}}</p>
                <p><strong>🎯 Aspectos exactos (< 1°):</strong> {{{{ aspectos_transitos|selectattr("orbe", "lt", 1.0)|list|length }}}}</p>
                {{% if aspectos_transitos %}}
                <p><strong>⭐ Aspecto más exacto:</strong> 
                    {{% set aspecto_exacto = aspectos_transitos|min(attribute="orbe") %}}
                    {{{{ aspecto_exacto.planeta_transito }}}} {{{{ aspecto_exacto.tipo }}}} {{{{ aspecto_exacto.planeta_natal }}}} ({{{{ "%.2f"|format(aspecto_exacto.orbe) }}}}°)
                </p>
                {{% endif %}}
            </div>
            {{% endif %}}
        </div>
        {{% endif %}}

        <!-- SINASTRIA (si aplica) -->
        {{% if imagenes_base64 and imagenes_base64.sinastria %}}
        <div class="imagen-carta">
            <h2>💞 Análisis de Compatibilidad</h2>
            <img src="{{{{ imagenes_base64.sinastria }}}}" alt="Sinastría">
        </div>
        {{% endif %}}

        <!-- RESUMEN DE SESIÓN -->
        {{% if resumen_sesion %}}
        <div class="section">
            <h2>📞 Resumen de tu Sesión</h2>
            <p><strong>Duración:</strong> {{{{ duracion_minutos|default(40) }}}} minutos</p>
            <div class="interpretacion">{{{{ resumen_sesion }}}}</div>
        </div>
        {{% endif %}}

        <!-- FOOTER -->
        <div class="footer">
            <p><strong>Fecha de generación:</strong> {{{{ fecha_generacion }}}} a las {{{{ hora_generacion }}}}</p>
            <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
            <p>✨ Este análisis astrológico ha sido creado con precisión cósmica ✨</p>
        </div>
    </div>
</body>
</html>"""
        
        # PREPARAR DATOS PARA EL TEMPLATE
        from datetime import datetime
        import pytz
        zona = pytz.timezone('Europe/Madrid')
        ahora = datetime.now(zona)
        
        # Datos básicos del template
        datos_template = {
            'nombre': datos_cliente.get('nombre', 'Cliente'),
            'email': datos_cliente.get('email', ''),
            'fecha_nacimiento': datos_cliente.get('fecha_nacimiento', ''),
            'hora_nacimiento': datos_cliente.get('hora_nacimiento', ''),
            'lugar_nacimiento': datos_cliente.get('lugar_nacimiento', ''),
            'fecha_generacion': ahora.strftime("%d/%m/%Y"),
            'hora_generacion': ahora.strftime("%H:%M:%S"),
            'duracion_minutos': archivos_unicos.get('duracion_minutos', 40),
            'resumen_sesion': resumen_sesion
        }
        
        # AÑADIR DATOS DE ASPECTOS SI ESTÁN DISPONIBLES
        if 'imagenes_base64' in archivos_unicos:
            datos_template['imagenes_base64'] = archivos_unicos['imagenes_base64']
        
        if 'aspectos_natales' in archivos_unicos:
            datos_template['aspectos_natales'] = archivos_unicos['aspectos_natales']
            
        if 'aspectos_progresiones' in archivos_unicos:
            datos_template['aspectos_progresiones'] = archivos_unicos['aspectos_progresiones']
            
        if 'aspectos_transitos' in archivos_unicos:
            datos_template['aspectos_transitos'] = archivos_unicos['aspectos_transitos']
            
        if 'posiciones_natales' in archivos_unicos:
            datos_template['posiciones_natales'] = archivos_unicos['posiciones_natales']
            
        if 'estadisticas' in archivos_unicos:
            datos_template['estadisticas'] = archivos_unicos['estadisticas']
        
        # Renderizar template
        template = Template(template_html)
        html_content = template.render(**datos_template)
        
        # Generar archivo HTML
        archivo_html = archivos_unicos.get('informe_html', f"templates/informe_{tipo_servicio}_{datos_cliente.get('codigo_servicio', 'test')}.html")
        
        # Crear directorio si no existe
        os.makedirs('templates', exist_ok=True)
        
        # Guardar archivo HTML
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ AS Cartastral - HTML generado: {archivo_html}")
        return archivo_html
        
    except Exception as e:
        print(f"❌ Error generando HTML para AS Cartastral: {e}")
        import traceback
        traceback.print_exc()
        return None


def convertir_html_a_pdf(archivo_html, archivo_pdf):
    """Convertir HTML a PDF usando Playwright - VERSIÓN MEJORADA"""
    try:
        print(f"🔄 Convirtiendo HTML a PDF: {archivo_html} -> {archivo_pdf}")
        
        # Crear directorio de salida si no existe
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Leer el archivo HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Cargar el HTML con base_url para resolver rutas relativas
            page.set_content(html_content)
            
            # Esperar a que se carguen las imágenes base64
            page.wait_for_load_state('networkidle')
            
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
                prefer_css_page_size=True
            )
            
            browser.close()
        
        # Verificar que el PDF se creó
        if os.path.exists(archivo_pdf):
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado exitosamente: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            print(f"❌ Error: PDF no se creó en {archivo_pdf}")
            return False
            
    except Exception as e:
        print(f"❌ Error convirtiendo HTML a PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


# Funciones adicionales para compatibilidad con el sistema existente
def obtener_ruta_imagen_absoluta(nombre_imagen):
    """Obtener ruta absoluta de imagen (LEGACY - para compatibilidad)"""
    # Esta función se mantiene para compatibilidad con código existente
    # Pero en el nuevo sistema base64 no se usa
    ruta = f"./img/{nombre_imagen}"
    if os.path.exists(ruta):
        return os.path.abspath(ruta)
    else:
        # Devolver placeholder SVG si no existe
        return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y0ZjRmNCIvPjx0ZXh0IHg9IjE1MCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkltYWdlbiBubyBkaXNwb25pYmxlPC90ZXh0Pjwvc3ZnPg=="

def obtener_portada_con_logo(tipo_servicio, nombre):
    """Generar portada con logo (LEGACY - para compatibilidad)"""
    return f"""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-radius: 10px; margin-bottom: 30px;">
        <h1 style="margin: 0; font-size: 2.5em;">AS Cartastral</h1>
        <h2 style="margin: 10px 0;">{tipo_servicio.replace('_', ' ').title()}</h2>
        <h3 style="margin: 0;">Para {nombre}</h3>
    </div>
    """
    
# =======================================================================
# FUNCIÓN FALTANTE - AÑADIR AL FINAL DE informes.py
# =======================================================================

def generar_y_enviar_informe_desde_agente(datos_cliente, tipo_servicio, resumen_sesion="", archivos_cartas=None):
    """
    Función para generar y procesar informe desde agentes
    VERSIÓN ACTUALIZADA para sistema base64
    """
    try:
        print(f"📧 Generando informe desde agente: {tipo_servicio}")
        
        # Crear archivos_unicos si no se proporciona
        if not archivos_cartas:
            import uuid
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            id_unico = str(uuid.uuid4())[:8]
            
            archivos_cartas = {
                'informe_html': f"templates/informe_{tipo_servicio}_{id_unico}.html",
                'informe_pdf': f"informes/informe_{tipo_servicio}_{id_unico}.pdf",
                'timestamp': timestamp,
                'es_producto_m': False,
                'duracion_minutos': 40
            }
        
        # PASO 1: Generar HTML
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
        
        # PASO 2: Convertir a PDF
        archivo_pdf = archivos_cartas.get('informe_pdf', f"informes/informe_{tipo_servicio}_{archivos_cartas.get('timestamp', 'unknown')}.pdf")
        
        # Crear directorio si no existe
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
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'archivo_html': None,
            'archivo_pdf': None,
            'traceback': traceback.format_exc()
        }

# =======================================================================
# FUNCIONES ADICIONALES DE COMPATIBILIDAD
# =======================================================================

def generar_informe_completo(datos_cliente, tipo_servicio, datos_astrales=None, resumen_sesion=""):
    """
    Función wrapper para compatibilidad con sistema anterior
    """
    try:
        # Preparar archivos_unicos con datos astrales si están disponibles
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        archivos_unicos = {
            'timestamp': timestamp,
            'es_producto_m': False,
            'duracion_minutos': 40
        }
        
        # Si se proporcionan datos astrales, añadirlos
        if datos_astrales:
            archivos_unicos.update(datos_astrales)
        
        # Generar informe
        resultado = generar_y_enviar_informe_desde_agente(
            datos_cliente=datos_cliente,
            tipo_servicio=tipo_servicio,
            resumen_sesion=resumen_sesion,
            archivos_cartas=archivos_unicos
        )
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error en generar_informe_completo: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def procesar_informe_con_aspectos(datos_cliente, tipo_servicio, aspectos_data, resumen_sesion=""):
    """
    Procesar informe con datos de aspectos específicos
    """
    try:
        # Estructurar datos de aspectos para el template
        archivos_cartas = {
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'aspectos_natales': aspectos_data.get('aspectos_natales', []),
            'aspectos_progresiones': aspectos_data.get('aspectos_progresiones', []),
            'aspectos_transitos': aspectos_data.get('aspectos_transitos', []),
            'posiciones_natales': aspectos_data.get('posiciones_natales', {}),
            'imagenes_base64': aspectos_data.get('imagenes_base64', {}),
            'estadisticas': aspectos_data.get('estadisticas', {}),
            'duracion_minutos': 40
        }
        
        return generar_y_enviar_informe_desde_agente(
            datos_cliente=datos_cliente,
            tipo_servicio=tipo_servicio,
            resumen_sesion=resumen_sesion,
            archivos_cartas=archivos_cartas
        )
        
    except Exception as e:
        print(f"❌ Error en procesar_informe_con_aspectos: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# =======================================================================
# FUNCIÓN DE COMPATIBILIDAD PARA EMAILS (si se usa)
# =======================================================================

def enviar_informe_por_email(datos_cliente, archivo_pdf, tipo_servicio):
    """
    Enviar informe por email (función placeholder para compatibilidad)
    """
    try:
        print(f"📧 Enviando informe por email: {archivo_pdf}")
        
        # NOTA: Aquí iría la lógica de envío de email real
        # Por ahora es un placeholder que simula el envío
        
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
                'error': 'Archivo PDF no encontrado para envío'
            }
            
    except Exception as e:
        print(f"❌ Error enviando informe por email: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# =======================================================================
# ENDPOINT DE TEST PARA LA FUNCIÓN RECUPERADA
# =======================================================================

def test_funcion_desde_agente():
    """
    Test de la función generar_y_enviar_informe_desde_agente recuperada
    """
    try:
        # Datos de test
        datos_cliente_test = {
            'nombre': 'Cliente Test',
            'email': 'test@test.com',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        resumen_test = "Esta es una sesión de prueba para verificar que la función recuperada funciona correctamente."
        
        # Simular datos astrales
        archivos_test = {
            'imagenes_base64': {
                'carta_natal': 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzY2N2VlYSIvPjx0ZXh0IHg9IjE1MCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5DYXJ0YSBOYXRhbCBUZXN0PC90ZXh0Pjwvc3ZnPg=='
            },
            'aspectos_natales': [
                {'planeta1': 'Sol', 'aspecto': 'conjuncion', 'planeta2': 'Marte', 'orbe': 0.8},
                {'planeta1': 'Luna', 'aspecto': 'sextil', 'planeta2': 'Venus', 'orbe': 2.1}
            ],
            'estadisticas': {
                'total_aspectos_natal': 2,
                'total_aspectos_transitos': 0
            }
        }
        
        # Probar la función
        resultado = generar_y_enviar_informe_desde_agente(
            datos_cliente=datos_cliente_test,
            tipo_servicio='carta_astral_ia',
            resumen_sesion=resumen_test,
            archivos_cartas=archivos_test
        )
        
        return resultado
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error en test: {str(e)}',
            'traceback': traceback.format_exc()
        }