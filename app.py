from flask import Flask, render_template, request, jsonify, make_response
import os
import json
import glob
from datetime import datetime
# from weasyprint import HTML as weasyHTML
# from grafologia.routes import grafologia_bp
from flask import redirect, url_for

# ← LÍNEA CAMBIADA: Cambiar de routes_empresas a captador_empresas_simple
from captador_empresas_simple import captador_bp

app = Flask(__name__)
# ← LÍNEA CAMBIADA: Cambiar de empresas_bp a captador_bp
app.register_blueprint(captador_bp, url_prefix='/api')
# app.register_blueprint(grafologia_bp, url_prefix="/grafologia")
# Aceptar rutas con y sin barra final
app.url_map.strict_slashes = False

# DEBUG: log de cada request
from flask import request, jsonify, redirect, url_for
@app.before_request
def _dbg_log():
    print(f"→ {request.method} {request.path}")

# Listado de rutas (para inspección desde navegador)
@app.route("/__routes")
def __routes():
    return "<pre>" + "\n".join(sorted([r.rule for r in app.url_map.iter_rules()])) + "</pre>"

# Redirección vía url_for al blueprint (prueba adicional)
@app.route("/_grafo_health")
def _grafo_health():
    return redirect(url_for("grafologia.health"))
print("✅ Blueprint grafologia registrado")
print("🔎 Blueprints:", list(app.blueprints.keys()))
print("🔎 URL MAP:")
for r in app.url_map.iter_rules():
    print(" •", r.rule)

def obtener_ultima_carta():
    try:
        patron = "cartas_generadas/carta_*.json"
        archivos_json = glob.glob(patron)
        if not archivos_json:
            return None, None
        archivo_mas_reciente = max(archivos_json, key=os.path.getmtime)
        with open(archivo_mas_reciente, "r", encoding="utf-8") as f:
            carta_data = json.load(f)
        print(f"✓ Cargando carta desde: {archivo_mas_reciente}")
        return carta_data, archivo_mas_reciente
    except Exception as e:
        print(f"Error cargando carta: {e}")
        return None, None

def convertir_formato_datos(carta_data):
    if not carta_data:
        return {
            "planets": {},
            "houses": {},
            "points": {},
            "angles": {}
        }
    planets = {}
    for planeta, data in carta_data.get("posiciones_planetas", {}).items():
        planets[planeta.lower()] = {
            "sign": data["signo"],
            "degree": data["grado_en_signo"],
            "element": data["elemento"]
        }
    houses = {}
    for casa_data in carta_data.get("cuspides_casas", []):
        casa_num = casa_data["casa"]
        houses[f"house_{casa_num}"] = {
            "sign": casa_data["signo"],
            "degree": casa_data["grado_en_signo"]
        }
    points = {
        "ascendant": {
            "sign": carta_data.get("ascendente", {}).get("signo", ""),
            "degree": carta_data.get("ascendente", {}).get("grado_en_signo", 0)
        },
        "midheaven": {
            "sign": carta_data.get("mediocielo", {}).get("signo", ""),
            "degree": carta_data.get("mediocielo", {}).get("grado_en_signo", 0)
        }
    }
    angles = {
        "ascendant": carta_data.get("ascendente", {}).get("grado", 0),
        "midheaven": carta_data.get("mediocielo", {}).get("grado", 0)
    }
    return {
        "planets": planets,
        "houses": houses,
        "points": points,
        "angles": angles
    }

