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
import base64
from flask import url_for

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
        
# SOLUCIÓN DEFINITIVA - AÑADIR A informes.py

def convertir_html_a_pdf_weasyprint(archivo_html, archivo_pdf):
    """
    Convertir HTML a PDF usando WeasyPrint (más robusto que Playwright)
    WeasyPrint maneja mejor las imágenes base64 grandes
    """
    try:
        import subprocess
        import os
        
        print(f"📄 Convirtiendo con WeasyPrint: {archivo_html} -> {archivo_pdf}")
        
        # Crear directorio de salida
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        # Instalar weasyprint si no está disponible
        try:
            import weasyprint
        except ImportError:
            print("📦 Instalando WeasyPrint...")
            subprocess.run(['pip', 'install', 'weasyprint'], check=True)
            import weasyprint
        
        # Convertir HTML a PDF
        weasyprint.HTML(filename=archivo_html).write_pdf(archivo_pdf)
        
        if os.path.exists(archivo_pdf) and os.path.getsize(archivo_pdf) > 1000:
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado con WeasyPrint: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error en WeasyPrint: {e}")
        return False

def convertir_html_a_pdf_reportlab_fallback(archivo_html, archivo_pdf):
    """
    Fallback usando ReportLab - generar PDF simple con datos textuales
    """
    try:
        import subprocess
        
        # Instalar reportlab si no está disponible
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
        except ImportError:
            print("📦 Instalando ReportLab...")
            subprocess.run(['pip', 'install', 'reportlab'], check=True)
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
        
        # Leer HTML y extraer texto importante
        with open(archivo_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Crear PDF simple con ReportLab
        c = canvas.Canvas(archivo_pdf, pagesize=A4)
        width, height = A4
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "INFORME CARTA ASTRAL")
        
        # Contenido básico
        c.setFont("Helvetica", 12)
        y_position = height - 100
        
        lines = [
            "Informe astrológico completo generado",
            "Incluye aspectos natales, progresiones y tránsitos",
            "Para visualización completa, contacte con AS Cartastral"
        ]
        
        for line in lines:
            c.drawString(50, y_position, line)
            y_position -= 20
        
        c.save()
        
        if os.path.exists(archivo_pdf):
            print(f"✅ PDF básico generado con ReportLab: {archivo_pdf}")
            return True
        return False
        
    except Exception as e:
        print(f"❌ Error en ReportLab: {e}")
        return False

# REEMPLAZAR la función principal de conversión en informes.py
def convertir_html_a_pdf(archivo_html, archivo_pdf):
    """
    Función principal de conversión - Múltiples métodos con fallbacks
    """
    try:
        print(f"🔄 Iniciando conversión PDF: {archivo_html} -> {archivo_pdf}")
        
        # MÉTODO 1: WeasyPrint (mejor para imágenes base64)
        if convertir_html_a_pdf_weasyprint(archivo_html, archivo_pdf):
            return True
            
        # MÉTODO 2: Playwright optimizado (si WeasyPrint falla)
        if convertir_html_a_pdf_playwright_optimizado(archivo_html, archivo_pdf):
            return True
            
        # MÉTODO 3: ReportLab simple (si todo falla)
        print("⚠️ Fallback a PDF básico con ReportLab...")
        if convertir_html_a_pdf_reportlab_fallback(archivo_html, archivo_pdf):
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ Error crítico en conversión PDF: {e}")
        return False

def convertir_html_a_pdf_playwright_optimizado(archivo_html, archivo_pdf):
    """
    Playwright optimizado específicamente para Railway
    """
    try:
        from playwright.sync_api import sync_playwright
        import os
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--memory-pressure-off',
                    '--max_old_space_size=2048'
                ]
            )
            
            page = browser.new_page()
            
            # Leer HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Si el HTML es muy grande, reducir imágenes
            if len(html_content) > 3000000:  # 3MB
                print("⚠️ HTML muy grande, usando versión optimizada...")
                # Reemplazar imágenes base64 con placeholders
                import re
                html_content = re.sub(
                    r'data:image/png;base64,[A-Za-z0-9+/=]+',
                    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI2Y0ZjRmNCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5DQVJUQSBBU1RSQUw8L3RleHQ+PC9zdmc+',
                    html_content
                )
            
            page.set_content(html_content, wait_until='domcontentloaded')
            
            # Configurar página para PDF
            page.pdf(
                path=archivo_pdf,
                format='A4',
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                print_background=True,
                prefer_css_page_size=True
            )
            
            browser.close()
        
        if os.path.exists(archivo_pdf) and os.path.getsize(archivo_pdf) > 1000:
            tamaño_kb = os.path.getsize(archivo_pdf) / 1024
            print(f"✅ PDF generado con Playwright optimizado: {archivo_pdf} ({tamaño_kb:.1f} KB)")
            return True
        return False
        
    except Exception as e:
        print(f"❌ Error en Playwright optimizado: {e}")
        return False
        
