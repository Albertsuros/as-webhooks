# routes_empresas.py
from flask import Blueprint, request, jsonify, render_template_string
from busqueda_empresas import buscador

# Crear Blueprint para las rutas de empresas
empresas_bp = Blueprint('empresas', __name__)

# ==========================================
# RUTAS PARA ACTIVAR BÚSQUEDAS
# ==========================================

@empresas_bp.route('/buscar/<sector>/<ubicacion>')
def buscar_empresas(sector, ubicacion):
    """Activar búsqueda de empresas"""
    agente_id = request.args.get('agente', 'busca_empresas_1')
    cantidad = int(request.args.get('cantidad', 10))
    
    # Ejecutar búsqueda
    resultado = buscador.ejecutar_busqueda(sector, ubicacion, agente_id, cantidad)
    
    return jsonify(resultado)

@empresas_bp.route('/buscar')
def buscar_form():
    """Formulario simple para búsqueda manual"""
    sector = request.args.get('sector', '')
    ubicacion = request.args.get('ubicacion', '')
    
    if sector and ubicacion:
        return buscar_empresas(sector, ubicacion)
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Buscar Empresas</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            .form-group { margin: 15px 0; }
            input, select { padding: 10px; margin: 5px; }
            .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>🔍 Buscar Empresas</h1>
        <form method="GET">
            <div class="form-group">
                <label>Sector:</label><br>
                <select name="sector" required>
                    <option value="">Seleccionar sector</option>
                    <option value="restaurantes">Restaurantes</option>
                    <option value="clinicas">Clínicas</option>
                    <option value="gimnasios">Gimnasios</option>
                    <option value="peluquerias">Peluquerías</option>
                    <option value="talleres">Talleres</option>
                    <option value="tiendas">Tiendas</option>
                    <option value="consultoras">Consultoras</option>
                </select>
            </div>
            <div class="form-group">
                <label>Ubicación:</label><br>
                <select name="ubicacion" required>
                    <option value="">Seleccionar ubicación</option>
                    <option value="barcelona">Barcelona</option>
                    <option value="madrid">Madrid</option>
                    <option value="valencia">Valencia</option>
                    <option value="sevilla">Sevilla</option>
                    <option value="bilbao">Bilbao</option>
                    <option value="zaragoza">Zaragoza</option>
                </select>
            </div>
            <div class="form-group">
                <label>Agente:</label><br>
                <select name="agente">
                    <option value="busca_empresas_1">Busca Empresas 1</option>
                    <option value="busca_empresas_2">Busca Empresas 2</option>
                    <option value="busca_empresas_3">Busca Empresas 3</option>
                </select>
            </div>
            <button type="submit" class="btn">🚀 Buscar Empresas</button>
        </form>
        
        <h2>📞 Enlaces rápidos:</h2>
        <a href="/api/buscar/restaurantes/barcelona?agente=busca_empresas_1" class="btn">Restaurantes BCN</a>
        <a href="/api/buscar/clinicas/madrid?agente=busca_empresas_2" class="btn">Clínicas Madrid</a>
        <a href="/api/buscar/gimnasios/valencia?agente=busca_empresas_3" class="btn">Gimnasios Valencia</a>
    </body>
    </html>
    '''
    return html

# ==========================================
# RUTAS PARA VER EMPRESAS
# ==========================================

@empresas_bp.route('/empresas')
def listar_empresas():
    """Ver todas las empresas"""
    estado = request.args.get('estado')
    vendedor = request.args.get('vendedor')
    
    resultado = buscador.obtener_empresas(estado=estado, vendedor=vendedor)
    return jsonify(resultado)

@empresas_bp.route('/empresas/<estado>')
def empresas_por_estado(estado):
    """Ver empresas por estado específico"""
    resultado = buscador.obtener_empresas(estado=estado)
    return jsonify(resultado)

@empresas_bp.route('/vendedor/<vendedor>/empresas')
def empresas_vendedor(vendedor):
    """Ver empresas asignadas a vendedor"""
    resultado = buscador.obtener_empresas(vendedor=vendedor)
    return jsonify(resultado)

# ==========================================
# RUTAS PARA GESTIÓN
# ==========================================

@empresas_bp.route('/asignar', methods=['POST'])
def asignar_empresa():
    """Asignar empresa a vendedor"""
    data = request.get_json()
    empresa_id = data.get('empresa_id')
    vendedor = data.get('vendedor')
    
    if not empresa_id or not vendedor:
        return jsonify({
            'success': False,
            'error': 'Faltan datos: empresa_id y vendedor'
        }), 400
    
    resultado = buscador.asignar_vendedor(empresa_id, vendedor)
    return jsonify(resultado)

# ==========================================
# DASHBOARD PRINCIPAL
# ==========================================

@empresas_bp.route('/dashboard')
def dashboard():
    """Dashboard principal de empresas"""
    
    # Obtener estadísticas
    todas = buscador.obtener_empresas()
    pendientes = buscador.obtener_empresas(estado='pendiente')
    contactadas = buscador.obtener_empresas(estado='contactada')
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard Empresas</title>
        <style>
            body {{ font-family: Arial; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
            .stat {{ background: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; }}
            .stat h2 {{ margin: 0; color: #007bff; font-size: 2em; }}
            .stat p {{ margin: 5px 0 0 0; color: #666; }}
            .section {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .btn {{ background: #007bff; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; margin: 5px; display: inline-block; }}
            .btn:hover {{ background: #0056b3; }}
            .btn.success {{ background: #28a745; }}
            .btn.warning {{ background: #ffc107; color: black; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 Dashboard de Búsqueda de Empresas</h1>
                <p>Sistema de gestión de empresas captadas por agentes</p>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <h2>{todas['total']}</h2>
                    <p>Total Empresas</p>
                </div>
                <div class="stat">
                    <h2>{pendientes['total']}</h2>
                    <p>Pendientes</p>
                </div>
                <div class="stat">
                    <h2>{contactadas['total']}</h2>
                    <p>Contactadas</p>
                </div>
                <div class="stat">
                    <h2>3</h2>
                    <p>Agentes Activos</p>
                </div>
            </div>
            
            <div class="section">
                <h2>🔍 Activar Búsquedas</h2>
                <p>Hacer clic para activar agentes buscadores:</p>
                <a href="/api/buscar/restaurantes/barcelona?agente=busca_empresas_1" class="btn">🍽️ Restaurantes Barcelona</a>
                <a href="/api/buscar/clinicas/madrid?agente=busca_empresas_2" class="btn">🏥 Clínicas Madrid</a>
                <a href="/api/buscar/gimnasios/valencia?agente=busca_empresas_3" class="btn">💪 Gimnasios Valencia</a>
                <a href="/api/buscar/peluquerias/sevilla?agente=busca_empresas_1" class="btn">✂️ Peluquerías Sevilla</a>
                <a href="/api/buscar/talleres/bilbao?agente=busca_empresas_2" class="btn">🔧 Talleres Bilbao</a>
                <a href="/api/buscar" class="btn warning">📝 Búsqueda Manual</a>
            </div>
            
            <div class="section">
                <h2>📊 Ver Datos</h2>
                <p>Consultar empresas capturadas:</p>
                <a href="/api/empresas" class="btn success">📋 Todas las Empresas</a>
                <a href="/api/empresas/pendientes" class="btn">⏳ Pendientes de Contactar</a>
                <a href="/api/empresas/contactada" class="btn">✅ Ya Contactadas</a>
                <a href="/api/empresas/asignada" class="btn">👤 Asignadas</a>
            </div>
            
            <div class="section">
                <h2>📞 Vendedores</h2>
                <p>Empresas por vendedor:</p>
                <a href="/api/vendedor/albert/empresas" class="btn">👨 Albert</a>
                <a href="/api/vendedor/juan/empresas" class="btn">👨 Juan</a>
                <a href="/api/vendedor/carlos/empresas" class="btn">👨 Carlos</a>
            </div>
            
            <div class="section">
                <h2>⚡ URLs Directas</h2>
                <p>Para usar en Make o scripts:</p>
                <code>GET /api/buscar/SECTOR/UBICACION?agente=busca_empresas_1</code><br>
                <code>GET /api/empresas/pendientes</code><br>
                <code>POST /api/asignar (empresa_id, vendedor)</code>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

# ==========================================
# RUTA DE TESTING
# ==========================================

@empresas_bp.route('/test')
def test_sistema():
    """Probar que el sistema funciona"""
    try:
        # Crear tabla si no existe
        buscador.crear_tabla()
        
        # Hacer búsqueda de prueba
        resultado = buscador.ejecutar_busqueda('test', 'barcelona', 'test_agente', 3)
        
        return jsonify({
            'success': True,
            'message': 'Sistema funcionando correctamente',
            'test_resultado': resultado
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error en el sistema'
        }), 500