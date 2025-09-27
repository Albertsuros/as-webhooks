import os
import gc
from datetime import datetime
import pytz
from jinja2 import Template
import matplotlib
matplotlib.use('Agg')
import traceback
import subprocess
import shutil

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
    """Función actualizada para agentes"""
    return generar_pdf_completo_optimizado(datos_cliente, tipo_servicio, resumen_sesion)

def procesar_y_enviar_informe(datos_cliente, tipo_servicio, datos_astrales=None, resumen_sesion=""):
    """Función actualizada para main.py"""
    return generar_pdf_completo_optimizado(datos_cliente, tipo_servicio, resumen_sesion)

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
    """Función actualizada para usar sistema optimizado"""
    return generar_pdf_completo_optimizado(datos_cliente, especialidad, "Informe astrológico completo")
        
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
        
# =======================================================================
# 1. GENERAR CARTAS OPTIMIZADAS (TAMAÑO REDUCIDO)
# =======================================================================

def generar_cartas_astrales_optimizadas(datos_natales):
    """
    Generar cartas astrales con tamaño optimizado y archivos temporales
    """
    try:
        print("🔧 Generando cartas astrales OPTIMIZADAS...")
        
        # Extraer datos
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', '')
        
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_natal = (año, mes, dia, hora, minuto)
        else:
            raise ValueError("Formato fecha/hora incorrecto")
        
        coordenadas_ciudades = {
            'Madrid': (40.42, -3.70),
            'Barcelona': (41.39, 2.16),
            'Valencia': (39.47, -0.38),
        }
        
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        ciudad_nombre = 'Madrid, España'
        for ciudad, coords in coordenadas_ciudades.items():
            if ciudad.lower() in lugar_nacimiento.lower():
                lugar_coords = coords
                ciudad_nombre = f"{ciudad}, España"
                break
        
        # Crear directorio temporal para esta sesión
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_dir = f"temp_cartas_{timestamp}"
        os.makedirs(temp_dir, exist_ok=True)
        
        archivos_cartas = {}
        datos_aspectos = {}
        
        # =====================================
        # 1. CARTA NATAL OPTIMIZADA
        # =====================================
        print("📊 Generando Carta Natal optimizada...")
        try:
            from carta_natal import CartaAstralNatal
            import matplotlib.pyplot as plt
            
            # TAMAÑO OPTIMIZADO: 12x12 en lugar de 16x14
            carta_natal = CartaAstralNatal(figsize=(12, 12))
            
            aspectos_natal, posiciones_natal = carta_natal.crear_carta_astral_natal(
                fecha_natal=fecha_natal,
                lugar_natal=lugar_coords,
                ciudad_natal=ciudad_nombre,
                guardar_archivo=True,  # Guardar como archivo
                directorio_salida=temp_dir
            )
            
            # Buscar el archivo generado
            import glob
            archivos_png = glob.glob(f"{temp_dir}/*natal*.png")
            if not archivos_png:
                archivos_png = glob.glob(f"{temp_dir}/*.png")
            
            if archivos_png:
                archivo_carta_natal = archivos_png[0]
                # Renombrar para consistencia
                archivo_final = f"{temp_dir}/carta_natal_{timestamp}.png"
                shutil.move(archivo_carta_natal, archivo_final)
                archivos_cartas['carta_natal'] = archivo_final
            
            datos_aspectos['natal'] = {
                'aspectos': aspectos_natal,
                'posiciones': posiciones_natal
            }
            
            plt.close('all')  # Cerrar todas las figuras
            gc.collect()      # Limpiar memoria
            
            print(f"✅ Carta natal: {len(aspectos_natal)} aspectos, archivo: {archivos_cartas.get('carta_natal', 'No generado')}")
            
        except Exception as e:
            print(f"⚠️ Error en carta natal: {e}")
            datos_aspectos['natal'] = {'aspectos': [], 'posiciones': {}}
        
        # =====================================
        # 2. PROGRESIONES OPTIMIZADAS
        # =====================================
        print("📈 Generando Progresiones optimizadas...")
        try:
            from progresiones import CartaProgresiones
            from datetime import datetime as dt
            
            # TAMAÑO OPTIMIZADO
            carta_prog = CartaProgresiones(figsize=(12, 12))
            hoy = dt.now()
            edad_actual = (hoy.year - año) + (hoy.month - mes) / 12.0
            
            aspectos_prog, pos_natales, pos_prog, _, _ = carta_prog.crear_carta_progresiones(
                fecha_nacimiento=fecha_natal,
                edad_consulta=edad_actual,
                lugar_nacimiento=lugar_coords,
                lugar_actual=lugar_coords,
                ciudad_nacimiento=ciudad_nombre,
                ciudad_actual=ciudad_nombre,
                guardar_archivo=True,
                directorio_salida=temp_dir
            )
            
            # Buscar archivo de progresiones
            archivos_prog = glob.glob(f"{temp_dir}/*progres*.png")
            if archivos_prog:
                archivo_final = f"{temp_dir}/progresiones_{timestamp}.png"
                shutil.move(archivos_prog[0], archivo_final)
                archivos_cartas['progresiones'] = archivo_final
            
            datos_aspectos['progresiones'] = {
                'aspectos': aspectos_prog,
                'posiciones_natales': pos_natales,
                'posiciones_progresadas': pos_prog
            }
            
            plt.close('all')
            gc.collect()
            
            print(f"✅ Progresiones: {len(aspectos_prog)} aspectos, archivo: {archivos_cartas.get('progresiones', 'No generado')}")
            
        except Exception as e:
            print(f"⚠️ Error en progresiones: {e}")
            datos_aspectos['progresiones'] = {'aspectos': []}
        
        # =====================================
        # 3. TRÁNSITOS OPTIMIZADOS
        # =====================================
        print("🔄 Generando Tránsitos optimizados...")
        try:
            from transitos import CartaTransitos
            from datetime import datetime as dt
            
            # TAMAÑO OPTIMIZADO
            carta_trans = CartaTransitos(figsize=(12, 12))
            hoy = dt.now()
            fecha_consulta = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
            
            resultado = carta_trans.crear_carta_transitos(
                fecha_nacimiento=fecha_natal,
                fecha_transito=fecha_consulta,
                lugar_nacimiento=lugar_coords,
                guardar_archivo=True,
                directorio_salida=temp_dir
            )
            
            if resultado and len(resultado) >= 3:
                aspectos_trans, pos_natales, pos_transitos = resultado[:3]
                
                # Buscar archivo de tránsitos
                archivos_trans = glob.glob(f"{temp_dir}/*transit*.png")
                if not archivos_trans:
                    archivos_trans = glob.glob(f"{temp_dir}/*{timestamp[-6:]}*.png")  # Buscar por timestamp
                
                if archivos_trans:
                    archivo_final = f"{temp_dir}/transitos_{timestamp}.png"
                    shutil.move(archivos_trans[-1], archivo_final)  # Último archivo generado
                    archivos_cartas['transitos'] = archivo_final
                
                datos_aspectos['transitos'] = {
                    'aspectos': aspectos_trans,
                    'posiciones_natales': pos_natales,
                    'posiciones_transitos': pos_transitos
                }
                
                print(f"✅ Tránsitos: {len(aspectos_trans)} aspectos, archivo: {archivos_cartas.get('transitos', 'No generado')}")
            else:
                raise Exception("Resultado de tránsitos vacío")
                
            plt.close('all')
            gc.collect()
                
        except Exception as e:
            print(f"⚠️ Error en tránsitos: {e}")
            datos_aspectos['transitos'] = {'aspectos': []}
        
        # =====================================
        # COMPILAR DATOS COMPLETOS
        # =====================================
        aspectos_natales = datos_aspectos['natal']['aspectos']
        posiciones_natales = datos_aspectos['natal']['posiciones']
        aspectos_progresiones = datos_aspectos['progresiones']['aspectos']
        aspectos_transitos = datos_aspectos['transitos']['aspectos']
        
        estadisticas = {
            'total_aspectos_natal': len(aspectos_natales),
            'total_aspectos_progresiones': len(aspectos_progresiones),
            'total_aspectos_transitos': len(aspectos_transitos)
        }
        
        datos_completos = {
            # Datos principales
            'aspectos_natales': aspectos_natales,
            'posiciones_natales': posiciones_natales,
            'aspectos_progresiones': aspectos_progresiones,
            'aspectos_transitos': aspectos_transitos,
            'estadisticas': estadisticas,
            
            # Archivos de cartas
            'archivos_cartas': archivos_cartas,
            'temp_dir': temp_dir,
            
            # Metadatos
            'timestamp': timestamp,
            'metodo': 'archivos_temporales_optimizados',
            'datos_originales': datos_natales
        }
        
        print("✅ Cartas astrales OPTIMIZADAS generadas como archivos temporales")
        print(f"📁 Directorio temporal: {temp_dir}")
        print(f"📊 Archivos generados: {list(archivos_cartas.keys())}")
        
        return True, datos_completos
        
    except Exception as e:
        print(f"❌ Error en cartas optimizadas: {e}")
        traceback.print_exc()
        return False, None