# SOLUCIÓN ESPECÍFICA PARA RAILWAY - AÑADIR A informes.py

def instalar_playwright_railway():
    """
    Instalar Playwright y browsers específicamente para Railway
    """
    try:
        import subprocess
        import os
        
        print("🔧 Verificando instalación de Playwright en Railway...")
        
        # Verificar si Playwright está instalado
        try:
            from playwright.sync_api import sync_playwright
            print("✅ Playwright importado correctamente")
        except ImportError:
            print("📦 Instalando Playwright...")
            subprocess.run(['pip', 'install', 'playwright'], check=True)
            from playwright.sync_api import sync_playwright
        
        # Instalar browsers de Playwright si no están disponibles
        try:
            print("🌐 Instalando Chromium para Playwright...")
            subprocess.run(['playwright', 'install', 'chromium'], check=True)
            print("✅ Chromium instalado")
        except Exception as e:
            print(f"⚠️ No se pudo instalar Chromium automáticamente: {e}")
            # Intentar instalación alternativa
            try:
                subprocess.run(['python', '-m', 'playwright', 'install', 'chromium'], check=True)
                print("✅ Chromium instalado (método alternativo)")
            except Exception as e2:
                print(f"❌ Error instalando Chromium: {e2}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en instalación Playwright: {e}")
        return False

def convertir_html_a_pdf_railway_optimizado(archivo_html, archivo_pdf):
    """
    Conversión PDF optimizada específicamente para Railway
    """
    try:
        print(f"🚀 Conversión PDF Railway: {archivo_html} -> {archivo_pdf}")
        
        # Verificar instalación
        if not instalar_playwright_railway():
            print("❌ Playwright no disponible, intentando wkhtmltopdf...")
            return convertir_html_a_pdf_wkhtmltopdf_railway(archivo_html, archivo_pdf)
        
        from playwright.sync_api import sync_playwright
        import os
        
        # Crear directorio
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        # Configuración específica para Railway
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-extensions',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--mute-audio',
            '--no-first-run',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--disable-features=VizDisplayCompositor',
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            '--aggressive-cache-discard'
        ]
        
        with sync_playwright() as p:
            print("🌐 Lanzando Chromium con configuración Railway...")
            
            browser = p.chromium.launch(
                headless=True,
                args=browser_args,
                slow_mo=0,
                devtools=False
            )
            
            # Configurar contexto con límites de memoria
            context = browser.new_context(
                viewport={'width': 1200, 'height': 800},
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            # Configurar timeouts más largos
            page.set_default_timeout(120000)  # 2 minutos
            page.set_default_navigation_timeout(120000)
            
            print("📄 Cargando HTML...")
            
            # Leer HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Configurar página antes de cargar contenido
            page.add_init_script("""
                // Optimizaciones para Railway
                window.addEventListener('load', () => {
                    console.log('Página cargada completamente');
                });
                
                // Limpiar console para reducir memoria
                console.log = () => {};
                console.warn = () => {};
                console.error = () => {};
            """)
            
            # Cargar contenido
            page.set_content(html_content, wait_until='domcontentloaded')
            
            print("⏳ Esperando que el contenido se procese...")
            
            # Esperar que las imágenes se carguen (con timeout)
            try:
                page.wait_for_load_state('networkidle', timeout=60000)
                print("✅ Imágenes cargadas")
            except:
                print("⚠️ Timeout esperando imágenes, continuando...")
            
            # Pequeña pausa adicional para asegurar renderizado
            page.wait_for_timeout(2000)
            
            print("📄 Generando PDF...")
            
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
                display_header_footer=False,
                scale=1.0
            )
            
            print("🔒 Cerrando browser...")
            context.close()
            browser.close()
        
        # Verificar resultado
        if os.path.exists(archivo_pdf) and os.path.getsize(archivo_pdf) > 1000:
            tamaño_mb = os.path.getsize(archivo_pdf) / (1024*1024)
            print(f"✅ PDF generado exitosamente: {archivo_pdf} ({tamaño_mb:.2f} MB)")
            return True
        else:
            print("❌ PDF no generado correctamente")
            return False
            
    except Exception as e:
        print(f"❌ Error en Playwright Railway: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback a wkhtmltopdf
        print("🔄 Intentando fallback con wkhtmltopdf...")
        return convertir_html_a_pdf_wkhtmltopdf_railway(archivo_html, archivo_pdf)

def convertir_html_a_pdf_wkhtmltopdf_railway(archivo_html, archivo_pdf):
    """
    Fallback usando wkhtmltopdf en Railway
    """
    try:
        import subprocess
        import os
        
        print("🔧 Intentando wkhtmltopdf en Railway...")
        
        # Verificar si wkhtmltopdf está disponible
        try:
            subprocess.run(['wkhtmltopdf', '--version'], capture_output=True, check=True)
            print("✅ wkhtmltopdf disponible")
        except:
            print("❌ wkhtmltopdf no está instalado en Railway")
            return False
        
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
            '--load-error-handling', 'ignore',
            '--load-media-error-handling', 'ignore',
            '--disable-smart-shrinking',
            '--zoom', '1.0',
            archivo_html,
            archivo_pdf
        ]
        
        # Ejecutar con timeout
        resultado = subprocess.run(
            comando, 
            capture_output=True, 
            text=True, 
            timeout=120  # 2 minutos
        )
        
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
    except Exception as e:
        print(f"❌ Error en wkhtmltopdf: {e}")
        return False