@app.route("/informe")
def generar_informe():
    carta_data, archivo_carta = obtener_ultima_carta()
    if not carta_data:
        return render_template("error.html", mensaje="No se encontraron cartas astrales.")
    datos_convertidos = convertir_formato_datos(carta_data)
    fecha_info = carta_data.get("fecha_nacimiento", {})
    lugar_info = carta_data.get("lugar", {})
    nombre_base = os.path.basename(archivo_carta).replace('.json', '')
    patron_png = f"cartas_generadas/{nombre_base}*.png"
    archivos_png = glob.glob(patron_png)
    if archivos_png:
        nombre_imagen = os.path.basename(archivos_png[0])
    else:
        nombre_imagen = "carta_no_encontrada.png"

    html = render_template(
        "informe.html",
        nombre="Consultante",
        fecha=f"{fecha_info.get('dia', '')}/{fecha_info.get('mes', '')}/{fecha_info.get('año', '')}",
        hora=fecha_info.get('hora_oficial', ''),
        ciudad=lugar_info.get('descripcion', 'Ubicación no especificada'),
        pais="",
        planetas=datos_convertidos["planets"],
        casas=datos_convertidos["houses"],
        puntos=datos_convertidos["points"],
        angulos=datos_convertidos["angles"],
        nombre_imagen=nombre_imagen,
        aspectos=carta_data.get("aspectos", [])
    )
    # pdf = weasyHTML(string=html, base_url=request.host_url).write_pdf()
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=informe_carta.pdf"
    return response

