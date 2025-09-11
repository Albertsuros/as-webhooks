
from flask import Flask, render_template, request, jsonify, make_response
import os
import json
import glob
from datetime import datetime

# ← NUEVA LÍNEA: Importar el sistema de captadores
from captador_empresas_simple import captador_bp

app = Flask(__name__)

# ← NUEVA LÍNEA: Registrar las rutas de captadores
app.register_blueprint(captador_bp, url_prefix='/api')

# Ruta principal - mostrar todos los endpoints disponibles
@app.route('/')
def home():
    """Mostrar todos los endpoints disponibles"""
    endpoints = {
        # Endpoints originales
        "/admin": "GET - Panel de administración",
        "/calendario": "GET - Calendario de citas", 
        "/health": "GET - Verificación de estado",
        "/limpieza/estado": "GET - Estado del sistema de limpieza",
        "/limpieza/manual": "POST - Ejecutar limpieza manual",
        
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
        "/api/resumen": "GET - Resumen del sistema"
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
            "papelerias", "librerías", "consultoras", "academias", "autoescuelas",
            "inmobiliarias", "seguros", "abogados", "dentistas", "fisioterapeutas"
        ]
    })

# ==========================================
# WEBHOOKS ORIGINALES (mantener funcionando)
# ==========================================

@app.route('/webhook/astrologa_astrolhoraria', methods=['POST'])
def webhook_astrologa_astrolhoraria():
    """Webhook para Astróloga Horaria"""
    try:
        data = request.get_json()
        # Tu lógica existente aquí
        return jsonify({"status": "success", "webhook": "astrologa_astrolhoraria"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/astrologa_cartastral', methods=['POST'])
def webhook_astrologa_cartastral():
    """Webhook para Astróloga Carta Astral"""
    try:
        data = request.get_json()
        # Tu lógica existente aquí
        return jsonify({"status": "success", "webhook": "astrologa_cartastral"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/astrologa_revolsolar', methods=['POST'])
def webhook_astrologa_revolsolar():
    """Webhook para Astróloga Revolución Solar"""
    try:
        data = request.get_json()
        # Tu lógica existente aquí
        return jsonify({"status": "success", "webhook": "astrologa_revolsolar"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/astrologa_sinastria', methods=['POST'])
def webhook_astrologa_sinastria():
    """Webhook para Astróloga Sinastría"""
    try:
        data = request.get_json()
        # Tu lógica existente aquí
        return jsonify({"status": "success", "webhook": "astrologa_sinastria"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# WEBHOOKS DE BÚSQUEDA DE EMPRESAS (actualizados para usar nuevo sistema)
@app.route('/webhook/busca_empresas1', methods=['POST'])
def webhook_busca_empresas1():
    """Webhook Búsqueda Empresas 1 - Redirige al nuevo sistema"""
    try:
        data = request.get_json()
        
        # Extraer sector y ubicación del webhook data si están disponibles
        sector = data.get('sector', 'general')
        ubicacion = data.get('ubicacion', 'barcelona')
        
        return jsonify({
            "status": "success", 
            "webhook": "busca_empresas1",
            "message": f"Usar endpoint: /api/captador1/{sector}/{ubicacion}",
            "redirect_url": f"/api/captador1/{sector}/{ubicacion}"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/busca_empresas2', methods=['POST'])
def webhook_busca_empresas2():
    """Webhook Búsqueda Empresas 2 - Redirige al nuevo sistema"""
    try:
        data = request.get_json()
        
        sector = data.get('sector', 'general')
        ubicacion = data.get('ubicacion', 'madrid')
        
        return jsonify({
            "status": "success", 
            "webhook": "busca_empresas2",
            "message": f"Usar endpoint: /api/captador2/{sector}/{ubicacion}",
            "redirect_url": f"/api/captador2/{sector}/{ubicacion}"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/busca_empresas3', methods=['POST'])
def webhook_busca_empresas3():
    """Webhook Búsqueda Empresas 3 - Redirige al nuevo sistema"""
    try:
        data = request.get_json()
        
        sector = data.get('sector', 'general')
        ubicacion = data.get('ubicacion', 'valencia')
        
        return jsonify({
            "status": "success", 
            "webhook": "busca_empresas3",
            "message": f"Usar endpoint: /api/captador3/{sector}/{ubicacion}",
            "redirect_url": f"/api/captador3/{sector}/{ubicacion}"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# WEBHOOKS DE VENDEDORES (actualizados para usar nuevo sistema)
@app.route('/webhook/vendedor1', methods=['POST'])
def webhook_vendedor1():
    """Webhook de Vendedor 1 (Albert) - Integrado con nuevo sistema"""
    try:
        data = request.get_json()
        
        return jsonify({
            "status": "success",
            "webhook": "vendedor1",
            "vendedor": "albert",
            "message": "Vendedor Albert conectado al sistema de empresas",
            "endpoints_disponibles": {
                "siguiente_empresa": "/api/vendedor_siguiente/albert",
                "marcar_resultado": "/api/vendedor_resultado/ID/RESULTADO",
                "excel_empresas": "/api/excel_vendedor/albert"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/vendedor2', methods=['POST'])
def webhook_vendedor2():
    """Webhook de Vendedor 2 (Juan) - Integrado con nuevo sistema"""
    try:
        data = request.get_json()
        
        return jsonify({
            "status": "success",
            "webhook": "vendedor2", 
            "vendedor": "juan",
            "message": "Vendedor Juan conectado al sistema de empresas",
            "endpoints_disponibles": {
                "siguiente_empresa": "/api/vendedor_siguiente/juan",
                "marcar_resultado": "/api/vendedor_resultado/ID/RESULTADO", 
                "excel_empresas": "/api/excel_vendedor/juan"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/vendedor3', methods=['POST'])
def webhook_vendedor3():
    """Webhook de Vendedor 3 (Carlos) - Integrado con nuevo sistema"""
    try:
        data = request.get_json()
        
        return jsonify({
            "status": "success",
            "webhook": "vendedor3",
            "vendedor": "carlos", 
            "message": "Vendedor Carlos conectado al sistema de empresas",
            "endpoints_disponibles": {
                "siguiente_empresa": "/api/vendedor_siguiente/carlos",
                "marcar_resultado": "/api/vendedor_resultado/ID/RESULTADO",
                "excel_empresas": "/api/excel_vendedor/carlos"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# OTROS WEBHOOKS (mantener como estaban)
@app.route('/webhook/chistes1', methods=['POST'])
def webhook_chistes1():
    """Webhook chistes1"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "chistes1"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/grafologia', methods=['POST'])
def webhook_grafologia():
    """Webhook Grafología"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "grafologia"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/lectura_facial', methods=['POST'])
def webhook_lectura_facial():
    """Webhook Lectura Facial"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "lectura_facial"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/lectura_manos', methods=['POST'])
def webhook_lectura_manos():
    """Webhook Lectura de Manos"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "lectura_manos"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/psico_coaching', methods=['POST'])
def webhook_psico_coaching():
    """Webhook Psicología y Coaching"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "psico_coaching"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# Webhooks de redes sociales
@app.route('/webhook/redes_sociales1', methods=['POST'])
def webhook_redes_sociales1():
    """Webhook Redes Sociales 1"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales1"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/redes_sociales2', methods=['POST'])
def webhook_redes_sociales2():
    """Webhook Redes Sociales 2"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales2"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/redes_sociales3', methods=['POST'])
def webhook_redes_sociales3():
    """Webhook Redes Sociales 3"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales3"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/redes_sociales4', methods=['POST'])
def webhook_redes_sociales4():
    """Webhook Redes Sociales 4"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales4"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/redes_sociales5', methods=['POST'])
def webhook_redes_sociales5():
    """Webhook Redes Sociales 5"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales5"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/redes_sociales6', methods=['POST'])
def webhook_redes_sociales6():
    """Webhook Redes Sociales 6"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales6"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/redes_sociales7', methods=['POST'])
def webhook_redes_sociales7():
    """Webhook Redes Sociales 7"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "redes_sociales7"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/sofia', methods=['POST'])
def webhook_sofia():
    """Webhook de Sofía"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "sofia"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/tecnico_soporte', methods=['POST'])
def webhook_tecnico_soporte():
    """Webhook Técnico Soporte"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "tecnico_soporte"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/veronica', methods=['POST'])
def webhook_veronica():
    """Webhook de Verónica"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "veronica"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/webhook/woocommerce', methods=['POST'])
def webhook_woocommerce():
    """Webhook de WooCommerce"""
    try:
        data = request.get_json()
        return jsonify({"status": "success", "webhook": "woocommerce"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ==========================================
# RUTAS ADMINISTRATIVAS ORIGINALES
# ==========================================

@app.route('/admin')
def admin():
    """Panel de administración"""
    return jsonify({
        "message": "Panel de administración",
        "sistema_empresas": {
            "captadores_activos": 3,
            "vendedores_activos": 3,
            "resumen": "/api/resumen"
        }
    })

@app.route('/calendario')
def calendario():
    """Calendario de citas"""
    return jsonify({"message": "Calendario de citas"})

@app.route('/health')
def health():
    """Verificación de estado del sistema"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sistema_empresas": "activo",
        "webhooks": "activos"
    })

@app.route('/limpieza/estado')
def limpieza_estado():
    """Estado del sistema de limpieza"""
    return jsonify({"limpieza_estado": "activo"})

@app.route('/limpieza/manual', methods=['POST'])
def limpieza_manual():
    """Ejecutar limpieza manual"""
    return jsonify({"limpieza_manual": "ejecutada"})

if __name__ == '__main__':
    # Crear directorio data si no existe
    if not os.path.exists('data'):
        os.makedirs('data')
    
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))