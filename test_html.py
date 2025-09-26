from flask import Blueprint, jsonify
import os
import glob
from datetime import datetime

# Crear blueprint
test_html_bp = Blueprint('test_html', __name__)

@test_html_bp.route('/test/ver_html_con_cartas_reales')
def ver_html_con_cartas_reales():
    """Ver HTML usando las cartas reales que ya sabemos que funcionan"""
    try:
        # Importar aquí para evitar problemas circulares
        from informes import generar_informe_html
        
        # Datos de prueba
        datos_cliente = {
            'nombre': 'Cliente con Cartas Reales',
            'email': 'cartas@reales.com',
            'codigo_servicio': 'REAL_123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # USAR CARTAS REALES que YA funcionan
        archivos_reales = {
            'carta_natal_img': 'https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926114637.png',
            'progresiones_img': 'https://as-webhooks-production.up.railway.app/static/progresiones_test_20250926114637.png', 
            'transitos_img': 'https://as-webhooks-production.up.railway.app/static/transitos_test_20250926114637.png'
        }
        
        # Generar HTML con cartas reales
        archivo_html = generar_informe_html(
            datos_cliente,
            'carta_astral_ia',
            archivos_reales,
            "HTML con cartas astrológicas REALES que ya funcionan perfectamente. Este sería el contenido exacto del PDF."
        )
        
        if archivo_html and os.path.exists(archivo_html):
            # Leer HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            return html_content
        else:
            return "<h1>Error: No se pudo generar HTML</h1>", 500
            
    except Exception as e:
        import traceback
        return f"""
        <html>
        <body>
            <h1 style="color: red;">Error</h1>
            <p>{str(e)}</p>
            <pre>{traceback.format_exc()}</pre>
        </body>
        </html>
        """, 500

@test_html_bp.route('/test/ver_html_carta_astral/<especialidad>')
def ver_html_carta_astral(especialidad):
    """Mostrar HTML generado directamente en el browser"""
    try:
        from informes import generar_informe_html
        
        # Importar función que sabemos que existe
        from main import crear_archivos_unicos_testing
        
        # Datos de prueba
        datos_cliente = {
            'nombre': 'Cliente Prueba HTML',
            'email': 'html@test.com',
            'codigo_servicio': f'HTML_{especialidad.upper()}',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # Generar archivos únicos
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        
        # Generar HTML
        archivo_html = generar_informe_html(
            datos_cliente, 
            especialidad, 
            archivos_unicos, 
            "Este es el HTML completo que se convertiría a PDF"
        )
        
        if archivo_html and os.path.exists(archivo_html):
            # Leer y servir el HTML directamente
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Servir HTML directo al browser
            return html_content
        else:
            return f"""
            <html>
            <body>
                <h1 style="color: red;">Error generando HTML</h1>
                <p>No se pudo generar el archivo HTML para {especialidad}</p>
                <p>Archivo esperado: {archivo_html}</p>
            </body>
            </html>
            """, 500
            
    except Exception as e:
        import traceback
        return f"""
        <html>
        <body>
            <h1 style="color: red;">Error crítico</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <pre style="background: #f0f0f0; padding: 10px;">
{traceback.format_exc()}
            </pre>
        </body>
        </html>
        """, 500

@test_html_bp.route('/test/lista_archivos_html_generados')
def lista_archivos_html_generados():
    """Listar todos los HTML generados para poder verlos"""
    try:
        # Buscar archivos HTML en templates/
        patron_html = "templates/informe_*.html"
        archivos_html = glob.glob(patron_html)
        
        # Crear lista con info de cada archivo
        lista_archivos = []
        
        for archivo in archivos_html:
            try:
                stats = os.stat(archivo)
                nombre_archivo = os.path.basename(archivo)
                
                lista_archivos.append({
                    'nombre': nombre_archivo,
                    'tamaño_kb': round(stats.st_size / 1024, 2),
                    'fecha_creacion': datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'ver_url': f'/test/ver_archivo_html/{nombre_archivo}'
                })
            except:
                continue
        
        # Ordenar por fecha más reciente
        lista_archivos.sort(key=lambda x: x['fecha_creacion'], reverse=True)
        
        # Crear HTML de respuesta
        html_response = """
        <html>
        <head>
            <title>Archivos HTML Generados - AS Cartastral</title>
            <style>
                body { font-family: Arial; margin: 40px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #3498db; color: white; }
                .btn { background: #2ecc71; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; }
                .btn:hover { background: #27ae60; }
            </style>
        </head>
        <body>
            <h1>📄 Archivos HTML Generados</h1>
            <p>Archivos HTML que se han generado. Haz clic en "Ver" para abrir cada uno.</p>
        """
        
        if lista_archivos:
            html_response += """
            <table>
                <tr>
                    <th>Nombre</th>
                    <th>Tamaño (KB)</th>
                    <th>Fecha</th>
                    <th>Ver</th>
                </tr>
            """
            
            for archivo in lista_archivos:
                html_response += f"""
                <tr>
                    <td>{archivo['nombre']}</td>
                    <td>{archivo['tamaño_kb']} KB</td>
                    <td>{archivo['fecha_creacion']}</td>
                    <td><a href="{archivo['ver_url']}" class="btn" target="_blank">Ver</a></td>
                </tr>
                """
            
            html_response += "</table>"
        else:
            html_response += "<p>No se encontraron archivos HTML.</p>"
        
        html_response += """
            <hr>
            <h3>🔧 Enlaces de Prueba:</h3>
            <ul>
                <li><a href="/test/ver_html_con_cartas_reales" target="_blank">📊 Ver HTML con cartas reales</a></li>
                <li><a href="/test/ver_html_carta_astral/carta_astral_ia" target="_blank">🔮 Generar HTML carta astral</a></li>
                <li><a href="/test/ver_html_carta_astral/sinastria_ia" target="_blank">💑 Generar HTML sinastría</a></li>
                <li><a href="/debug/sofia_generacion" target="_blank">⚡ Generar cartas nuevas</a></li>
            </ul>
        </body>
        </html>
        """
        
        return html_response
        
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>", 500

@test_html_bp.route('/test/ver_archivo_html/<nombre_archivo>')
def ver_archivo_html(nombre_archivo):
    """Ver un archivo HTML específico"""
    try:
        ruta_archivo = f"templates/{nombre_archivo}"
        
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html_content
        else:
            return f"<h1>Archivo no encontrado: {nombre_archivo}</h1>", 404
            
    except Exception as e:
        return f"<h1>Error leyendo archivo: {str(e)}</h1>", 500