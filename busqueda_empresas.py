# busqueda_empresas.py
import requests
import sqlite3
import random
import time
from datetime import datetime
from flask import jsonify

class BuscadorEmpresas:
    def __init__(self, db_path="data/empresas.db"):
        self.db_path = db_path
        self.crear_tabla()
    
    def crear_tabla(self):
        """Crear tabla de empresas si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS empresas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    telefono TEXT,
                    email TEXT,
                    web TEXT,
                    direccion TEXT,
                    sector TEXT NOT NULL,
                    ubicacion TEXT NOT NULL,
                    agente_captura TEXT NOT NULL,
                    estado TEXT DEFAULT 'pendiente',
                    fecha_captura DATETIME DEFAULT CURRENT_TIMESTAMP,
                    vendedor_asignado TEXT,
                    contacto_nombre TEXT,
                    contacto_cargo TEXT,
                    resultado_llamada TEXT,
                    notas TEXT,
                    email_enviado BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Tabla empresas creada/verificada")
            
        except Exception as e:
            print(f"❌ Error creando tabla: {e}")
    
    def buscar_empresas_simuladas(self, sector, ubicacion, cantidad=5):
        """
        Simula búsqueda de empresas (para demo)
        En producción, aquí harías web scraping real
        """
        empresas = []
        
        # Generar empresas de ejemplo realistas
        tipos_empresa = [
            f"{sector.capitalize()} {ubicacion}",
            f"Grupo {sector.capitalize()}",
            f"{ubicacion} {sector.capitalize()} Center",
            f"{sector.capitalize()} Barcelona S.L.",
            f"Asociación {sector.capitalize()} {ubicacion}"
        ]
        
        for i in range(cantidad):
            empresa = {
                'nombre': f"{random.choice(tipos_empresa)} {i+1}",
                'telefono': f"93{random.randint(1000000, 9999999)}",
                'email': f"info@{sector}{i+1}.es",
                'web': f"https://www.{sector}{i+1}.es",
                'direccion': f"Calle {sector.capitalize()} {random.randint(1, 100)}, {ubicacion}",
                'sector': sector,
                'ubicacion': ubicacion
            }
            empresas.append(empresa)
            
        return empresas
    
    def buscar_empresas_google(self, sector, ubicacion, cantidad=10):
        """
        Búsqueda real en Google (versión básica)
        """
        try:
            # Para demo, usamos búsqueda simulada
            # En producción real, usar APIs como:
            # - Google Places API
            # - Scraping con BeautifulSoup
            # - APIs de directorios de empresas
            
            query = f"{sector} {ubicacion} teléfono email"
            print(f"🔍 Buscando: {query}")
            
            # Simular delay de búsqueda real
            time.sleep(2)
            
            return self.buscar_empresas_simuladas(sector, ubicacion, cantidad)
            
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            return []
    
    def guardar_empresa(self, empresa, agente_id):
        """Guardar empresa en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar si ya existe
            cursor.execute(
                'SELECT id FROM empresas WHERE nombre = ? OR telefono = ?',
                (empresa['nombre'], empresa['telefono'])
            )
            
            if cursor.fetchone():
                conn.close()
                return False  # Ya existe
            
            # Insertar nueva empresa
            cursor.execute('''
                INSERT INTO empresas (
                    nombre, telefono, email, web, direccion,
                    sector, ubicacion, agente_captura, estado,
                    fecha_captura
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                empresa['nombre'],
                empresa['telefono'],
                empresa['email'],
                empresa['web'],
                empresa['direccion'],
                empresa['sector'],
                empresa['ubicacion'],
                agente_id,
                'pendiente',
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error guardando empresa: {e}")
            return False
    
    def ejecutar_busqueda(self, sector, ubicacion, agente_id, cantidad=10):
        """Ejecutar búsqueda completa"""
        try:
            print(f"🚀 Agente {agente_id} iniciando búsqueda: {sector} en {ubicacion}")
            
            # Buscar empresas
            empresas_encontradas = self.buscar_empresas_google(sector, ubicacion, cantidad)
            
            # Guardar en base de datos
            empresas_guardadas = 0
            for empresa in empresas_encontradas:
                if self.guardar_empresa(empresa, agente_id):
                    empresas_guardadas += 1
                    print(f"✅ Guardada: {empresa['nombre']}")
            
            resultado = {
                'success': True,
                'agente': agente_id,
                'sector': sector,
                'ubicacion': ubicacion,
                'empresas_encontradas': len(empresas_encontradas),
                'empresas_guardadas': empresas_guardadas,
                'timestamp': datetime.now().isoformat(),
                'message': f'Búsqueda completada: {empresas_guardadas} nuevas empresas guardadas'
            }
            
            print(f"🎯 Búsqueda completada: {empresas_guardadas} nuevas empresas")
            return resultado
            
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            return {
                'success': False,
                'error': str(e),
                'agente': agente_id
            }
    
    def obtener_empresas(self, estado=None, vendedor=None, limit=100):
        """Obtener empresas de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if estado:
                cursor.execute(
                    'SELECT * FROM empresas WHERE estado = ? ORDER BY fecha_captura DESC LIMIT ?',
                    (estado, limit)
                )
            elif vendedor:
                cursor.execute(
                    'SELECT * FROM empresas WHERE vendedor_asignado = ? OR vendedor_asignado IS NULL ORDER BY fecha_captura DESC LIMIT ?',
                    (vendedor, limit)
                )
            else:
                cursor.execute(
                    'SELECT * FROM empresas ORDER BY fecha_captura DESC LIMIT ?',
                    (limit,)
                )
            
            columnas = [description[0] for description in cursor.description]
            empresas = []
            
            for fila in cursor.fetchall():
                empresa = dict(zip(columnas, fila))
                empresas.append(empresa)
            
            conn.close()
            
            return {
                'success': True,
                'empresas': empresas,
                'total': len(empresas)
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo empresas: {e}")
            return {
                'success': False,
                'error': str(e),
                'empresas': []
            }
    
    def asignar_vendedor(self, empresa_id, vendedor):
        """Asignar empresa a vendedor"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE empresas SET vendedor_asignado = ?, estado = ? WHERE id = ?',
                (vendedor, 'asignada', empresa_id)
            )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': f'Empresa asignada a {vendedor}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Instancia global del buscador
buscador = BuscadorEmpresas()