# =======================================================================
# 2. GENERAR HTML CON RUTAS DE ARCHIVOS LOCALES
# =======================================================================

def generar_html_con_archivos_locales(datos_cliente, tipo_servicio, datos_cartas, resumen_sesion=""):
    """
    Generar HTML que usa archivos PNG locales (no base64)
    """
    try:
        zona = pytz.timezone('Europe/Madrid')
        ahora = datetime.now(zona)
        timestamp = datos_cartas.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        archivos_cartas = datos_cartas.get('archivos_cartas', {})
        
        # Template HTML con rutas de archivos
        template_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{datos_cliente.get('nombre', 'Cliente')} - Informe Astrológico - AS Cartastral</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
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
        }}
        .datos-personales {{
            background: #667eea;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .dato {{
            font-weight: bold;
            color: #FFD700;
        }}
        .carta-section {{
            margin: 40px 0;
            page-break-inside: avoid;
        }}
        .carta-section h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            text-align: center;
        }}
        .carta-imagen {{
            text-align: center;
            margin: 20px 0;
        }}
        .carta-imagen img {{
            max-width: 100%;
            height: auto;
            border: 2px solid #667eea;
            border-radius: 10px;
        }}
        .aspectos-section {{
            background: #f8f9ff;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}
        .aspectos-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        .aspecto-item {{
            background: white;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #e0e6ed;
            display: flex;
            justify-content: space-between;
            align-items: center;
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
        }}
        .estadisticas {{
            background: #e8f5e8;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #667eea;
            color: #666;
        }}
        @media print {{
            body {{ margin: 0; }}
            .container {{ max-width: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌟 Informe Astrológico Completo 🌟</h1>
            <h2>AS Cartastral - Análisis Personalizado</h2>
        </div>

        <div class="datos-personales">
            <h3>📋 Datos Personales</h3>
            <p><span class="dato">Nombre:</span> {datos_cliente.get('nombre', 'Cliente')}</p>
            <p><span class="dato">Email:</span> {datos_cliente.get('email', '')}</p>
            <p><span class="dato">Fecha de nacimiento:</span> {datos_cliente.get('fecha_nacimiento', '')}</p>
            <p><span class="dato">Hora de nacimiento:</span> {datos_cliente.get('hora_nacimiento', '')}</p>
            <p><span class="dato">Lugar de nacimiento:</span> {datos_cliente.get('lugar_nacimiento', '')}</p>
        </div>
"""
        
        # CARTA NATAL
        aspectos_natales = datos_cartas.get('aspectos_natales', [])
        if 'carta_natal' in archivos_cartas:
            template_html += f"""
        <div class="carta-section">
            <h2>🌅 Tu Carta Natal</h2>
            <div class="carta-imagen">
                <img src="{archivos_cartas['carta_natal']}" alt="Carta Natal">
            </div>
            <p>Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento.</p>
            
            <div class="aspectos-section">
                <h3>⭐ Aspectos Natales ({len(aspectos_natales)})</h3>
                <div class="aspectos-grid">
"""
            
            for aspecto in aspectos_natales[:15]:
                planeta1 = aspecto.get('planeta1', 'Planeta1')
                planeta2 = aspecto.get('planeta2', 'Planeta2')
                tipo_aspecto = aspecto.get('aspecto', 'aspecto')
                orbe = aspecto.get('orbe', 0)
                
                template_html += f"""
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{planeta1} {tipo_aspecto} {planeta2}</span>
                        <span class="aspecto-orbe">{orbe:.1f}°</span>
                    </div>
"""
            
            if len(aspectos_natales) > 15:
                template_html += f"""
                    <div style="grid-column: 1 / -1; text-align: center; color: #667eea; font-style: italic;">
                        + {len(aspectos_natales) - 15} aspectos adicionales
                    </div>
"""
            
            template_html += """
                </div>
            </div>
        </div>
"""
        
        # PROGRESIONES
        aspectos_progresiones = datos_cartas.get('aspectos_progresiones', [])
        if 'progresiones' in archivos_cartas:
            template_html += f"""
        <div class="carta-section">
            <h2>📈 Progresiones Secundarias</h2>
            <div class="carta-imagen">
                <img src="{archivos_cartas['progresiones']}" alt="Progresiones Secundarias">
            </div>
            <p>Las progresiones muestran tu evolución personal interna.</p>
            
            <div class="aspectos-section">
                <h3>🌱 Aspectos de Progresión ({len(aspectos_progresiones)})</h3>
                <div class="aspectos-grid">
"""
            
            for aspecto in aspectos_progresiones[:12]:
                planeta_progresion = aspecto.get('planeta_progresion', 'PlanetaProg')
                planeta_natal = aspecto.get('planeta_natal', 'PlanetaNatal')
                tipo = aspecto.get('tipo', 'aspecto')
                orbe = aspecto.get('orbe', 0)
                
                template_html += f"""
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{planeta_progresion} {tipo} {planeta_natal}</span>
                        <span class="aspecto-orbe">{orbe:.1f}°</span>
                    </div>
"""
            
            template_html += """
                </div>
            </div>
        </div>
"""
        
        # TRÁNSITOS
        aspectos_transitos = datos_cartas.get('aspectos_transitos', [])
        if 'transitos' in archivos_cartas:
            template_html += f"""
        <div class="carta-section">
            <h2>🔄 Tránsitos Actuales</h2>
            <div class="carta-imagen">
                <img src="{archivos_cartas['transitos']}" alt="Tránsitos Actuales">
            </div>
            <p>Los tránsitos planetarios actuales muestran las energías que están influyendo en tu vida ahora.</p>
            
            <div class="aspectos-section">
                <h3>⚡ Aspectos de Tránsito ({len(aspectos_transitos)})</h3>
                <div class="aspectos-grid">
"""
            
            for aspecto in aspectos_transitos[:12]:
                planeta_transito = aspecto.get('planeta_transito', 'PlanetaTrans')
                planeta_natal = aspecto.get('planeta_natal', 'PlanetaNatal')
                tipo = aspecto.get('tipo', 'aspecto')
                orbe = aspecto.get('orbe', 0)
                
                template_html += f"""
                    <div class="aspecto-item">
                        <span class="aspecto-planetas">{planeta_transito} {tipo} {planeta_natal}</span>
                        <span class="aspecto-orbe">{orbe:.1f}°</span>
                    </div>
"""
            
            template_html += """
                </div>
            </div>
        </div>
"""
        
        # ESTADÍSTICAS
        estadisticas = datos_cartas.get('estadisticas', {})
        template_html += f"""
        <div class="estadisticas">
            <h3>📊 Resumen Estadístico</h3>
            <p><strong>Total de aspectos natales:</strong> {estadisticas.get('total_aspectos_natal', 0)}</p>
            <p><strong>Total de aspectos de progresión:</strong> {estadisticas.get('total_aspectos_progresiones', 0)}</p>
            <p><strong>Total de aspectos de tránsito:</strong> {estadisticas.get('total_aspectos_transitos', 0)}</p>
        </div>
"""
        
        # RESUMEN DE SESIÓN
        if resumen_sesion:
            template_html += f"""
        <div style="background: #f8f9ff; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>📞 Resumen de tu Sesión</h2>
            <p>{resumen_sesion}</p>
        </div>
"""
        
        template_html += f"""
        <div class="footer">
            <p><strong>Fecha de generación:</strong> {ahora.strftime("%d/%m/%Y")} a las {ahora.strftime("%H:%M:%S")}</p>
            <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
        </div>
    </div>
</body>
</html>"""
        
        # Guardar HTML
        archivo_html = f"templates/informe_cartas_{tipo_servicio}_{timestamp}.html"
        os.makedirs('templates', exist_ok=True)
        
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(template_html)
        
        print(f"✅ HTML con archivos locales generado: {archivo_html}")
        return archivo_html
        
    except Exception as e:
        print(f"❌ Error generando HTML con archivos: {e}")
        traceback.print_exc()
        return None

# =======================================================================
# 3. CONVERTIR A PDF CON WKHTMLTOPDF (ALTERNATIVA A PLAYWRIGHT)
# =======================================================================

def convertir_html_a_pdf_wkhtmltopdf(archivo_html, archivo_pdf):
    """
    Convertir HTML a PDF usando wkhtmltopdf (más robusto para imágenes)
    """
    try:
        print(f"🔄 Convirtiendo con wkhtmltopdf: {archivo_html} -> {archivo_pdf}")
        
        # Crear directorio de salida
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        # Comando wkhtmltopdf
        comando = [
            'wkhtmltopdf',
            '--page-size', 'A4',
            '--margin-top', '1cm',
            '--margin-right', '1cm',
            '--margin-bottom', '1cm',
            '--margin-left', '1cm',
            '--enable-local-file-access',
            '--print-media-type',
            archivo_html,
            archivo_pdf
        ]
        
        # Ejecutar comando
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=60)
        
        if resultado.returncode == 0 and os.path.exists(archivo_pdf):
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado con wkhtmltopdf: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            print(f"❌ Error en wkhtmltopdf: {resultado.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout en wkhtmltopdf")
        return False
    except FileNotFoundError:
        print("❌ wkhtmltopdf no está instalado, usando Playwright como fallback")
        return convertir_html_a_pdf_playwright_fallback(archivo_html, archivo_pdf)
    except Exception as e:
        print(f"❌ Error en wkhtmltopdf: {e}")
        return False

def convertir_html_a_pdf_playwright_fallback(archivo_html, archivo_pdf):
    """
    Fallback a Playwright si wkhtmltopdf no está disponible
    """
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Leer HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            page.set_content(html_content)
            page.wait_for_load_state('domcontentloaded')
            
            page.pdf(
                path=archivo_pdf,
                format='A4',
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                print_background=True
            )
            
            browser.close()
        
        if os.path.exists(archivo_pdf):
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado con Playwright (fallback): {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error en Playwright fallback: {e}")
        return False

# =======================================================================
# 4. FUNCIÓN PRINCIPAL COMPLETA
# =======================================================================

def generar_pdf_completo_optimizado(datos_cliente, tipo_servicio, resumen_sesion=""):
    """
    Función principal: generar PDF completo con cartas optimizadas
    """
    try:
        print(f"🚀 Generando PDF completo optimizado: {tipo_servicio}")
        
        # PASO 1: Generar cartas optimizadas como archivos
        exito_cartas, datos_cartas = generar_cartas_astrales_optimizadas(datos_cliente)
        
        if not exito_cartas or not datos_cartas:
            return {
                'success': False,
                'error': 'No se pudieron generar las cartas astrales'
            }
        
        # PASO 2: Generar HTML con rutas de archivos
        archivo_html = generar_html_con_archivos_locales(
            datos_cliente, tipo_servicio, datos_cartas, resumen_sesion
        )
        
        if not archivo_html:
            return {
                'success': False,
                'error': 'No se pudo generar el HTML'
            }
        
        # PASO 3: Convertir a PDF
        timestamp = datos_cartas.get('timestamp')
        archivo_pdf = f"informes/informe_completo_{tipo_servicio}_{timestamp}.pdf"
        
        # Intentar wkhtmltopdf primero, luego Playwright
        pdf_success = convertir_html_a_pdf_wkhtmltopdf(archivo_html, archivo_pdf)
        
        # PASO 4: Limpiar archivos temporales (opcional - mantener por una semana)
        temp_dir = datos_cartas.get('temp_dir')
        if temp_dir and os.path.exists(temp_dir):
            # Por ahora mantener archivos - se pueden limpiar con cron job
            print(f"📁 Archivos temporales mantenidos en: {temp_dir}")
        
        if pdf_success:
            return {
                'success': True,
                'archivo_html': archivo_html,
                'archivo_pdf': archivo_pdf,
                'mensaje': 'PDF completo generado con cartas optimizadas',
                'aspectos_incluidos': {
                    'natal': len(datos_cartas.get('aspectos_natales', [])),
                    'progresiones': len(datos_cartas.get('aspectos_progresiones', [])),
                    'transitos': len(datos_cartas.get('aspectos_transitos', []))
                },
                'metodo': 'cartas_optimizadas_archivos_temporales',
                'temp_dir': temp_dir,
                'timestamp': timestamp
            }
        else:
            return {
                'success': False,
                'error': 'No se pudo convertir HTML a PDF',
                'archivo_html': archivo_html,
                'temp_dir': temp_dir
            }
            
    except Exception as e:
        print(f"❌ Error en PDF completo optimizado: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }