# routes_empresas.py - ARCHIVO COMPLETO FINAL
from flask import Blueprint, request, jsonify, render_template_string, make_response
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

@empresas_bp.route('/actualizar_campo', methods=['POST'])
def actualizar_campo():
    """Actualizar un campo específico de una empresa"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        campo = data.get('campo')
        valor = data.get('valor')
        
        if not empresa_id or not campo:
            return jsonify({
                'success': False,
                'error': 'Faltan datos: empresa_id y campo'
            }), 400
        
        # Actualizar en base de datos
        import sqlite3
        
        conn = sqlite3.connect(buscador.db_path)
        cursor = conn.cursor()
        
        # Validar que el campo existe en la tabla
        campos_validos = [
            'nombre', 'telefono', 'email', 'web', 'direccion',
            'contacto_nombre', 'contacto_cargo', 'estado', 
            'vendedor_asignado', 'resultado_llamada', 'notas'
        ]
        
        if campo not in campos_validos:
            return jsonify({
                'success': False,
                'error': f'Campo no válido: {campo}'
            }), 400
        
        # Actualizar campo
        cursor.execute(
            f'UPDATE empresas SET {campo} = ? WHERE id = ?',
            (valor, empresa_id)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Campo {campo} actualizado correctamente'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@empresas_bp.route('/añadir_manual', methods=['POST'])
def añadir_empresa_manual():
    """Añadir empresa manualmente"""
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        telefono = data.get('telefono', '')
        email = data.get('email', '')
        estado = data.get('estado', 'pendiente')
        
        if not nombre:
            return jsonify({
                'success': False,
                'error': 'El nombre es obligatorio'
            }), 400
        
        # Crear empresa manual
        empresa = {
            'nombre': nombre,
            'telefono': telefono,
            'email': email,
            'web': '',
            'direccion': '',
            'sector': 'manual',
            'ubicacion': 'manual'
        }
        
        # Guardar usando el buscador
        if buscador.guardar_empresa(empresa, 'manual'):
            return jsonify({
                'success': True,
                'message': 'Empresa añadida correctamente'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error guardando empresa o ya existe'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@empresas_bp.route('/eliminar/<int:empresa_id>', methods=['DELETE'])
def eliminar_empresa(empresa_id):
    """Eliminar empresa"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(buscador.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM empresas WHERE id = ?', (empresa_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({
                'success': True,
                'message': 'Empresa eliminada correctamente'
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Empresa no encontrada'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@empresas_bp.route('/duplicar/<int:empresa_id>', methods=['POST'])
def duplicar_empresa(empresa_id):
    """Duplicar empresa"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(buscador.db_path)
        cursor = conn.cursor()
        
        # Obtener empresa original
        cursor.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
        empresa = cursor.fetchone()
        
        if not empresa:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Empresa no encontrada'
            }), 404
        
        # Duplicar empresa (sin ID y con nombre modificado)
        cursor.execute('''
            INSERT INTO empresas (
                nombre, telefono, email, web, direccion,
                sector, ubicacion, agente_captura, estado,
                fecha_captura
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (
            f"{empresa[1]} (Copia)",  # nombre
            empresa[2],               # telefono
            empresa[3],               # email
            empresa[4],               # web
            empresa[5],               # direccion
            empresa[6],               # sector
            empresa[7],               # ubicacion
            'duplicado',              # agente_captura
            'pendiente'               # estado
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Empresa duplicada correctamente'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@empresas_bp.route('/exportar_excel')
def exportar_excel():
    """Exportar empresas a Excel (CSV por simplicidad)"""
    try:
        import csv
        import io
        
        # Obtener todas las empresas
        resultado = buscador.obtener_empresas(limit=10000)
        
        if not resultado['success']:
            return jsonify(resultado), 500
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'ID', 'Empresa', 'Teléfono', 'Email', 'Web',
            'Contacto', 'Cargo', 'Estado', 'Vendedor',
            'Fecha', 'Resultado', 'Notas'
        ])
        
        # Datos
        for empresa in resultado['empresas']:
            writer.writerow([
                empresa.get('id', ''),
                empresa.get('nombre', ''),
                empresa.get('telefono', ''),
                empresa.get('email', ''),
                empresa.get('web', ''),
                empresa.get('contacto_nombre', ''),
                empresa.get('contacto_cargo', ''),
                empresa.get('estado', ''),
                empresa.get('vendedor_asignado', ''),
                empresa.get('fecha_captura', ''),
                empresa.get('resultado_llamada', ''),
                empresa.get('notas', '')
            ])
        
        # Crear respuesta
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=empresas.csv'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@empresas_bp.route('/limpiar_todo', methods=['DELETE'])
def limpiar_base_datos():
    """Limpiar toda la base de datos"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(buscador.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM empresas')
        total_eliminadas = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Base de datos limpiada: {total_eliminadas} empresas eliminadas'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================================
