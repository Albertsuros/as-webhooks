# sistema_seguimiento.py
import sqlite3
import json
import os
from datetime import datetime, timedelta

class SeguimientoTelefonico:
    def __init__(self, db_path="seguimiento_clientes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Crear tabla de seguimiento si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sesiones_clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_telefono TEXT NOT NULL,
                    codigo_servicio TEXT NOT NULL,
                    tipo_servicio TEXT NOT NULL,
                    email TEXT,
                    datos_natales TEXT,  -- JSON con datos completos
                    fecha_inicio DATETIME NOT NULL,
                    fecha_expiracion DATETIME NOT NULL,
                    estado TEXT DEFAULT 'activo',  -- activo, expirado, completado
                    puede_revolucion_solar BOOLEAN DEFAULT 0,
                    conversacion_completa TEXT,  -- JSON con historial
                    archivos_generados TEXT,  -- JSON con rutas de archivos
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Índices para búsquedas rápidas
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_telefono ON sesiones_clientes(numero_telefono)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_codigo ON sesiones_clientes(codigo_servicio)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_estado ON sesiones_clientes(estado)')
            
            conn.commit()
            conn.close()
            print("✅ Base de datos de seguimiento inicializada")
            
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")
    
    def calcular_fecha_expiracion(self, tipo_servicio):
        """Calcular fecha de expiración según tipo de servicio"""
        ahora = datetime.now()
        
        if tipo_servicio == 'psico_coaching_ia':
            return ahora + timedelta(days=90)  # 3 meses
        elif tipo_servicio == 'psico_coaching_ia_half':
            return ahora + timedelta(hours=48)  # 48h para extensión
        elif tipo_servicio.endswith('_half'):
            return ahora + timedelta(hours=48)  # 48h para todas las extensiones
        elif tipo_servicio in ['carta_astral_ia', 'revolucion_solar_ia', 'sinastria_ia', 'astrologia_horaria_ia']:
            return ahora + timedelta(hours=48)
        elif tipo_servicio == 'lectura_facial_ia':
            # Sin seguimiento especial (lectura facial es de 15 min)
            return ahora + timedelta(hours=1)  # 1 hora mínima
        else:
            # Fallback: 48 horas
            return ahora + timedelta(hours=48)
    
    def registrar_nueva_sesion(self, numero_telefono, codigo_servicio, tipo_servicio, email, datos_natales=None):
        """Registrar nueva sesión de cliente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            fecha_inicio = datetime.now()
            fecha_expiracion = self.calcular_fecha_expiracion(tipo_servicio)
            puede_revolucion_solar = 1 if tipo_servicio == 'carta_astral_ia' else 0
            
            cursor.execute('''
                INSERT INTO sesiones_clientes 
                (numero_telefono, codigo_servicio, tipo_servicio, email, datos_natales, 
                 fecha_inicio, fecha_expiracion, puede_revolucion_solar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (numero_telefono, codigo_servicio, tipo_servicio, email, 
                  json.dumps(datos_natales) if datos_natales else None,
                  fecha_inicio, fecha_expiracion, puede_revolucion_solar))
            
            sesion_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Nueva sesión registrada - ID: {sesion_id}")
            return sesion_id, fecha_expiracion
            
        except Exception as e:
            print(f"❌ Error registrando sesión: {e}")
            return None, None
    
    def buscar_sesion_activa(self, numero_telefono):
        """Buscar sesión activa para un número de teléfono"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            ahora = datetime.now()
            
            cursor.execute('''
                SELECT id, codigo_servicio, tipo_servicio, email, datos_natales,
                       fecha_expiracion, puede_revolucion_solar, conversacion_completa,
                       archivos_generados, estado
                FROM sesiones_clientes 
                WHERE numero_telefono = ? 
                  AND estado IN ('activo', 'pendiente_fotos')
                  AND fecha_inicio > ?  -- 60h técnicas vs 48h comerciales
                ORDER BY fecha_inicio DESC
                LIMIT 1
            ''', (numero_telefono, ahora - timedelta(hours=60)))
            
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado:
                return {
                    'id': resultado[0],
                    'codigo_servicio': resultado[1],
                    'tipo_servicio': resultado[2],
                    'email': resultado[3],
                    'datos_natales': json.loads(resultado[4]) if resultado[4] else None,
                    'fecha_expiracion': resultado[5],
                    'puede_revolucion_solar': bool(resultado[6]),
                    'conversacion_completa': json.loads(resultado[7]) if resultado[7] else [],
                    'archivos_generados': json.loads(resultado[8]) if resultado[8] else {},
                    'estado': resultado[9]
                }
            return None
            
        except Exception as e:
            print(f"❌ Error buscando sesión activa: {e}")
            return None
    
    def actualizar_conversacion(self, sesion_id, nueva_interaccion):
        """Actualizar conversación de una sesión"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener conversación actual
            cursor.execute('SELECT conversacion_completa FROM sesiones_clientes WHERE id = ?', (sesion_id,))
            resultado = cursor.fetchone()
            
            if resultado:
                conversacion_actual = json.loads(resultado[0]) if resultado[0] else []
                conversacion_actual.append({
                    'timestamp': datetime.now().isoformat(),
                    'contenido': nueva_interaccion
                })
                
                cursor.execute('''
                    UPDATE sesiones_clientes 
                    SET conversacion_completa = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (json.dumps(conversacion_actual), sesion_id))
                
                conn.commit()
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error actualizando conversación: {e}")
            return False
            
    def limpiar_sesiones_test(self):
        """Limpiar SOLO las sesiones de prueba, manteniendo las reales"""
        try:
            # Números de teléfono específicos para pruebas
            numeros_test = [
                "34600000000",
                "34600000001", 
                "34600000002"
            ]
            
            # Códigos de servicio específicos para pruebas
            codigos_test = [
                "RS_999888",
                "RS_888777", 
                "RS_333444",
                "AI_111222"
            ]
            
            # CREAR CONEXIÓN TEMPORAL (como hace el resto de la clase)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Limpiar por números de teléfono de prueba
            for numero in numeros_test:
                query = "DELETE FROM sesiones_clientes WHERE numero_telefono = ?"
                cursor.execute(query, (numero,))
                
            # Limpiar por códigos de servicio de prueba
            for codigo in codigos_test:
                query = "DELETE FROM sesiones_clientes WHERE codigo_servicio = ?"
                cursor.execute(query, (codigo,))
            
            conn.commit()
            cursor.close()
            conn.close()  # CERRAR CONEXIÓN
            
            print(f"🧹 Sesiones de prueba limpiadas (manteniendo sesiones reales)")
            
        except Exception as e:
            print(f"Error limpiando sesiones de prueba: {e}")
    
    def finalizar_sesion(self, sesion_id, estado='completado'):
        """Finalizar una sesión"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE sesiones_clientes 
                SET estado = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (estado, sesion_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error finalizando sesión: {e}")
            return False
            
    def actualizar_estado_sesion(self, sesion_id, nuevo_estado):
        """Actualizar estado de una sesión"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE sesiones_clientes 
                SET estado = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (nuevo_estado, sesion_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Estado actualizado a '{nuevo_estado}' para sesión {sesion_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error actualizando estado: {e}")
            return False
    
    def reactivar_codigo(self, numero_telefono, codigo_servicio):
        """Reactivar código por llamada cortada"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Buscar sesión del código
            cursor.execute('''
                SELECT id, tipo_servicio FROM sesiones_clientes 
                WHERE numero_telefono = ? AND codigo_servicio = ?
                ORDER BY fecha_inicio DESC LIMIT 1
            ''', (numero_telefono, codigo_servicio))
            
            resultado = cursor.fetchone()
            
            if resultado:
                sesion_id, tipo_servicio = resultado
                nueva_expiracion = self.calcular_fecha_expiracion(tipo_servicio)
                
                cursor.execute('''
                    UPDATE sesiones_clientes 
                    SET estado = 'activo', fecha_expiracion = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (nueva_expiracion, sesion_id))
                
                conn.commit()
                conn.close()
                return True
            
            conn.close()
            return False
            
        except Exception as e:
            print(f"❌ Error reactivando código: {e}")
            return False
    
    def limpiar_sesiones_expiradas(self):
        """Limpiar sesiones expiradas (ejecutar diariamente)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Marcar como expiradas las sesiones que pasaron 7 días
            fecha_limite = datetime.now() - datetime.timedelta(days=7)
            
            cursor.execute('''
                UPDATE sesiones_clientes 
                SET estado = 'expirado'
                WHERE estado = 'activo' 
                  AND fecha_inicio < ?
            ''', (fecha_limite,))
            
            sesiones_expiradas = cursor.rowcount
            
            # Eliminar datos sensibles de sesiones muy antiguas (30+ días)
            fecha_limite_borrado = datetime.now() - datetime.timedelta(days=30)
            
            cursor.execute('''
                UPDATE sesiones_clientes 
                SET datos_natales = NULL, conversacion_completa = NULL, email = NULL
                WHERE fecha_inicio < ?
            ''', (fecha_limite_borrado,))
            
            datos_borrados = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print(f"✅ Limpieza: {sesiones_expiradas} sesiones expiradas, {datos_borrados} datos borrados")
            return sesiones_expiradas, datos_borrados
            
        except Exception as e:
            print(f"❌ Error en limpieza: {e}")
            return 0, 0
    
    def obtener_estadisticas(self):
        """Obtener estadísticas de uso"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Estadísticas generales
            cursor.execute('SELECT COUNT(*) FROM sesiones_clientes')
            total_sesiones = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM sesiones_clientes WHERE estado = "activo"')
            sesiones_activas = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM sesiones_clientes WHERE estado = "completado"')
            sesiones_completadas = cursor.fetchone()[0]
            
            # Por tipo de servicio
            cursor.execute('''
                SELECT tipo_servicio, COUNT(*) 
                FROM sesiones_clientes 
                GROUP BY tipo_servicio
            ''')
            por_servicio = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_sesiones': total_sesiones,
                'sesiones_activas': sesiones_activas,
                'sesiones_completadas': sesiones_completadas,
                'por_servicio': por_servicio
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return {}

# Función para integrar en Sofia
def obtener_numero_telefono_desde_vapi(data):
    """
    Extraer número de teléfono desde datos de Vapi
    PERSONALIZAR según formato de Vapi
    """
    # Ejemplo - ajustar según formato real de Vapi
    call_data = data.get('call', {})
    customer = call_data.get('customer', {})
    
    # Posibles campos donde puede estar el número
    numero = (
        customer.get('number') or 
        call_data.get('phoneNumber') or 
        data.get('from') or
        data.get('caller_id')
    )
    
    if numero:
        # Limpiar formato (+34 937 496 233 -> +34937496233)
        numero = ''.join(filter(str.isdigit, numero.replace('+', '+')))
    
    return numero

# Función de prueba
def test_sistema_seguimiento():
    """Probar el sistema de seguimiento"""
    print("🧪 Probando sistema de seguimiento...")
    
    seguimiento = SeguimientoTelefonico()
    
    # Simular nueva sesión
    numero = "+34937496233"
    codigo = "AI_123456"
    email = "test@cliente.com"
    
    sesion_id, expiracion = seguimiento.registrar_nueva_sesion(
        numero, codigo, 'carta_astral_ia', email
    )
    
    print(f"📝 Sesión creada: ID {sesion_id}, expira: {expiracion}")
    
    # Buscar sesión
    sesion = seguimiento.buscar_sesion_activa(numero)
    print(f"🔍 Sesión encontrada: {sesion}")
    
    # Estadísticas
    stats = seguimiento.obtener_estadisticas()
    print(f"📊 Estadísticas: {stats}")

if __name__ == "__main__":
    test_sistema_seguimiento()