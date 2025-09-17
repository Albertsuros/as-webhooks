from flask import Flask, render_template, request, jsonify, make_response
import os
import json
import glob
import requests
import subprocess
from retell import Retell
from datetime import datetime
# from weasyprint import HTML as weasyHTML
# from grafologia.routes import grafologia_bp
from flask import redirect, url_for

# ← LÍNEA CAMBIADA: Cambiar de routes_empresas a captador_empresas_simple
from captador_empresas_simple import captador_bp

# Configuración Zadarma-Retell
RETELL_API_KEY = os.environ.get('RETELL_API_KEY', 'key_714d5a5aa52c32258065da200b70')
ZADARMA_PHONE_NUMBER_ID = os.environ.get('+34936941520', '')

# Agent IDs de vendedores
AGENT_IDS = {
    'Albert': 'agent_f81a7da78a5ee87c667872153d',
    'Juan': 'agent_dddba811832aba40131c6a0f4e', 
    'Carlos': 'agent_80f7849e15b2f72d0aaf64989d'
}

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
    
def retell_llamada_zadarma(telefono, empresa, vendedor):
    """
    Nueva función para llamadas automatizadas via Zadarma-Retell
    """
    if not ZADARMA_PHONE_NUMBER_ID:
        return {"success": False, "error": "Zadarma no configurado aún"}
    
    headers = {
        'Authorization': f'Bearer {RETELL_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "phone_number": telefono,
        "agent_id": AGENT_IDS.get(vendedor, AGENT_IDS['Albert']),
        "phone_number_id": ZADARMA_PHONE_NUMBER_ID,
        "retell_llm_dynamic_variables": {
            "empresa": empresa,
            "vendedor": vendedor,
            "telefono": telefono,
            "origen": "automatizacion_vendedores"
        }
    }
    
    try:
        response = requests.post(
            'https://api.retellai.com/v2/call',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            return {
                "success": True,
                "call_id": response.json().get("call_id"),
                "message": f"Llamada iniciada: {vendedor} → {telefono}"
            }
        else:
            return {
                "success": False,
                "error": f"Error Retell: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"Excepción: {str(e)}"}

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
        
@app.route('/webhook/retell_callback', methods=['POST'])
def webhook_retell_callback():
    try:
        data = request.get_json()
        call_status = data.get('call_status')
        call_id = data.get('call_id')
        empresa_id = data.get('metadata', {}).get('empresa_id')
        
        if call_status == 'ended' and empresa_id:
            print(f"Llamada terminada para empresa {empresa_id}")
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route('/api/test_imports', methods=['GET'])
def test_imports():
    try:
        print("Testing imports...")
        from retell import Retell
        print("Retell import: OK")
        
        import os
        api_key = os.getenv('RETELL_API_KEY')
        print(f"API Key: {'Encontrada' if api_key else 'NO ENCONTRADA'}")
        
        return jsonify({"imports": "OK", "api_key_found": bool(api_key)})
    except Exception as e:
        print(f"ERROR en imports: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
@app.route('/api/retell_llamada', methods=['POST'])
def retell_llamada():
    try:
        data = request.get_json()
        from retell import Retell
        api_key = os.getenv('RETELL_API_KEY')
        retell_client = Retell(api_key=api_key)
        
        response = retell_client.call.create_phone_call(
            from_number=data.get('from_number'),
            to_number=data.get('to_number'),
            agent_id=data.get('agent_id')
        )
        
        return jsonify({
            "status": "success",
            "call_id": response.call_id,
            "call_status": response.call_status
        })
        
    except Exception as e:
        print(f"ERROR SDK: {str(e)}")
        return jsonify({
            "error_message": str(e),
            "error_details": repr(e)
        }), 200  # Cambiado a 200 para ver el error en Make

@app.route('/api/test_retell_step', methods=['POST'])
def test_retell_step():
    try:
        print("=== PASO 1: Función ejecutándose ===")
        
        data = request.get_json()
        print(f"=== PASO 2: Datos: {data} ===")
        
        from retell import Retell
        print("=== PASO 3: Import OK ===")
        
        api_key = os.getenv('RETELL_API_KEY')
        print(f"=== PASO 4: API Key OK ===")
        
        retell_client = Retell(api_key=api_key)
        print("=== PASO 5: Cliente inicializado ===")
        
        return jsonify({"test": "Todos los pasos OK"})
        
    except Exception as e:
        print(f"=== ERROR en paso: {str(e)} ===")
        return jsonify({"error": str(e)}), 500
        
@app.route('/api/test_simple', methods=['GET'])
def test_simple():
    return "FUNCIONA"
    
@app.route('/api/debug_phone_numbers', methods=['GET'])
def debug_phone_numbers():
    try:
        from retell import Retell
        retell_client = Retell(api_key=os.getenv('RETELL_API_KEY'))
        numbers = retell_client.phone_number.list()
        return jsonify(numbers)
    except Exception as e:
        return jsonify({"error": str(e)})
    
def retell_llamada_zadarma(telefono, empresa, vendedor):
    """
    Nueva función para llamadas automatizadas via Zadarma-Retell
    """
    if not ZADARMA_PHONE_NUMBER_ID:
        return {"success": False, "error": "Zadarma no configurado aún"}
    
    headers = {
        'Authorization': f'Bearer {key_714d5a5aa52c32258065da200b70}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "phone_number": telefono,
        "agent_id": AGENT_IDS.get(vendedor, AGENT_IDS['Albert']),
        "phone_number_id": +34936941520,
        "retell_llm_dynamic_variables": {
            "empresa": empresa,
            "vendedor": vendedor,
            "telefono": telefono,
            "origen": "automatizacion_vendedores"
        }
    }
    
    try:
        response = requests.post(
            'https://api.retellai.com/v2/call',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            return {
                "success": True,
                "call_id": response.json().get("call_id"),
                "message": f"Llamada iniciada: {vendedor} → {telefono}"
            }
        else:
            return {
                "success": False,
                "error": f"Error Retell: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"Excepción: {str(e)}"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)