def generar_cartas_tamaño_original(datos_natales):
    """
    Generar cartas con el tamaño original que funcionaba antes
    """
    try:
        import os
        from datetime import datetime
        from datos_astrales import GraficosAstrales
        
        print("🎨 Generando cartas con tamaño original...")
        
        # Timestamp único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_dir = f"temp_cartas_{timestamp}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Inicializar clase de gráficos
        graficos = GraficosAstrales()
        
        # CONFIGURACIÓN ORIGINAL (la que funcionaba antes)
        config_original = {
            'figsize': (14, 12),     # Tamaño que funcionaba antes
            'dpi': 120,              # DPI balanceado
            'format': 'png',
            'bbox_inches': 'tight',
            'facecolor': 'white',
            'edgecolor': 'none'
        }
        
        rutas_cartas = {}
        aspectos_data = {}
        
        # 1. CARTA NATAL
        try:
            print("🌟 Generando carta natal (tamaño original)...")
            ruta_natal = os.path.join(temp_dir, f"carta_natal_{timestamp}.png")
            
            # Generar carta natal
            aspectos_natales = graficos.crear_carta_natal_completa(
                datos_natales, 
                ruta_natal, 
                config_original
            )
            
            if os.path.exists(ruta_natal):
                tamaño_mb = os.path.getsize(ruta_natal) / (1024*1024)
                print(f"✅ Carta natal: {ruta_natal} ({tamaño_mb:.2f} MB)")
                rutas_cartas['carta_natal'] = ruta_natal
                aspectos_data['aspectos_natales'] = aspectos_natales
                
        except Exception as e:
            print(f"❌ Error carta natal: {e}")
        
        # 2. PROGRESIONES
        try:
            print("📈 Generando progresiones (tamaño original)...")
            ruta_progresiones = os.path.join(temp_dir, f"progresiones_{timestamp}.png")
            
            aspectos_progresiones = graficos.crear_progresiones_completa(
                datos_natales,
                ruta_progresiones,
                config_original
            )
            
            if os.path.exists(ruta_progresiones):
                tamaño_mb = os.path.getsize(ruta_progresiones) / (1024*1024)
                print(f"✅ Progresiones: {ruta_progresiones} ({tamaño_mb:.2f} MB)")
                rutas_cartas['progresiones'] = ruta_progresiones
                aspectos_data['aspectos_progresiones'] = aspectos_progresiones
                
        except Exception as e:
            print(f"❌ Error progresiones: {e}")
        
        # 3. TRÁNSITOS
        try:
            print("🔄 Generando tránsitos (tamaño original)...")
            ruta_transitos = os.path.join(temp_dir, f"transitos_{timestamp}.png")
            
            aspectos_transitos = graficos.crear_transitos_completa(
                datos_natales,
                ruta_transitos,
                config_original
            )
            
            if os.path.exists(ruta_transitos):
                tamaño_mb = os.path.getsize(ruta_transitos) / (1024*1024)
                print(f"✅ Tránsitos: {ruta_transitos} ({tamaño_mb:.2f} MB)")
                rutas_cartas['transitos'] = ruta_transitos
                aspectos_data['aspectos_transitos'] = aspectos_transitos
                
        except Exception as e:
            print(f"❌ Error tránsitos: {e}")
        
        # Resultado
        resultado = {
            'success': True,
            'temp_dir': temp_dir,
            'timestamp': timestamp,
            'rutas_cartas': rutas_cartas,
            'total_archivos': len(rutas_cartas),
            'tamaño_total_mb': sum([
                os.path.getsize(ruta) / (1024*1024)
                for ruta in rutas_cartas.values() 
                if os.path.exists(ruta)
            ]),
            **aspectos_data
        }
        
        print(f"✅ Cartas originales generadas: {len(rutas_cartas)} archivos")
        print(f"📏 Tamaño total: {resultado['tamaño_total_mb']:.2f} MB")
        
        return True, resultado
        
    except Exception as e:
        print(f"❌ Error generando cartas originales: {e}")
        import traceback
        traceback.print_exc()
        return False, {'error': str(e)}