# PANEL DE CONTROL PRINCIPAL
# ==========================================

@empresas_bp.route('/panel')
def panel_control():
    """Panel de control tipo Excel"""
    html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestión de Empresas - AS Asesores</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .controls { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .control-panel { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .control-panel h3 { margin-bottom: 15px; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #555; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        .form-group textarea { height: 80px; resize: vertical; }
        .btn { background: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: 600; transition: background 0.3s; }
        .btn:hover { background: #0056b3; }
        .btn.success { background: #28a745; }
        .btn.warning { background: #ffc107; color: black; }
        .btn.danger { background: #dc3545; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
        .stat-card .number { font-size: 2.5em; font-weight: bold; color: #007bff; margin-bottom: 5px; }
        .stat-card .label { color: #666; font-size: 14px; }
        .table-container { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .table-header { background: #007bff; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .table-controls { display: flex; gap: 10px; }
        .search-box { padding: 8px 12px; border: none; border-radius: 5px; background: rgba(255,255,255,0.2); color: white; }
        .search-box::placeholder { color: rgba(255,255,255,0.7); }
        .excel-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .excel-table th { background: #f8f9fa; padding: 12px 8px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: 600; position: sticky; top: 0; z-index: 10; }
        .excel-table td { padding: 10px 8px; border-bottom: 1px solid #e9ecef; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .excel-table tr:hover { background: #f8f9fa; }
        .estado { padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; text-align: center; }
        .estado.pendiente { background: #fff3cd; color: #856404; }
        .estado.proceso { background: #cce7ff; color: #0066cc; }
        .estado.contactada { background: #d4edda; color: #155724; }
        .estado.rechazada { background: #f8d7da; color: #721c24; }
        .accion-btn { padding: 4px 8px; margin: 2px; border: none; border-radius: 3px; cursor: pointer; font-size: 11px; }
        .editable { background: transparent; border: none; width: 100%; padding: 2px; }
        .editable:focus { background: #e7f3ff; outline: 1px solid #007bff; }
        .table-wrapper { max-height: 600px; overflow-y: auto; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .filters { background: white; padding: 15px 20px; border-bottom: 1px solid #e9ecef; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }
        .filter-group { display: flex; align-items: center; gap: 5px; }
        .filter-group select { padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 Sistema de Gestión de Empresas</h1>
            <p>Panel de control completo para búsqueda, gestión y seguimiento de empresas</p>
        </div>

        <div class="controls">
            <div class="control-panel">
                <h3>🔍 Búsqueda Personalizada</h3>
                <div class="form-group">
                    <label>Tipo de negocio:</label>
                    <input type="text" id="tipoNegocio" placeholder="ej: restaurantes, clínicas, talleres...">
                </div>
                <div class="form-group">
                    <label>Ubicación:</label>
                    <input type="text" id="ubicacion" placeholder="ej: Barcelona, Madrid, toda Cataluña...">
                </div>
                <div class="form-group">
                    <label>Fuente de búsqueda:</label>
                    <select id="fuente">
                        <option value="google">Google + Páginas Amarillas</option>
                        <option value="google_maps">Google Maps</option>
                        <option value="paginas_amarillas">Solo Páginas Amarillas</option>
                        <option value="manual">Entrada manual</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Criterios adicionales:</label>
                    <textarea id="criterios" placeholder="ej: con web, sin web, tamaño pequeño, abiertos..."></textarea>
                </div>
                <button class="btn" onclick="iniciarBusqueda()">🚀 Buscar Empresas</button>
            </div>

            <div class="control-panel">
                <h3>📝 Añadir Empresa Manual</h3>
                <div class="form-group">
                    <label>Nombre empresa:</label>
                    <input type="text" id="nombreManual" placeholder="Nombre de la empresa">
                </div>
                <div class="form-group">
                    <label>Teléfono:</label>
                    <input type="text" id="telefonoManual" placeholder="Teléfono">
                </div>
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" id="emailManual" placeholder="Email">
                </div>
                <div class="form-group">
                    <label>Estado inicial:</label>
                    <select id="estadoManual">
                        <option value="pendiente">Pendiente</option>
                        <option value="proceso">En proceso</option>
                        <option value="contactada">Contactada</option>
                    </select>
                </div>
                <button class="btn success" onclick="añadirEmpresaManual()">➕ Añadir Empresa</button>
            </div>

            <div class="control-panel">
                <h3>⚡ Acciones Rápidas</h3>
                <div class="form-group">
                    <label>Exportar datos:</label>
                    <button class="btn warning" onclick="exportarExcel()">📊 Descargar Excel</button>
                </div>
                <div class="form-group">
                    <label>Asignaciones masivas:</label>
                    <select id="vendedorMasivo">
                        <option value="">Seleccionar vendedor</option>
                        <option value="albert">Albert</option>
                        <option value="juan">Juan</option>
                        <option value="carlos">Carlos</option>
                    </select>
                    <button class="btn" onclick="asignarMasivo()">👥 Asignar Seleccionadas</button>
                </div>
                <div class="form-group">
                    <label>Limpiar base de datos:</label>
                    <button class="btn danger" onclick="confirmarLimpiar()">🗑️ Limpiar Todo</button>
                </div>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number" id="totalEmpresas">0</div>
                <div class="label">Total Empresas</div>
            </div>
            <div class="stat-card">
                <div class="number" id="pendientes">0</div>
                <div class="label">Pendientes</div>
            </div>
            <div class="stat-card">
                <div class="number" id="proceso">0</div>
                <div class="label">En Proceso</div>
            </div>
            <div class="stat-card">
                <div class="number" id="contactadas">0</div>
                <div class="label">Contactadas</div>
            </div>
            <div class="stat-card">
                <div class="number" id="hoy">0</div>
                <div class="label">Captadas Hoy</div>
            </div>
        </div>

        <div class="table-container">
            <div class="table-header">
                <h3>📋 Empresas Captadas</h3>
                <div class="table-controls">
                    <input type="text" class="search-box" placeholder="Buscar empresa..." id="searchBox" oninput="filtrarTabla()">
                    <button class="btn" onclick="cargarEmpresas()">🔄 Actualizar</button>
                </div>
            </div>
            
            <div class="filters">
                <div class="filter-group">
                    <label>Estado:</label>
                    <select id="filtroEstado" onchange="aplicarFiltros()">
                        <option value="">Todos</option>
                        <option value="pendiente">Pendiente</option>
                        <option value="proceso">En Proceso</option>
                        <option value="contactada">Contactada</option>
                        <option value="rechazada">Rechazada</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Vendedor:</label>
                    <select id="filtroVendedor" onchange="aplicarFiltros()">
                        <option value="">Todos</option>
                        <option value="albert">Albert</option>
                        <option value="juan">Juan</option>
                        <option value="carlos">Carlos</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Fecha:</label>
                    <input type="date" id="filtroFecha" onchange="aplicarFiltros()">
                </div>
            </div>
            
            <div class="table-wrapper">
                <table class="excel-table" id="tablaEmpresas">
                    <thead>
                        <tr>
                            <th><input type="checkbox" id="selectAll" onchange="seleccionarTodos()"></th>
                            <th>ID</th>
                            <th>Empresa</th>
                            <th>Teléfono</th>
                            <th>Email</th>
                            <th>Web</th>
                            <th>Contacto</th>
                            <th>Cargo</th>
                            <th>Estado</th>
                            <th>Vendedor</th>
                            <th>Fecha</th>
                            <th>Resultado</th>
                            <th>Notas</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody id="cuerpoTabla">
                        <tr>
                            <td colspan="14" class="loading">Cargando empresas...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let empresas = [];
        let empresasFiltradas = [];

        document.addEventListener('DOMContentLoaded', function() {
            cargarEmpresas();
        });

        async function cargarEmpresas() {
            try {
                const response = await fetch('/api/empresas');
                const data = await response.json();
                
                if (data.success) {
                    empresas = data.empresas;
                    empresasFiltradas = empresas;
                    actualizarTabla();
                    actualizarEstadisticas();
                } else {
                    console.error('Error:', data.error);
                }
            } catch (error) {
                console.error('Error cargando empresas:', error);
            }
        }

        function actualizarTabla() {
            const tbody = document.getElementById('cuerpoTabla');
            
            if (empresasFiltradas.length === 0) {
                tbody.innerHTML = '<tr><td colspan="14" class="loading">No hay empresas que mostrar</td></tr>';
                return;
            }
            
            tbody.innerHTML = empresasFiltradas.map(empresa => `
                <tr data-id="${empresa.id}">
                    <td><input type="checkbox" class="empresa-checkbox" value="${empresa.id}"></td>
                    <td>${empresa.id}</td>
                    <td><input type="text" class="editable" value="${empresa.nombre || ''}" onchange="actualizarCampo(${empresa.id}, 'nombre', this.value)"></td>
                    <td><input type="text" class="editable" value="${empresa.telefono || ''}" onchange="actualizarCampo(${empresa.id}, 'telefono', this.value)"></td>
                    <td><input type="email" class="editable" value="${empresa.email || ''}" onchange="actualizarCampo(${empresa.id}, 'email', this.value)"></td>
                    <td><input type="url" class="editable" value="${empresa.web || ''}" onchange="actualizarCampo(${empresa.id}, 'web', this.value)"></td>
                    <td><input type="text" class="editable" value="${empresa.contacto_nombre || ''}" onchange="actualizarCampo(${empresa.id}, 'contacto_nombre', this.value)"></td>
                    <td><input type="text" class="editable" value="${empresa.contacto_cargo || ''}" onchange="actualizarCampo(${empresa.id}, 'contacto_cargo', this.value)"></td>
                    <td>
                        <select class="estado ${empresa.estado}" onchange="actualizarCampo(${empresa.id}, 'estado', this.value)">
                            <option value="pendiente" ${empresa.estado === 'pendiente' ? 'selected' : ''}>Pendiente</option>
                            <option value="proceso" ${empresa.estado === 'proceso' ? 'selected' : ''}>En Proceso</option>
                            <option value="contactada" ${empresa.estado === 'contactada' ? 'selected' : ''}>Contactada</option>
                            <option value="rechazada" ${empresa.estado === 'rechazada' ? 'selected' : ''}>Rechazada</option>
                        </select>
                    </td>
                    <td>
                        <select onchange="actualizarCampo(${empresa.id}, 'vendedor_asignado', this.value)">
                            <option value="">Sin asignar</option>
                            <option value="albert" ${empresa.vendedor_asignado === 'albert' ? 'selected' : ''}>Albert</option>
                            <option value="juan" ${empresa.vendedor_asignado === 'juan' ? 'selected' : ''}>Juan</option>
                            <option value="carlos" ${empresa.vendedor_asignado === 'carlos' ? 'selected' : ''}>Carlos</option>
                        </select>
                    </td>
                    <td>${new Date(empresa.fecha_captura).toLocaleDateString()}</td>
                    <td><input type="text" class="editable" value="${empresa.resultado_llamada || ''}" onchange="actualizarCampo(${empresa.id}, 'resultado_llamada', this.value)"></td>
                    <td><input type="text" class="editable" value="${empresa.notas || ''}" onchange="actualizarCampo(${empresa.id}, 'notas', this.value)"></td>
                    <td>
                        <button class="accion-btn" onclick="eliminarEmpresa(${empresa.id})" style="background: #dc3545; color: white;">🗑️</button>
                        <button class="accion-btn" onclick="duplicarEmpresa(${empresa.id})" style="background: #28a745; color: white;">📋</button>
                    </td>
                </tr>
            `).join('');
        }

        function actualizarEstadisticas() {
            const total = empresas.length;
            const pendientes = empresas.filter(e => e.estado === 'pendiente').length;
            const proceso = empresas.filter(e => e.estado === 'proceso').length;
            const contactadas = empresas.filter(e => e.estado === 'contactada').length;
            
            const hoy = new Date().toDateString();
            const hoyCount = empresas.filter(e => 
                new Date(e.fecha_captura).toDateString() === hoy
            ).length;

            document.getElementById('totalEmpresas').textContent = total;
            document.getElementById('pendientes').textContent = pendientes;
            document.getElementById('proceso').textContent = proceso;
            document.getElementById('contactadas').textContent = contactadas;
            document.getElementById('hoy').textContent = hoyCount;
        }

        function filtrarTabla() {
            const busqueda = document.getElementById('searchBox').value.toLowerCase();
            
            empresasFiltradas = empresas.filter(empresa => {
                return (empresa.nombre || '').toLowerCase().includes(busqueda) ||
                       (empresa.telefono || '').toLowerCase().includes(busqueda) ||
                       (empresa.email || '').toLowerCase().includes(busqueda);
            });
            
            aplicarFiltros();
        }

        function aplicarFiltros() {
            const estadoFiltro = document.getElementById('filtroEstado').value;
            const vendedorFiltro = document.getElementById('filtroVendedor').value;
            const fechaFiltro = document.getElementById('filtroFecha').value;
            
            let filtradas = empresasFiltradas;
            
            if (estadoFiltro) {
                filtradas = filtradas.filter(e => e.estado === estadoFiltro);
            }
            
            if (vendedorFiltro) {
                filtradas = filtradas.filter(e => e.vendedor_asignado === vendedorFiltro);
            }
            
            if (fechaFiltro) {
                filtradas = filtradas.filter(e => 
                    new Date(e.fecha_captura).toDateString() === new Date(fechaFiltro).toDateString()
                );
            }
            
            empresasFiltradas = filtradas;
            actualizarTabla();
        }

        function iniciarBusqueda() {
            const tipo = document.getElementById('tipoNegocio').value;
            const ubicacion = document.getElementById('ubicacion').value;
            
            if (!tipo || !ubicacion) {
                alert('Por favor, completa tipo de negocio y ubicación');
                return;
            }
            
            window.open(`/api/buscar/${tipo}/${ubicacion}?agente=busca_empresas_1`, '_blank');
            setTimeout(() => cargarEmpresas(), 3000);
        }

        async function actualizarCampo(id, campo, valor) {
            try {
                const response = await fetch('/api/actualizar_campo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ empresa_id: id, campo: campo, valor: valor })
                });
                
                const result = await response.json();
                if (!result.success) {
                    console.error('Error actualizando campo:', result.error);
                    alert('Error actualizando campo: ' + result.error);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error de conexión');
            }
        }

        async function exportarExcel() {
            try {
                window.open('/api/exportar_excel', '_blank');
            } catch (error) {
                console.error('Error exportando:', error);
                alert('Error exportando datos');
            }
        }

        function seleccionarTodos() {
            const selectAll = document.getElementById('selectAll');
            const checkboxes = document.querySelectorAll('.empresa-checkbox');
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
        }

        async function asignarMasivo() {
            const vendedor = document.getElementById('vendedorMasivo').value;
            const seleccionadas = document.querySelectorAll('.empresa-checkbox:checked');
            
            if (!vendedor) {
                alert('Selecciona un vendedor');
                return;
            }
            
            if (seleccionadas.length === 0) {
                alert('Selecciona empresas para asignar');
                return;
            }
            
            try {
                for (const checkbox of seleccionadas) {
                    await actualizarCampo(checkbox.value, 'vendedor_asignado', vendedor);
                }
                
                alert(`${seleccionadas.length} empresas asignadas a ${vendedor}`);
                cargarEmpresas();
                
            } catch (error) {
                console.error('Error asignando masivo:', error);
                alert('Error en asignación masiva');
            }
        }

        async function añadirEmpresaManual() {
            const nombre = document.getElementById('nombreManual').value;
            const telefono = document.getElementById('telefonoManual').value;
            const email = document.getElementById('emailManual').value;
            const estado = document.getElementById('estadoManual').value;
            
            if (!nombre) {
                alert('El nombre es obligatorio');
                return;
            }
            
            try {
                const response = await fetch('/api/añadir_manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nombre: nombre, telefono: telefono, email: email, estado: estado })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('Empresa añadida correctamente');
                    document.getElementById('nombreManual').value = '';
                    document.getElementById('telefonoManual').value = '';
                    document.getElementById('emailManual').value = '';
                    cargarEmpresas();
                } else {
                    alert('Error: ' + result.error);
                }
                
            } catch (error) {
                console.error('Error:', error);
                alert('Error de conexión');
            }
        }

        async function eliminarEmpresa(id) {
            if (confirm('¿Estás seguro de eliminar esta empresa?')) {
                try {
                    const response = await fetch(`/api/eliminar/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        alert('Empresa eliminada correctamente');
                        cargarEmpresas();
                    } else {
                        alert('Error: ' + result.error);
                    }
                    
                } catch (error) {
                    console.error('Error:', error);
                    alert('Error de conexión');
                }
            }
        }

        async function duplicarEmpresa(id) {
            try {
                const response = await fetch(`/api/duplicar/${id}`, { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    alert('Empresa duplicada correctamente');
                    cargarEmpresas();
                } else {
                    alert('Error: ' + result.error);
                }
                
            } catch (error) {
                console.error('Error:', error);
                alert('Error de conexión');
            }
        }

        async function confirmarLimpiar() {
            if (confirm('¿Estás SEGURO de eliminar TODAS las empresas? Esta acción no se puede deshacer.')) {
                if (confirm('¡ÚLTIMA CONFIRMACIÓN! Se eliminarán TODAS las empresas. ¿Continuar?')) {
                    try {
                        const response = await fetch('/api/limpiar_todo', { method: 'DELETE' });
                        const result = await response.json();
                        
                        if (result.success) {
                            alert(result.message);
                            cargarEmpresas();
                        } else {
                            alert('Error: ' + result.error);
                        }
                        
                    } catch (error) {
                        console.error('Error:', error);
                        alert('Error de conexión');
                    }
                }
            }
        }
    </script>
</body>
</html>'''
    
    return html_content

# ==========================================
# DASHBOARD SIMPLE
# ==========================================

@empresas_bp.route('/dashboard')
def dashboard():
    """Dashboard principal de empresas"""
    
    try:
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
                    <h2>⚡ Panel de Control Avanzado</h2>
                    <a href="/api/panel" class="btn success">🎯 Ir al Panel Principal</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f"Error cargando dashboard: {str(e)}", 500

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