@app.route("/api/cartas")
def listar_cartas():
    try:
        patron = "cartas_generadas/carta_*.json"
        archivos_json = glob.glob(patron)
        cartas = []
        for archivo in archivos_json:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
            fecha_info = data.get("fecha_nacimiento", {})
            lugar_info = data.get("lugar", {})
            cartas.append({
                "archivo": os.path.basename(archivo),
                "fecha": f"{fecha_info.get('dia', '')}/{fecha_info.get('mes', '')}/{fecha_info.get('año', '')}",
                "hora": fecha_info.get('hora_oficial', ''),
                "lugar": lugar_info.get('descripcion', ''),
                "fecha_creacion": datetime.fromtimestamp(os.path.getmtime(archivo)).strftime("%Y-%m-%d %H:%M:%S")
            })
        cartas.sort(key=lambda x: x["fecha_creacion"], reverse=True)
        return jsonify(cartas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/carta/<archivo>")
def ver_carta_especifica(archivo):
    try:
        ruta_archivo = f"cartas_generadas/{archivo}"
        if not os.path.exists(ruta_archivo):
            return render_template("error.html", mensaje="Carta no encontrada")
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            carta_data = json.load(f)
        datos_convertidos = convertir_formato_datos(carta_data)
        fecha_info = carta_data.get("fecha_nacimiento", {})
        lugar_info = carta_data.get("lugar", {})
        nombre_base = archivo.replace('.json', '')
        patron_png = f"cartas_generadas/{nombre_base}*.png"
        archivos_png = glob.glob(patron_png)
        if archivos_png:
            nombre_imagen = os.path.basename(archivos_png[0])
        else:
            nombre_imagen = "carta_no_encontrada.png"
        return render_template(
            "informe.html",
            nombre="Consultante",
            fecha=f"{fecha_info.get('dia', '')}/{fecha_info.get('mes', '')}/{fecha_info.get('año', '')}",
            hora=fecha_info.get('hora_oficial', ''),
            ciudad=lugar_info.get('descripcion', 'Ubicación no especificada'),
            pais="",
            planetas=datos_convertidos["planets"],
            casas=datos_convertidos["houses"],
            puntos=datos_convertidos["points"],
            angulos=datos_convertidos["angles"],
            nombre_imagen=nombre_imagen,
            aspectos=carta_data.get("aspectos", [])
        )
    except Exception as e:
        return render_template("error.html", mensaje=f"Error cargando carta: {str(e)}")
        
@app.route("/")
def home():
    """Mostrar todos los endpoints disponibles"""
    endpoints = {
        # Endpoints originales (astrología)
        "/admin": "GET - Panel de administración",
        "/calendario": "GET - Calendario de citas",
        "/health": "GET - Verificación de estado",
        "/limpieza/estado": "GET - Estado del sistema de limpieza",
        "/limpieza/manual": "POST - Ejecutar limpieza manual",
        "/informe": "GET - Generar informe astrológico",
        "/api/cartas": "GET - Listar cartas astrales",
        "/carta/<archivo>": "GET - Ver carta específica",
        
        # Webhooks originales
        "/webhook/astrologa_astrolhoraria": "POST - Webhook Astróloga Horaria",
        "/webhook/astrologa_cartastral": "POST - Webhook Astróloga Carta Astral",
        "/webhook/astrologa_revolsolar": "POST - Webhook Astróloga Revolución Solar",
        "/webhook/astrologa_sinastria": "POST - Webhook Astróloga Sinastría",
        "/webhook/busca_empresas1": "POST - Webhook Búsqueda Empresas 1",
        "/webhook/busca_empresas2": "POST - Webhook Búsqueda Empresas 2",
        "/webhook/busca_empresas3": "POST - Webhook Búsqueda Empresas 3",
        "/webhook/chistes1": "POST - Webhook chistes1",
        "/webhook/grafologia": "POST - Webhook Grafología",
        "/webhook/lectura_facial": "POST - Webhook Lectura Facial",
        "/webhook/lectura_manos": "POST - Webhook Lectura de Manos",
        "/webhook/psico_coaching": "POST - Webhook Psicología y Coaching",
        "/webhook/redes_sociales1": "POST - Webhook Redes Sociales 1",
        "/webhook/redes_sociales2": "POST - Webhook Redes Sociales 2",
        "/webhook/redes_sociales3": "POST - Webhook Redes Sociales 3",
        "/webhook/redes_sociales4": "POST - Webhook Redes Sociales 4",
        "/webhook/redes_sociales5": "POST - Webhook Redes Sociales 5",
        "/webhook/redes_sociales6": "POST - Webhook Redes Sociales 6",
        "/webhook/redes_sociales7": "POST - Webhook Redes Sociales 7",
        "/webhook/sofia": "POST - Webhook de Sofía",
        "/webhook/tecnico_soporte": "POST - Webhook Técnico Soporte",
        "/webhook/vendedor1": "POST - Webhook de Vendedor 1",
        "/webhook/vendedor2": "POST - Webhook de Vendedor 2",
        "/webhook/vendedor3": "POST - Webhook de Vendedor 3",
        "/webhook/veronica": "POST - Webhook de Verónica",
        "/webhook/woocommerce": "POST - Webhook de WooCommerce",
        
        # NUEVOS ENDPOINTS - Sistema de Captadores
        "/api/captador1/SECTOR/UBICACION": "GET - Captador 1 buscar empresas",
        "/api/captador2/SECTOR/UBICACION": "GET - Captador 2 buscar empresas",
        "/api/captador3/SECTOR/UBICACION": "GET - Captador 3 buscar empresas",
        "/api/asignar_vendedor/VENDEDOR/CANTIDAD": "GET - Asignar empresas a vendedor",
        "/api/excel_todas": "GET - Exportar todas las empresas (Excel)",
        "/api/excel_pendientes": "GET - Exportar empresas pendientes (Excel)",
        "/api/excel_vendedor/VENDEDOR": "GET - Exportar empresas de vendedor (Excel)",
        "/api/vendedor_siguiente/VENDEDOR": "GET - Siguiente empresa para vendedor",
        "/api/vendedor_resultado/ID/RESULTADO": "GET - Marcar resultado de llamada",
        "/api/resumen": "GET - Resumen del sistema de empresas"
    }
    
    return jsonify({
        "message": "Servidor de agentes funcionando correctamente",
        "endpoints": endpoints,
        "ejemplos_captadores": {
            "activar_captador_1": "GET /api/captador1/restaurantes/barcelona",
            "activar_captador_2": "GET /api/captador2/clinicas/madrid",
            "activar_captador_3": "GET /api/captador3/talleres/valencia",
            "asignar_a_albert": "GET /api/asignar_vendedor/albert/20",
            "siguiente_empresa_juan": "GET /api/vendedor_siguiente/juan",
            "marcar_contactada": "GET /api/vendedor_resultado/123/contactada"
        },
        "sectores_ejemplo": [
            "restaurantes", "clinicas", "talleres", "peluquerias", "gimnasios",
            "farmacias", "opticas", "veterinarios", "panaderias", "floristerias",
            "papelerias", "librerias", "consultoras", "academias", "autoescuelas",
            "inmobiliarias", "seguros", "abogados", "dentistas", "fisioterapeutas"
        ]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)