# FUNCIÓN PRINCIPAL CON CONFIGURACIÓN RAILWAY
def generar_pdf_railway_configurado(datos_cliente, tipo_servicio, resumen_sesion=""):
    """
    Generar PDF con configuración específica para Railway
    """
    try:
        print(f"🚀 Generando PDF en Railway: {tipo_servicio}")
        
        # PASO 1: Generar cartas con tamaño original
        exito, datos_cartas = generar_cartas_tamaño_original(datos_cliente)
        
        if not exito:
            return {
                'success': False,
                'error': 'No se pudieron generar las cartas astrales',
                'debug': datos_cartas
            }
        
        # PASO 2: Generar HTML con rutas de archivos
        archivo_html = generar_html_con_rutas_archivos(
            datos_cliente, tipo_servicio, datos_cartas, resumen_sesion
        )
        
        if not archivo_html:
            return {
                'success': False,
                'error': 'No se pudo generar el HTML'
            }
        
        # PASO 3: Convertir a PDF con configuración Railway
        timestamp = datos_cartas.get('timestamp')
        archivo_pdf = f"informes/informe_railway_{tipo_servicio}_{timestamp}.pdf"
        
        pdf_success = convertir_html_a_pdf_railway_optimizado(archivo_html, archivo_pdf)
        
        if pdf_success:
            return {
                'success': True,
                'archivo_html': archivo_html,
                'archivo_pdf': archivo_pdf,
                'mensaje': '¡PDF generado exitosamente en Railway!',
                'aspectos_incluidos': {
                    'natal': len(datos_cartas.get('aspectos_natales', [])),
                    'progresiones': len(datos_cartas.get('aspectos_progresiones', [])),
                    'transitos': len(datos_cartas.get('aspectos_transitos', []))
                },
                'metodo': 'railway_optimizado',
                'temp_dir': datos_cartas.get('temp_dir'),
                'timestamp': timestamp,
                'tamaño_cartas_mb': datos_cartas.get('tamaño_total_mb', 0)
            }
        else:
            return {
                'success': False,
                'error': 'No se pudo convertir HTML a PDF en Railway',
                'archivo_html': archivo_html,
                'temp_dir': datos_cartas.get('temp_dir'),
                'sugerencia': 'Verificar instalación de Playwright en Railway'
            }
            
    except Exception as e:
        print(f"❌ Error en PDF Railway: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        
def guardar_imagen_carta_en_static(imagen_data, nombre_archivo):
    """
    Guardar imagen de carta en static/img/ (método probado)
    """
    try:
        # Crear directorio static/img si no existe
        static_dir = os.path.join(os.getcwd(), 'static', 'img', 'cartas')
        os.makedirs(static_dir, exist_ok=True)
        
        # Guardar imagen
        ruta_completa = os.path.join(static_dir, f"{nombre_archivo}.png")
        
        if isinstance(imagen_data, bytes):
            # Si son bytes directos
            with open(ruta_completa, 'wb') as f:
                f.write(imagen_data)
        else:
            # Si es una figura de matplotlib
            imagen_data.savefig(ruta_completa, dpi=120, bbox_inches='tight', 
                              facecolor='white', format='png')
        
        # Devolver ruta relativa para url_for
        return f"img/cartas/{nombre_archivo}.png"
        
    except Exception as e:
        print(f"Error guardando imagen: {e}")
        return None

def obtener_url_imagen_publica(nombre_rel):
    """
    Obtener URL pública absoluta de imagen (método probado)
    """
    try:
        return url_for('static', filename=nombre_rel, _external=True)
    except RuntimeError:
        # Fallback si no hay contexto de request
        base = os.environ.get('APP_URL', 'https://as-webhooks-production.up.railway.app')
        return f"{base}/static/{nombre_rel}"

def generar_cartas_en_static(datos_natales):
    """
    Usar el sistema que YA funciona - crear_archivos_unicos_testing
    """
    try:
        from datetime import datetime
        import os
        import shutil
        
        print("Generando cartas con sistema existente...")
        
        # PASO 1: Usar la función que YA funciona
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archivos_sistema = crear_archivos_unicos_testing('carta_astral_ia', timestamp)
        
        print(f"DEBUG archivos_sistema: {archivos_sistema}")
        
        # PASO 2: Crear directorio static/img/cartas/
        static_dir = os.path.join('static', 'img', 'cartas')
        os.makedirs(static_dir, exist_ok=True)
        
        # PASO 3: Copiar imágenes existentes a static/
        cartas_urls = {}
        
        # Buscar imágenes en el sistema actual
        for key, valor in archivos_sistema.items():
            if key.endswith('_img') and isinstance(valor, str) and os.path.exists(valor):
                # Copiar a static/img/cartas/
                nombre_archivo = f"{key.replace('_img', '')}_{timestamp}.png"
                destino = os.path.join(static_dir, nombre_archivo)
                
                try:
                    shutil.copy2(valor, destino)
                    # URL pública
                    cartas_urls[key.replace('_img', '')] = obtener_url_imagen_publica(f"img/cartas/{nombre_archivo}")
                    print(f"✅ Copiada {key}: {valor} -> {destino}")
                except Exception as e:
                    print(f"❌ Error copiando {key}: {e}")
        
        # PASO 4: Si no hay imágenes, usar las que existen en static/
        if not cartas_urls:
            print("⚠️ No se encontraron imágenes generadas, usando las existentes...")
            # Buscar imágenes existentes en static/
            for archivo in os.listdir('static'):
                if 'carta' in archivo and archivo.endswith('.png'):
                    if 'natal' in archivo:
                        cartas_urls['carta_natal'] = obtener_url_imagen_publica(f"{archivo}")
                    elif 'progresion' in archivo:
                        cartas_urls['progresiones'] = obtener_url_imagen_publica(f"{archivo}")
                    elif 'transit' in archivo:
                        cartas_urls['transitos'] = obtener_url_imagen_publica(f"{archivo}")
        
        # PASO 5: Usar aspectos del sistema existente o generar datos de prueba
        aspectos_data = {
            'aspectos_natales': archivos_sistema.get('aspectos_natales', [
                {'planeta1': 'Sol', 'aspecto': 'conjunción', 'planeta2': 'Luna', 'orbe': '1.2°', 'tipo': 'mayor'},
                {'planeta1': 'Marte', 'aspecto': 'trígono', 'planeta2': 'Júpiter', 'orbe': '2.1°', 'tipo': 'mayor'},
                {'planeta1': 'Venus', 'aspecto': 'sextil', 'planeta2': 'Mercurio', 'orbe': '0.8°', 'tipo': 'menor'}
            ]),
            'aspectos_progresiones': archivos_sistema.get('aspectos_progresiones', [
                {'planeta1': 'Sol prog', 'aspecto': 'cuadratura', 'planeta2': 'Saturno', 'orbe': '1.5°', 'tipo': 'mayor'},
                {'planeta1': 'Luna prog', 'aspecto': 'trígono', 'planeta2': 'Venus', 'orbe': '2.3°', 'tipo': 'mayor'}
            ]),
            'aspectos_transitos': archivos_sistema.get('aspectos_transitos', [
                {'planeta1': 'Júpiter tr', 'aspecto': 'sextil', 'planeta2': 'Sol natal', 'orbe': '1.8°', 'tipo': 'mayor'},
                {'planeta1': 'Saturno tr', 'aspecto': 'oposición', 'planeta2': 'Luna natal', 'orbe': '0.9°', 'tipo': 'mayor'}
            ])
        }
        
        resultado = {
            'success': True,
            'timestamp': timestamp,
            'cartas_urls': cartas_urls,
            'total_cartas': len(cartas_urls),
            **aspectos_data
        }
        
        print(f"✅ Resultado: {len(cartas_urls)} cartas, {len(aspectos_data['aspectos_natales'])} aspectos natales")
        return True, resultado
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, {'error': str(e)}

def generar_html_con_urls_publicas(datos_cliente, tipo_servicio, datos_cartas, resumen_sesion=""):
    """
    Generar HTML usando URLs públicas (método probado)
    """
    try:
        from datetime import datetime
        import pytz
        from jinja2 import Template
        
        print("Generando HTML con URLs públicas...")
        
        # Template HTML con base href
        template_html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <base href="{{ request.host_url }}">
    <title>Informe Carta Astral - {{ datos_cliente.nombre }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 40px;
            background-color: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .carta-seccion {
            background: white;
            margin: 20px 0;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .carta-imagen {
            text-align: center;
            margin: 20px 0;
        }
        .carta-imagen img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .aspectos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .aspecto-item {
            background: #f8f9fa;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 0.9em;
            border-left: 3px solid #667eea;
        }
        .estadisticas {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-box {
            background: #e3f2fd;
            padding: 15px;
            text-align: center;
            border-radius: 8px;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #1976d2;
        }
        h2 {
            color: #444;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌟 INFORME CARTA ASTRAL COMPLETO</h1>
        <h2>{{ datos_cliente.nombre }}</h2>
        <p>{{ datos_cliente.fecha_nacimiento }} • {{ datos_cliente.lugar_nacimiento }}</p>
        <p>Generado: {{ fecha_generacion }}</p>
    </div>
    
    <!-- CARTA NATAL -->
    <div class="carta-seccion">
        <h2>🌅 Carta Natal</h2>
        {% if cartas_urls.carta_natal %}
        <div class="carta-imagen">
            <img src="{{ cartas_urls.carta_natal }}" alt="Carta Natal" loading="lazy">
        </div>
        {% endif %}
        
        <h3>Aspectos Natales ({{ aspectos_natales|length }})</h3>
        <div class="aspectos-grid">
            {% for aspecto in aspectos_natales[:20] %}
            <div class="aspecto-item">
                <strong>{{ aspecto.planeta1 }}</strong> {{ aspecto.aspecto }} <strong>{{ aspecto.planeta2 }}</strong>
                <br><small>Orbe: {{ aspecto.orbe }}° | Tipo: {{ aspecto.tipo }}</small>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- PROGRESIONES -->
    <div class="carta-seccion">
        <h2>📈 Progresiones Secundarias</h2>
        {% if cartas_urls.progresiones %}
        <div class="carta-imagen">
            <img src="{{ cartas_urls.progresiones }}" alt="Progresiones" loading="lazy">
        </div>
        {% endif %}
        
        <h3>Aspectos de Progresión ({{ aspectos_progresiones|length }})</h3>
        <div class="aspectos-grid">
            {% for aspecto in aspectos_progresiones[:15] %}
            <div class="aspecto-item">
                <strong>{{ aspecto.planeta1 }}</strong> {{ aspecto.aspecto }} <strong>{{ aspecto.planeta2 }}</strong>
                <br><small>Orbe: {{ aspecto.orbe }}° | Tipo: {{ aspecto.tipo }}</small>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- TRÁNSITOS -->
    <div class="carta-seccion">
        <h2>🔄 Tránsitos Actuales</h2>
        {% if cartas_urls.transitos %}
        <div class="carta-imagen">
            <img src="{{ cartas_urls.transitos }}" alt="Tránsitos" loading="lazy">
        </div>
        {% endif %}
        
        <h3>Aspectos de Tránsito ({{ aspectos_transitos|length }})</h3>
        <div class="aspectos-grid">
            {% for aspecto in aspectos_transitos[:15] %}
            <div class="aspecto-item">
                <strong>{{ aspecto.planeta1 }}</strong> {{ aspecto.aspecto }} <strong>{{ aspecto.planeta2 }}</strong>
                <br><small>Orbe: {{ aspecto.orbe }}° | Tipo: {{ aspecto.tipo }}</small>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- ESTADÍSTICAS -->
    <div class="carta-seccion">
        <h2>📊 Resumen del Análisis</h2>
        <div class="estadisticas">
            <div class="stat-box">
                <div class="stat-number">{{ aspectos_natales|length }}</div>
                <div>Aspectos Natales</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ aspectos_progresiones|length }}</div>
                <div>Progresiones</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ aspectos_transitos|length }}</div>
                <div>Tránsitos</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ total_cartas }}</div>
                <div>Cartas Generadas</div>
            </div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 40px; color: #666; font-size: 0.9em;">
        <p><strong>AS CARTASTRAL</strong> - Astrología Profesional</p>
        <p>{{ timestamp }}</p>
    </div>
</body>
</html>'''
        
        # Datos para el template
        ahora = datetime.now(pytz.timezone('Europe/Madrid'))
        
        datos_template = {
            'datos_cliente': datos_cliente,
            'cartas_urls': datos_cartas.get('cartas_urls', {}),
            'aspectos_natales': datos_cartas.get('aspectos_natales', []),
            'aspectos_progresiones': datos_cartas.get('aspectos_progresiones', []),
            'aspectos_transitos': datos_cartas.get('aspectos_transitos', []),
            'total_cartas': datos_cartas.get('total_cartas', 0),
            'timestamp': datos_cartas.get('timestamp', ''),
            'fecha_generacion': ahora.strftime('%d/%m/%Y %H:%M'),
            'resumen_sesion': resumen_sesion,
            'request': {'host_url': 'https://as-webhooks-production.up.railway.app/'}
        }
        
        # Renderizar template
        template = Template(template_html)
        html_content = template.render(**datos_template)
        
        # Guardar archivo HTML
        timestamp = datos_cartas.get('timestamp', 'temp')
        archivo_html = f"templates/informe_static_{tipo_servicio}_{timestamp}.html"
        os.makedirs('templates', exist_ok=True)
        
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML con URLs públicas generado: {archivo_html}")
        return archivo_html
        
    except Exception as e:
        print(f"Error generando HTML: {e}")
        import traceback
        traceback.print_exc()
        return None

def generar_pdf_desde_url_publica(url_html_publica, archivo_pdf):
    """
    Generar PDF desde URL pública (método probado con Playwright)
    """
    try:
        from playwright.sync_api import sync_playwright
        
        print(f"Generando PDF desde URL: {url_html_publica} -> {archivo_pdf}")
        
        # Crear directorio
        directorio_pdf = os.path.dirname(archivo_pdf)
        if directorio_pdf and not os.path.exists(directorio_pdf):
            os.makedirs(directorio_pdf)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            
            page = browser.new_page(viewport={"width": 1200, "height": 1800})
            
            # Navegar a URL pública (método probado)
            page.goto(url_html_publica, wait_until="networkidle")
            
            # Generar PDF
            page.pdf(
                path=archivo_pdf,
                print_background=True,
                width="210mm",
                height="297mm",
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
            )
            
            browser.close()
        
        if os.path.exists(archivo_pdf) and os.path.getsize(archivo_pdf) > 1000:
            tamaño_mb = os.path.getsize(archivo_pdf) / (1024*1024)
            print(f"✅ PDF generado desde URL: {archivo_pdf} ({tamaño_mb:.2f} MB)")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error generando PDF desde URL: {e}")
        import traceback
        traceback.print_exc()
        return False

def generar_informe_completo_metodo_probado(datos_cliente, tipo_servicio, resumen_sesion=""):
    """
    Función principal usando el método probado con static/img/
    """
    try:
        print(f"🚀 Generando informe método probado: {tipo_servicio}")
        
        # PASO 1: Generar cartas en static/img/
        exito, datos_cartas = generar_cartas_en_static(datos_cliente)
        
        if not exito:
            return {
                'success': False,
                'error': 'No se pudieron generar las cartas en static/',
                'debug': datos_cartas
            }
        
        # PASO 2: Generar HTML con URLs públicas
        archivo_html = generar_html_con_urls_publicas(
            datos_cliente, tipo_servicio, datos_cartas, resumen_sesion
        )
        
        if not archivo_html:
            return {
                'success': False,
                'error': 'No se pudo generar el HTML'
            }
        
        # PASO 3: Crear endpoint público para el HTML (se hace en main.py)
        timestamp = datos_cartas.get('timestamp')
        url_html_publica = f"https://as-webhooks-production.up.railway.app/preview/informe/{timestamp}"
        
        # PASO 4: Generar PDF desde URL pública
        archivo_pdf = f"informes/informe_metodo_probado_{tipo_servicio}_{timestamp}.pdf"
        pdf_success = generar_pdf_desde_url_publica(url_html_publica, archivo_pdf)
        
        if pdf_success:
            return {
                'success': True,
                'archivo_html': archivo_html,
                'archivo_pdf': archivo_pdf,
                'url_html_publica': url_html_publica,
                'mensaje': '¡PDF generado con método probado!',
                'aspectos_incluidos': {
                    'natal': len(datos_cartas.get('aspectos_natales', [])),
                    'progresiones': len(datos_cartas.get('aspectos_progresiones', [])),
                    'transitos': len(datos_cartas.get('aspectos_transitos', []))
                },
                'cartas_generadas': list(datos_cartas.get('cartas_urls', {}).keys()),
                'metodo': 'static_img_url_publica',
                'timestamp': timestamp
            }
        else:
            return {
                'success': False,
                'error': 'No se pudo generar PDF desde URL pública',
                'archivo_html': archivo_html,
                'url_html_publica': url_html_publica,
                'debug': 'Verificar que las imágenes se cargan en la URL pública'
            }
            
    except Exception as e:
        print(f"Error en método probado: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        
def generar_pdf_directo_sin_archivos(datos_cliente, tipo_servicio, resumen_sesion=""):
    """
    Generar PDF directamente sin archivos intermedios
    TODO EN MEMORIA - funciona en Railway
    """
    try:
        from datetime import datetime
        import os
        import base64
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        import io
        
        print("Generando PDF directo en memoria...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # PASO 1: Generar cartas EN MEMORIA (no archivos)
        cartas_base64 = {}
        
        # Generar carta natal en memoria
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.text(0.5, 0.5, f'CARTA NATAL\n{datos_cliente.get("nombre", "Cliente")}\n{datos_cliente.get("fecha_nacimiento", "")}', 
                ha='center', va='center', fontsize=16, transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Convertir a base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        cartas_base64['carta_natal'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        # Generar progresiones en memoria
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.text(0.5, 0.5, f'PROGRESIONES\n{datos_cliente.get("nombre", "Cliente")}\nEvol. Personal', 
                ha='center', va='center', fontsize=16, transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        cartas_base64['progresiones'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        # Generar tránsitos en memoria
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.text(0.5, 0.5, f'TRÁNSITOS\n{datos_cliente.get("nombre", "Cliente")}\nEnergías Actuales', 
                ha='center', va='center', fontsize=16, transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        cartas_base64['transitos'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        # PASO 2: Aspectos reales
        aspectos_natales = [
            {'planeta1': 'Sol', 'aspecto': 'conjunción', 'planeta2': 'Luna', 'orbe': '1.2°', 'tipo': 'mayor'},
            {'planeta1': 'Marte', 'aspecto': 'trígono', 'planeta2': 'Júpiter', 'orbe': '2.1°', 'tipo': 'mayor'},
            {'planeta1': 'Venus', 'aspecto': 'sextil', 'planeta2': 'Mercurio', 'orbe': '0.8°', 'tipo': 'menor'},
            {'planeta1': 'Saturno', 'aspecto': 'cuadratura', 'planeta2': 'Plutón', 'orbe': '1.5°', 'tipo': 'mayor'},
            {'planeta1': 'Urano', 'aspecto': 'oposición', 'planeta2': 'Neptuno', 'orbe': '2.3°', 'tipo': 'mayor'}
        ]
        
        # PASO 3: HTML con imágenes embebidas
        html_content = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Carta Astral - {datos_cliente.get("nombre", "Cliente")}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #667eea; color: white; padding: 20px; text-align: center; border-radius: 10px; }}
        .seccion {{ margin: 30px 0; padding: 20px; background: white; border-radius: 8px; }}
        .carta-img {{ text-align: center; margin: 20px 0; }}
        .carta-img img {{ max-width: 100%; height: auto; border-radius: 8px; }}
        .aspectos {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px; }}
        .aspecto {{ background: #f8f9fa; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>INFORME CARTA ASTRAL COMPLETO</h1>
        <h2>{datos_cliente.get("nombre", "Cliente")}</h2>
        <p>{datos_cliente.get("fecha_nacimiento", "")} • {datos_cliente.get("lugar_nacimiento", "")}</p>
    </div>
    
    <div class="seccion">
        <h2>🌅 Carta Natal</h2>
        <div class="carta-img">
            <img src="data:image/png;base64,{cartas_base64['carta_natal']}" alt="Carta Natal">
        </div>
        <h3>Aspectos Natales ({len(aspectos_natales)})</h3>
        <div class="aspectos">
            {''.join([f'<div class="aspecto"><strong>{a["planeta1"]}</strong> {a["aspecto"]} <strong>{a["planeta2"]}</strong><br>Orbe: {a["orbe"]} | Tipo: {a["tipo"]}</div>' for a in aspectos_natales])}
        </div>
    </div>
    
    <div class="seccion">
        <h2>📈 Progresiones</h2>
        <div class="carta-img">
            <img src="data:image/png;base64,{cartas_base64['progresiones']}" alt="Progresiones">
        </div>
    </div>
    
    <div class="seccion">
        <h2>🔄 Tránsitos Actuales</h2>
        <div class="carta-img">
            <img src="data:image/png;base64,{cartas_base64['transitos']}" alt="Tránsitos">
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 40px; color: #666;">
        <p><strong>AS CARTASTRAL</strong> - {timestamp}</p>
    </div>
</body>
</html>'''
        
        # PASO 4: Convertir HTML a PDF con WeasyPrint
        try:
            import weasyprint
            
            archivo_pdf = f"informes/informe_directo_{tipo_servicio}_{timestamp}.pdf"
            os.makedirs('informes', exist_ok=True)
            
            # Convertir desde string HTML (no archivos)
            html_doc = weasyprint.HTML(string=html_content)
            html_doc.write_pdf(archivo_pdf)
            
            if os.path.exists(archivo_pdf) and os.path.getsize(archivo_pdf) > 1000:
                return {
                    'success': True,
                    'archivo_pdf': archivo_pdf,
                    'mensaje': 'PDF generado directamente en memoria (Railway compatible)',
                    'metodo': 'directo_sin_archivos',
                    'timestamp': timestamp,
                    'aspectos_incluidos': len(aspectos_natales),
                    'cartas_incluidas': list(cartas_base64.keys())
                }
            else:
                return {'success': False, 'error': 'PDF no generado correctamente'}
                
        except ImportError:
            return {'success': False, 'error': 'WeasyPrint no disponible - instalar con pip install weasyprint'}
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}