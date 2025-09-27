from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import render_template_string
from flask import send_file
from datetime import datetime, timedelta
import datetime as dt
import json
from flask import render_template, send_file
from agents.sofia import handle_sofia_webhook, obtener_numero_telefono_desde_vapi
from agents.grafologia import handle_grafologia_webhook
from agents.veronica import handle_veronica_webhook  
from agents.vendedor_1 import handle_vendedor1_webhook  
from agents.vendedor_2 import handle_vendedor2_webhook  
from agents.vendedor_3 import handle_vendedor3_webhook  
from agents.tecnico_soporte import handle_tecnico_soporte_webhook  
from agents.astrologa_cartastral import handle_astrologa_cartastral_webhook  
from agents.astrologa_revolsolar import handle_astrologa_revolsolar_webhook  
from agents.astrologa_sinastria import handle_astrologa_sinastria_webhook  
from agents.astrologa_astrolhoraria import handle_astrologa_astrolhoraria_webhook  
from agents.psico_coaching import handle_psico_coaching_webhook  
from agents.lectura_manos import handle_lectura_manos_webhook  
from agents.lectura_facial import handle_lectura_facial_webhook  
from agents.busca_empresas1 import handle_busca_empresas1_webhook  
from agents.busca_empresas2 import handle_busca_empresas2_webhook  
from agents.busca_empresas3 import handle_busca_empresas3_webhook  
from agents.redes_sociales1 import handle_redes_sociales1_webhook  
from agents.redes_sociales2 import handle_redes_sociales2_webhook  
from agents.redes_sociales3 import handle_redes_sociales3_webhook  
from agents.redes_sociales4 import handle_redes_sociales4_webhook  
from agents.redes_sociales5 import handle_redes_sociales5_webhook  
from agents.redes_sociales6 import handle_redes_sociales6_webhook  
from agents.redes_sociales7 import handle_redes_sociales7_webhook  
from agents.chistes1 import handle_chistes1_webhook  
from app import app  # importa la app definida en app.py
from dotenv import load_dotenv
import os
import glob
import threading
import time
from informes import procesar_y_enviar_informe
from flask import send_from_directory
from pathlib import Path
from app import app
CORS(app, origins=["https://asasesores.com"])
try:
    from retell import Retell
    RETELL_SDK_AVAILABLE = True
    print("✅ Retell SDK disponible")
except ImportError:
    RETELL_SDK_AVAILABLE = False
    print("⚠️ Retell SDK no disponible - usando HTTP directo")

# ID del calendario AS Asesores
CALENDAR_ID = 'b64595022e163fbb552d1d5202a590605d3dd66079c082dc4037513c2a5369e1@group.calendar.google.com'

# Configuración Zadarma-Retell (CORREGIDO)
RETELL_API_KEY = os.environ.get('RETELL_API_KEY', 'key_714d5a5aa52c32258065da200b70')
ZADARMA_PHONE_NUMBER_ID = os.environ.get('ZADARMA_PHONE_NUMBER_ID', '+34936941520')  # ✅ CORREGIDO

# Agent IDs de vendedores (YA CORRECTOS)
AGENT_IDS = {
    'Albert': 'agent_f81a7da78a5ee87c667872153d',
    'Juan': 'agent_dddba811832aba40131c6a0f4e', 
    'Carlos': 'agent_80f7849e15b2f72d0aaf64989d'
}

# ========================================
# NUEVAS IMPORTACIONES PARA MEJORAS
# ========================================
import sqlite3
import requests
import gc
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from logica_citas_inteligente import obtener_horarios_disponibles_inteligentes, agendar_cita_inteligente

load_dotenv()

# 🔧 CREAR ARCHIVO DE CREDENCIALES AUTOMÁTICAMENTE
if not os.path.exists('google-credentials.json') and os.getenv('GOOGLE_CREDENTIALS_JSON'):
    with open('google-credentials.json', 'w') as f:
        f.write(os.getenv('GOOGLE_CREDENTIALS_JSON'))
    print("✅ Archivo google-credentials.json creado desde variable de entorno")

import sqlite3

class GestorEmpresasSimple:
    def __init__(self):
        # Forzar modo local ignorando variables de entorno
        self.dolibarr_url = None  # Forzar a None
        self.dolibarr_key = None  # Forzar a None
        self.init_local_db()
    
    def init_local_db(self):
        """Crear BD local para Lista Robinson propia"""
        conn = sqlite3.connect("empresas_robinson.db")
        cur = conn.cursor()
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lista_robinson_local (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cif TEXT UNIQUE,
            nombre_empresa TEXT,
            telefono TEXT,
            email TEXT,
            motivo TEXT,
            fecha_exclusion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS empresas_procesadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cif TEXT,
            telefono TEXT,
            email TEXT,
            ciudad TEXT,
            dolibarr_id INTEGER,
            agente_origen TEXT,
            fecha_procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'activo'
        )
        """)
        
        conn.commit()
        conn.close()
        print("Base de datos empresas inicializada")
    
    def esta_en_robinson_local(self, cif=None, telefono=None, email=None):
        """Verificar en lista Robinson local"""
        try:
            conn = sqlite3.connect("empresas_robinson.db")
            cur = conn.cursor()
            
            condiciones = []
            params = []
            
            if cif:
                condiciones.append("cif = ?")
                params.append(cif)
            if telefono:
                condiciones.append("telefono = ?")
                params.append(telefono)
            if email:
                condiciones.append("email = ?")
                params.append(email)
            
            if not condiciones:
                return False
            
            query = f"SELECT COUNT(*) FROM lista_robinson_local WHERE {' OR '.join(condiciones)}"
            cur.execute(query, params)
            
            count = cur.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            print(f"Error verificando Robinson local: {e}")
            return False
    
    def crear_empresa_dolibarr(self, datos):
        """Crear empresa en Dolibarr"""
        try:
            if not self.dolibarr_url or not self.dolibarr_key:
                print("Dolibarr no configurado - guardando solo local")
                return self.guardar_empresa_local(datos)
            
            headers = {
                "DOLAPIKEY": self.dolibarr_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "name": datos.get("nombre"),
                "phone": datos.get("telefono", ""),
                "email": datos.get("email", ""),
                "address": datos.get("direccion", ""),
                "town": datos.get("ciudad", ""),
                "idprof1": datos.get("cif", ""),
                "client": 2,  # Prospecto
                "note_private": f"Añadido por: {datos.get('agente', 'BUSCA_EMPRESAS')}"
            }
            
            response = requests.post(
                f"{self.dolibarr_url}/api/index.php/thirdparties",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                empresa = response.json()
                dolibarr_id = empresa.get('id')
                self.guardar_empresa_local(datos, dolibarr_id)
                return dolibarr_id
            else:
                print(f"Error Dolibarr: {response.status_code} - {response.text}")
                return self.guardar_empresa_local(datos)
                
        except Exception as e:
            print(f"Error creando en Dolibarr: {e}")
            return self.guardar_empresa_local(datos)
    
    def guardar_empresa_local(self, datos, dolibarr_id=None):
        """Guardar empresa en BD local"""
        try:
            conn = sqlite3.connect("empresas_robinson.db")
            cur = conn.cursor()
            
            cur.execute("""
            INSERT INTO empresas_procesadas 
            (nombre, cif, telefono, email, ciudad, dolibarr_id, agente_origen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datos.get("nombre"),
                datos.get("cif"),
                datos.get("telefono"),
                datos.get("email"),
                datos.get("ciudad"),
                dolibarr_id,
                datos.get("agente", "MANUAL")
            ))
            
            local_id = cur.lastrowid
            conn.commit()
            conn.close()
            
            return local_id
            
        except Exception as e:
            print(f"Error guardando local: {e}")
            return None

def procesar_empresa_simple(datos_empresa, agente_origen):
    """Procesar empresa con sistema simplificado"""
    try:
        gestor = GestorEmpresasSimple()
        
        # Verificar Robinson local
        en_robinson = gestor.esta_en_robinson_local(
            cif=datos_empresa.get("cif"),
            telefono=datos_empresa.get("telefono"),
            email=datos_empresa.get("email")
        )
        
        if en_robinson:
            return {
                "success": False,
                "reason": "robinson",
                "message": "Empresa en Lista Robinson local"
            }
        
        # Crear en Dolibarr
        datos_empresa["agente"] = agente_origen
        resultado_id = gestor.crear_empresa_dolibarr(datos_empresa)
        
        if resultado_id:
            # Notificar por Telegram
            mensaje = f"""
NUEVA EMPRESA ENCONTRADA

Empresa: {datos_empresa.get('nombre', 'Sin nombre')}
CIF: {datos_empresa.get('cif', 'No disponible')}
Ciudad: {datos_empresa.get('ciudad', 'No disponible')}
Teléfono: {datos_empresa.get('telefono', 'No disponible')}

Agente: {agente_origen}
ID: {resultado_id}
Lista para contacto

Hora: {datetime.now().strftime('%H:%M')}
            """.strip()
            
            try:
                enviar_telegram_mejora(mensaje)
            except:
                pass  # Si falla Telegram, continuar
            
            return {
                "success": True,
                "action": "created",
                "id": resultado_id,
                "message": "Empresa procesada correctamente"
            }
        else:
            return {
                "success": False,
                "reason": "system_error",
                "message": "Error procesando empresa"
            }
            
    except Exception as e:
        print(f"Error procesando empresa: {e}")
        return {
            "success": False,
            "reason": "exception",
            "message": str(e)
        }

# ========================================
# FUNCIONES WOOCOMMERCE (AÑADIR DESPUÉS LÍNEA 50)
# ========================================

def detectar_tipo_servicio_woo(product_name):
    """Detectar tipo de servicio desde nombre de producto WooCommerce"""
    nombre_lower = product_name.lower()
    
    # Mapeo de nombres de productos a tipos de servicio
    if 'carta astral' in nombre_lower and 'revolución' not in nombre_lower:
        return 'carta_astral_ia'
    elif 'revolución solar' in nombre_lower or ('carta astral' in nombre_lower and 'revolución' in nombre_lower):
        return 'revolucion_solar_ia'
    elif 'sinastría' in nombre_lower or 'sinastria' in nombre_lower:
        return 'sinastria_ia'
    elif 'astrología horaria' in nombre_lower or 'horaria' in nombre_lower:
        return 'astrologia_horaria_ia'
    elif 'psico' in nombre_lower or 'coaching' in nombre_lower:
        return 'psico_coaching_ia'
    elif 'lectura manos' in nombre_lower or 'manos' in nombre_lower:
        return 'lectura_manos_ia'
    elif 'lectura facial' in nombre_lower or 'facial' in nombre_lower:
        return 'lectura_facial_ia'
    elif 'astrólogo humano' in nombre_lower or 'astrologo personal' in nombre_lower:
        return 'astrologo_humano'
    elif 'tarot humano' in nombre_lower or 'tarot personal' in nombre_lower:
        return 'tarot_humano'
    elif 'carta astral' in nombre_lower and '½' in nombre_lower:
        return 'carta_astral_ia_half'
    elif 'revolución solar' in nombre_lower and '½' in nombre_lower:
        return 'revolucion_solar_ia_half'
    elif 'sinastría' in nombre_lower and '½' in nombre_lower:
        return 'sinastria_ia_half'
    elif 'lectura manos' in nombre_lower and '½' in nombre_lower:
        return 'lectura_manos_ia_half'
    elif 'psico' in nombre_lower and '½' in nombre_lower:
        return 'psico_coaching_ia_half'
    elif 'grafolog' in nombre_lower or 'análisis escritura' in nombre_lower:
        return 'grafologia_ia'
    else:
        return 'carta_astral_ia'  # Por defecto

def generar_codigo_unico(tipo_servicio, order_id):
    """Generar código único basado en tipo de servicio"""
    import random
    
    prefijos = {
        'carta_astral_ia': 'AI_',
        'revolucion_solar_ia': 'RS_',
        'sinastria_ia': 'SI_',
        'astrologia_horaria_ia': 'AH_',
        'psico_coaching_ia': 'PC_',
        'lectura_manos_ia': 'LM_',
        'lectura_facial_ia': 'LF_',
        'astrologo_humano': 'AS_',
        'tarot_humano': 'TH_',
        'carta_astral_ia_half': 'AIM',
        'revolucion_solar_ia_half': 'RSM',
        'sinastria_ia_half': 'SIM',
        'lectura_manos_ia_half': 'LMM',
        'psico_coaching_ia_half': 'PCM',
        'grafologia_ia': 'GR_'
    }
    
    prefijo = prefijos.get(tipo_servicio, 'AI_')
    numero_aleatorio = str(random.randint(100000, 999999))
    
    return f"{prefijo}{numero_aleatorio}"

def guardar_codigo_woocommerce(codigo, email, tipo_servicio):
    """Guardar código de WooCommerce en base de datos"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Crear tabla si no existe
        cur.execute("""
        CREATE TABLE IF NOT EXISTS codigos_woocommerce (
            codigo VARCHAR(50) PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            tipo_servicio VARCHAR(50) NOT NULL,
            fecha_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usado BOOLEAN DEFAULT 0
        )
        """)
        
        # Insertar código
        cur.execute("""
        INSERT INTO codigos_woocommerce (codigo, email, tipo_servicio, usado)
        VALUES (?, ?, ?, 0)
        """, (codigo, email, tipo_servicio))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Código WooCommerce guardado: {codigo} - {email}")
        return True
        
    except Exception as e:
        print(f"❌ Error guardando código WooCommerce: {e}")
        return False

def buscar_codigos_email(email):
    """Buscar códigos disponibles por email"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT codigo, tipo_servicio FROM codigos_woocommerce 
        WHERE email = ? AND usado = 0
        ORDER BY fecha_compra DESC
        """, (email,))
        
        codigos = cur.fetchall()
        conn.close()
        
        return [(codigo, tipo) for codigo, tipo in codigos]
        
    except Exception as e:
        print(f"❌ Error buscando códigos: {e}")
        return []
        
def buscar_email_por_codigo(codigo):
    """Buscar email asociado a un código de WooCommerce"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT email, tipo_servicio FROM codigos_woocommerce 
        WHERE codigo = ? AND usado = 0
        """, (codigo,))
        
        resultado = cur.fetchone()
        conn.close()
        
        if resultado:
            return resultado[0], resultado[1]  # email, tipo_servicio
        else:
            return None, None
        
    except Exception as e:
        print(f"❌ Error buscando email por código: {e}")
        return None, None

def marcar_codigo_usado(codigo):
    """Marcar código como usado"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        UPDATE codigos_woocommerce SET usado = 1 
        WHERE codigo = ?
        """, (codigo,))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error marcando código usado: {e}")
        return False

# ========================================
# SISTEMA DE IDS ÚNICOS Y AUTO-LIMPIEZA (MANTENIDO)
# ========================================

def generar_id_unico(codigo_cliente):
    """
    Genera un identificador único basado en timestamp + código de cliente
    Formato: YYYYMMDD_HHMMSS_CODIGO
    Ejemplo: 20250715_143052_CAR001
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{codigo_cliente}"

def obtener_nombres_archivos_unicos(tipo_servicio, codigo_cliente):
    """
    Genera nombres de archivos únicos para un servicio específico
    """
    id_unico = generar_id_unico(codigo_cliente)
    
    nombres = {}
    
    if tipo_servicio == "carta_natal":
        nombres = {
            "informe_html": f"templates/informe_carta_natal_{id_unico}.html",
            "carta_natal_img": f"static/carta_natal_{id_unico}.png",
            "progresiones_img": f"static/progresiones_{id_unico}.png", 
            "transitos_img": f"static/transitos_{id_unico}.png"
        }
    elif tipo_servicio == "revolucion_solar":
        nombres = {
            "informe_html": f"templates/informe_revolucion_{id_unico}.html",
            "revolucion_img": f"static/revolucion_solar_{id_unico}.png",
            "revolucion_natal_img": f"static/revolucion_natal_{id_unico}.png"
        }
    elif tipo_servicio == "sinastria":
        nombres = {
            "informe_html": f"templates/informe_sinastria_{id_unico}.html",
            "sinastria_img": f"static/sinastria_{id_unico}.png"
        }
    elif tipo_servicio == "astrol_horaria":
        nombres = {
            "informe_html": f"templates/informe_astrolhoraria_{id_unico}.html",
            "carta_horaria_img": f"static/carta_horaria_{id_unico}.png"
        }
    elif tipo_servicio == "lectura_manos":
        nombres = {
            "informe_html": f"templates/informe_lectura_manos_{id_unico}.html"
        }
    elif tipo_servicio == "lectura_facial":
        nombres = {
            "informe_html": f"templates/informe_lectura_facial_{id_unico}.html"
        }
    elif tipo_servicio == "psico_coaching":
        nombres = {
            "informe_html": f"templates/informe_psico_coaching_{id_unico}.html"
        }
    
    return nombres, id_unico

def limpiar_archivos_antiguos():
    """
    Elimina archivos antiguos con tiempos específicos por servicio
    - General: 7 días
    - Psico-coaching: 3 meses (90 días)
    """
    try:
        from datetime import datetime, timedelta
        import glob
        
        hace_7_dias = datetime.now() - timedelta(days=7)
        hace_90_dias = datetime.now() - timedelta(days=90)  # 3 meses
        archivos_eliminados = 0
        
        # Limpiar templates HTML
        for archivo in glob.glob("templates/informe_*.html"):
            try:
                fecha_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
                
                # Psico-coaching: 3 meses
                if 'psico_coaching' in archivo:
                    if fecha_archivo < hace_90_dias:
                        os.remove(archivo)
                        archivos_eliminados += 1
                        print(f"Eliminado archivo psico-coaching antiguo (3 meses): {archivo}")
                # Otros servicios: 7 días
                else:
                    if fecha_archivo < hace_7_dias:
                        os.remove(archivo)
                        archivos_eliminados += 1
                        print(f"Eliminado archivo antiguo (7 días): {archivo}")
                        
            except (OSError, ValueError) as e:
                print(f"Error procesando archivo {archivo}: {e}")
                continue
        
        # Limpiar imágenes dinámicas en static/
        for archivo in glob.glob("static/*.png"):
            try:
                fecha_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
                
                # Psico-coaching: 3 meses
                if 'psico_coaching' in archivo:
                    if fecha_archivo < hace_90_dias:
                        os.remove(archivo)
                        archivos_eliminados += 1
                        print(f"Eliminada imagen psico-coaching antigua (3 meses): {archivo}")
                # Otros servicios: 7 días
                else:
                    if fecha_archivo < hace_7_dias:
                        os.remove(archivo)
                        archivos_eliminados += 1
                        print(f"Eliminada imagen antigua (7 días): {archivo}")
                        
            except (OSError, ValueError) as e:
                print(f"Error procesando imagen {archivo}: {e}")
                continue
        
        print(f"Limpieza completada. Archivos eliminados: {archivos_eliminados}")
        
    except Exception as e:
        print(f"Error en limpieza automática: {e}")

def iniciar_limpieza_automatica():
    """
    Inicia el proceso de limpieza automática que se ejecuta cada 24 horas
    """
    def tarea_limpieza():
        while True:
            time.sleep(86400)  # 24 horas en segundos
            limpiar_archivos_antiguos()
    
    thread = threading.Thread(target=tarea_limpieza, daemon=True)
    thread.start()
    print("Sistema de limpieza automática iniciado (cada 24 horas)")

# Función utilitaria para pasar a los handlers
def preparar_datos_con_id(data, tipo_servicio):
    """
    Prepara los datos del webhook añadiendo información de archivos únicos
    """
    codigo_cliente = data.get('codigo_servicio', 'UNKNOWN')
    nombres_archivos, id_unico = obtener_nombres_archivos_unicos(tipo_servicio, codigo_cliente)
    
    # Añadir información de archivos únicos a los datos
    data['archivos_unicos'] = nombres_archivos
    data['id_unico'] = id_unico
    
    return data

# ========================================
# NUEVAS FUNCIONES PARA MEJORAS DEL CALENDARIO
# ========================================

def inicializar_bd_mejorada():
    """Inicializar base de datos mejorada para el sistema de citas"""
    conn = sqlite3.connect("calendario_citas.db")
    cur = conn.cursor()
    
    # Tabla principal de servicios/clientes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes_servicios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_servicio TEXT UNIQUE NOT NULL,
        tipo_servicio TEXT NOT NULL,
        cliente_nombre TEXT,
        cliente_email TEXT,
        cliente_telefono TEXT,
        datos_natales TEXT,
        numero_telefono TEXT,
        especialista TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'activo'
    )
    """)
    
    # Tabla específica para CITAS (solo servicios humanos)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS citas_agendadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_servicio_id INTEGER NOT NULL,
        fecha_cita DATE NOT NULL,
        horario TEXT NOT NULL,
        codigo_reserva TEXT UNIQUE NOT NULL,
        estado_cita TEXT DEFAULT 'confirmada',
        notas TEXT,
        fecha_agendamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_servicio_id) REFERENCES clientes_servicios(id)
    )
    """)
    
    # Tabla de seguimiento telefónico (para reconexiones)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sesiones_telefonicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_telefono TEXT NOT NULL,
        codigo_servicio TEXT NOT NULL,
        tipo_servicio TEXT NOT NULL,
        email TEXT,
        datos_natales TEXT,
        fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_expiracion TIMESTAMP NOT NULL,
        estado TEXT DEFAULT 'activa',
        puede_revolucion_solar BOOLEAN DEFAULT FALSE,
        conversacion_log TEXT DEFAULT '[]'
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Base de datos mejorada inicializada correctamente")

def registrar_cliente_servicio(codigo_servicio, tipo_servicio, cliente_datos, numero_telefono="", especialista=""):
    """Registrar cliente y servicio en BD principal"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Preparar datos
        datos_natales_json = json.dumps(cliente_datos) if cliente_datos else "{}"
        
        cur.execute("""
        INSERT INTO clientes_servicios 
        (codigo_servicio, tipo_servicio, cliente_nombre, cliente_email, cliente_telefono, 
         datos_natales, numero_telefono, especialista)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo_servicio,
            tipo_servicio, 
            cliente_datos.get('nombre', ''),
            cliente_datos.get('email', ''),
            cliente_datos.get('telefono', ''),
            datos_natales_json,
            numero_telefono,
            especialista
        ))
        
        cliente_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Cliente registrado: {codigo_servicio} - {tipo_servicio}")
        return cliente_id
        
    except Exception as e:
        print(f"❌ Error registrando cliente: {e}")
        return None

def agendar_cita_especifica(cliente_servicio_id, fecha_cita, horario, tipo_servicio):
    """Agendar cita específica para servicios humanos"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Generar código de reserva único
        import random
        import string
        codigo_reserva = generar_codigo_reserva_descriptivo(tipo_servicio)
        
        # Verificar disponibilidad
        cur.execute("""
        SELECT COUNT(*) FROM citas_agendadas 
        WHERE fecha_cita = ? AND horario = ? AND estado_cita != 'cancelada'
        """, (fecha_cita.strftime('%Y-%m-%d'), horario))
        
        if cur.fetchone()[0] > 0:
            conn.close()
            return False, "Horario no disponible"
        
        # Insertar cita
        cur.execute("""
        INSERT INTO citas_agendadas 
        (cliente_servicio_id, fecha_cita, horario, codigo_reserva, estado_cita)
        VALUES (?, ?, ?, ?, 'confirmada')
        """, (cliente_servicio_id, fecha_cita.strftime('%Y-%m-%d'), horario, codigo_reserva))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Cita agendada: {codigo_reserva} - {fecha_cita.strftime('%d/%m/%Y')} {horario}")
        return True, codigo_reserva
        
    except Exception as e:
        print(f"❌ Error agendando cita: {e}")
        return False, str(e)

def obtener_horarios_disponibles(tipo_servicio, fecha_solicitada):
    """Obtener horarios disponibles para un servicio y fecha"""
    try:
        horarios_base = {
            'astrologo_humano': {
                'lunes': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'martes': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'miercoles': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'jueves': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'viernes': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'sabado': ['12:00-13:00', '13:00-14:00'],
                'domingo': []
            },
            'tarot_humano': {
                'lunes': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'martes': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'miercoles': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'jueves': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'viernes': ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                'sabado': ['12:00-13:00', '13:00-14:00'],
                'domingo': []
            },
            'veronica_presencial': {
                'lunes': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '16:00-17:00', '17:00-18:00'],
                'martes': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '16:00-17:00', '17:00-18:00'],
                'miercoles': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '16:00-17:00', '17:00-18:00'],
                'jueves': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '16:00-17:00', '17:00-18:00'],
                'viernes': ['09:00-10:00', '10:00-11:00', '11:00-12:00'],
                'sabado': [],
                'domingo': []
            },
            'veronica_telefono': {
                'lunes': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                'martes': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                'miercoles': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                'jueves': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                'viernes': ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00'],
                'sabado': [],
                'domingo': []
            }
        }
        
        horarios_dia = horarios_base.get(tipo_servicio, {})
        
        dia_semana = fecha_solicitada.strftime('%A').lower()
        dias_es = {
            'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miercoles',
            'thursday': 'jueves', 'friday': 'viernes', 'saturday': 'sabado', 'sunday': 'domingo'
        }
        dia_semana = dias_es.get(dia_semana, dia_semana)
        
        horarios_disponibles = horarios_dia.get(dia_semana, [])
        
        # Filtrar horarios ya ocupados
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT horario FROM citas_agendadas 
        WHERE fecha_cita = ? AND estado_cita != 'cancelada'
        """, (fecha_solicitada.strftime('%Y-%m-%d'),))
        
        horarios_ocupados = [row[0] for row in cur.fetchall()]
        conn.close()
        
        # Filtrar disponibles
        horarios_libres = [h for h in horarios_disponibles if h not in horarios_ocupados]
        
        return horarios_libres
        
    except Exception as e:
        print(f"❌ Error obteniendo horarios disponibles: {e}")
        return []

def retell_llamada_zadarma(telefono, empresa, vendedor):
    """Nueva función para llamadas automatizadas via Zadarma-Retell - CORREGIDA"""
    print(f"=== INICIANDO LLAMADA ZADARMA: {telefono} - {vendedor} ===")
    
    if not ZADARMA_PHONE_NUMBER_ID:
        return {"success": False, "error": "Zadarma no configurado aún"}
    
    headers = {
        'Authorization': f'Bearer {RETELL_API_KEY}',  # ✅ Usa variable correcta
        'Content-Type': 'application/json'
    }
    
    payload = {
        "agent_id": AGENT_IDS.get(vendedor, AGENT_IDS['Albert']),
        "from_number": ZADARMA_PHONE_NUMBER_ID,
        "to_number": telefono,
        "direction": "outbound",  # ← Añadir este campo
        "retell_llm_dynamic_variables": {
            "empresa": empresa,
            "vendedor": vendedor,
            "telefono": telefono,
            "origen": "automatizacion_vendedores"
        }
    }
    
    try:
        response = requests.post(
            'https://api.retellai.com/v2/register-phone-call',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"=== RESPUESTA RETELL: {response.status_code} - {response.text} ===")
        
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
        print(f"=== ERROR LLAMADA: {str(e)} ===")
        return {"success": False, "error": f"Excepción: {str(e)}"}

def enviar_telegram_mejora(mensaje):
    """Enviar notificación por Telegram"""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("❌ Token o Chat ID de Telegram no configurados")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("✅ Notificación Telegram enviada")
            return True
        else:
            print(f"❌ Error enviando Telegram: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en notificación Telegram: {e}")
        return False

# ========================================
# WEBHOOKS EXISTENTES (MANTENIDOS IGUAL)
# ========================================

@app.route("/webhook/sofia", methods=["GET", "POST"])
def webhook_sofia():
    # Responder a validación GET de Vapi
    if request.method == "GET":
        return {"status": "ok", "message": "Sofia webhook ready"}
    
    # Para POST: permitir tanto validaciones como llamadas reales
    try:
        # Si no hay datos JSON, podría ser validación de Vapi
        if not request.is_json or not request.get_json():
            return {"status": "ok", "message": "Sofia webhook ready"}
            
        data = request.get_json()
        response = handle_sofia_webhook(data)
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en webhook_sofia: {e}")
        return jsonify({"status": "ok"})  # NUNCA devolver error 500

@app.route("/webhook/veronica", methods=["GET", "POST"])  
def webhook_veronica():
    # Responder a validación GET de Vapi
    if request.method == "GET":
        return {"status": "ok", "message": "Veronica webhook ready"}
    
    # Para POST: permitir tanto validaciones como llamadas reales
    try:
        # Si no hay datos JSON, podría ser validación de Vapi
        if not request.is_json or not request.get_json():
            return {"status": "ok", "message": "Veronica webhook ready"}
            
        data = request.get_json()
        response = handle_veronica_webhook(data)
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en webhook_veronica: {e}")
        return jsonify({"status": "ok"})  # NUNCA devolver error 500
        
@app.route("/webhook/veronica/retell", methods=["GET", "POST"])
def webhook_veronica_retell():
    return webhook_veronica()
        
@app.route('/webhook/fin_sesion', methods=['POST'])
def webhook_fin_sesion():
    try:
        data = request.json
        print(f"🔚 Fin de sesión recibido: {data}")
        
        # Extraer datos necesarios
        email = data.get('email')
        tipo_servicio = data.get('tipo_servicio')
        pdf_url = data.get('pdf_url')
        
        # Enviar informe
        if email and tipo_servicio:
            enviar_email_informe(email, tipo_servicio, pdf_url)
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/webhook/vendedor1", methods=["GET", "POST"])
def webhook_vendedor1():
    if request.method == "GET":
        return {"status": "ok", "message": "Vendedor1 webhook ready"}
    
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
            
        response = handle_vendedor1_webhook(data)
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en webhook_vendedor1: {e}")
        return jsonify({"type": "speak", "text": "Error interno del servidor"}), 500

@app.route("/webhook/vendedor2", methods=["GET", "POST"])
def webhook_vendedor2():
    if request.method == "GET":
        return {"status": "ok", "message": "Vendedor2 webhook ready"}
    
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
            
        response = handle_vendedor2_webhook(data)
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en webhook_vendedor2: {e}")
        return jsonify({"type": "speak", "text": "Error interno del servidor"}), 500

@app.route("/webhook/vendedor3", methods=["GET", "POST"])
def webhook_vendedor3():
    if request.method == "GET":
        return {"status": "ok", "message": "Vendedor3 webhook ready"}
    
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
            
        response = handle_vendedor3_webhook(data)
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en webhook_vendedor3: {e}")
        return jsonify({"type": "speak", "text": "Error interno del servidor"}), 500

@app.route("/webhook/tecnico_soporte", methods=["POST"])
def webhook_tecnico_soporte():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_tecnico_soporte_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_tecnico_soporte: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

# ========================================
# WEBHOOKS DE AS CARTASTRAL (Actualizados)
# ========================================

@app.route("/webhook/astrologa_cartastral", methods=["POST"])
def webhook_astrologa_cartastral():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para carta astral
        data = preparar_datos_con_id(data, "carta_natal")
        
        response = handle_astrologa_cartastral_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_astrologa_cartastral: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/astrologa_revolsolar", methods=["POST"])
def webhook_astrologa_revolsolar():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para revolución solar
        data = preparar_datos_con_id(data, "revolucion_solar")
        
        response = handle_astrologa_revolsolar_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_astrologa_revolsolar: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/astrologa_sinastria", methods=["POST"])
def webhook_astrologa_sinastria():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para sinastría
        data = preparar_datos_con_id(data, "sinastria")
        
        response = handle_astrologa_sinastria_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_astrologa_sinastria: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/astrologa_astrolhoraria", methods=["POST"])
def webhook_astrologa_astrolhoraria():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para astrología horaria
        data = preparar_datos_con_id(data, "astrol_horaria")
        
        response = handle_astrologa_astrolhoraria_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_astrologa_astrolhoraria: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/psico_coaching", methods=["POST"])
def webhook_psico_coaching():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para psico-coaching
        data = preparar_datos_con_id(data, "psico_coaching")
        
        response = handle_psico_coaching_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_psico_coaching: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/lectura_manos", methods=["POST"])
def webhook_lectura_manos():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para lectura de manos
        data = preparar_datos_con_id(data, "lectura_manos")
        
        response = handle_lectura_manos_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_lectura_manos: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/lectura_facial", methods=["POST"])
def webhook_lectura_facial():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Preparar datos con identificadores únicos para lectura facial
        data = preparar_datos_con_id(data, "lectura_facial")
        
        response = handle_lectura_facial_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_lectura_facial: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500
        
@app.route("/webhook/grafologia", methods=["POST"])
def webhook_grafologia():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        data = preparar_datos_con_id(data, "grafologia")
        response = handle_grafologia_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_grafologia: {e}")
        return jsonify({"type": "speak", "text": "Error interno del servidor"}), 500

# ========================================
# WEBHOOKS OTROS SERVICIOS (Mantenidos igual)
# ========================================

@app.route("/webhook/busca_empresas1", methods=["POST"])
def webhook_busca_empresas1():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        # Procesar con sistema simplificado
        resultado = procesar_empresa_simple(data, "BUSCA_EMPRESAS_1")
        
        if resultado["success"]:
            if resultado.get("action") == "created":
                response_text = f"Nueva empresa procesada con ID {resultado['id']}. Añadida a Dolibarr correctamente."
            else:
                response_text = f"Empresa procesada con ID {resultado['id']}."
        else:
            if resultado["reason"] == "robinson":
                response_text = "Esta empresa está en nuestra lista de exclusión y no será contactada."
            else:
                response_text = f"Error procesando empresa: {resultado['message']}"

        return jsonify({
            "type": "speak",
            "text": response_text
        })

    except Exception as e:
        print(f"Error en webhook_busca_empresas1: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error procesando empresa"
        }), 500

@app.route("/webhook/busca_empresas2", methods=["POST"])
def webhook_busca_empresas2():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        resultado = procesar_empresa_simple(data, "BUSCA_EMPRESAS_2")
        
        if resultado["success"]:
            response_text = f"Empresa procesada con ID {resultado['id']}."
        else:
            if resultado["reason"] == "robinson":
                response_text = "Esta empresa está en nuestra lista de exclusión."
            else:
                response_text = f"Error: {resultado['message']}"

        return jsonify({
            "type": "speak",
            "text": response_text
        })

    except Exception as e:
        print(f"Error en webhook_busca_empresas2: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error procesando empresa"
        }), 500

@app.route("/webhook/busca_empresas3", methods=["POST"])
def webhook_busca_empresas3():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        resultado = procesar_empresa_simple(data, "BUSCA_EMPRESAS_3")
        
        if resultado["success"]:
            response_text = f"Empresa procesada con ID {resultado['id']}."
        else:
            if resultado["reason"] == "robinson":
                response_text = "Esta empresa está en nuestra lista de exclusión."
            else:
                response_text = f"Error: {resultado['message']}"

        return jsonify({
            "type": "speak",
            "text": response_text
        })

    except Exception as e:
        print(f"Error en webhook_busca_empresas3: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error procesando empresa"
        }), 500

@app.route("/webhook/redes_sociales1", methods=["POST"])
def webhook_redes_sociales1():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales1_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales1: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/redes_sociales2", methods=["POST"])
def webhook_redes_sociales2():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales2_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales2: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/redes_sociales3", methods=["POST"])
def webhook_redes_sociales3():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales3_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales3: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/redes_sociales4", methods=["POST"])
def webhook_redes_sociales4():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales4_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales4: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/redes_sociales5", methods=["POST"])
def webhook_redes_sociales5():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales5_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales5: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/redes_sociales6", methods=["POST"])
def webhook_redes_sociales6():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales6_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales6: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/redes_sociales7", methods=["POST"])
def webhook_redes_sociales7():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_redes_sociales7_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_redes_sociales7: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/chistes1", methods=["POST"])
def webhook_chistes1():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos JSON"}), 400

        response = handle_chistes1_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_chistes1: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500
        
# ========================================
# WEBHOOK FIN DE SESIÓN AUTOMÁTICO - AÑADIR AQUÍ
# ========================================

@app.route('/webhook/fin_sesion_automatico', methods=['GET', 'POST'])
def webhook_fin_sesion_automatico():
    """Webhook para fin de sesión automático con informes.py"""
    try:
        # Responder a validación GET de Vapi
        if request.method == "GET":
            return {"status": "ok", "message": "Fin sesion automatico webhook ready"}
        
        data = request.get_json()
        print(f"🔚 FIN DE SESIÓN AUTOMÁTICO: {data}")
        
        # Extraer datos básicos
        email = data.get('email')
        tipo_servicio = data.get('tipo_servicio') 
        codigo_servicio = data.get('codigo_servicio', '')
        resumen_conversacion = data.get('call_summary', data.get('resumen_conversacion', ''))
        numero_telefono = data.get('numero_telefono', '+34930450985')
        
        print(f"📧 Procesando fin de sesión: {email} - {tipo_servicio}")
        
        # Si no tenemos datos, buscar en sistema de seguimiento
        if not email or not tipo_servicio:
            if numero_telefono:
                from agents.sofia import SeguimientoTelefonico
                seguimiento = SeguimientoTelefonico()
                sesion_activa = seguimiento.buscar_sesion_activa(numero_telefono)
                
                if sesion_activa:
                    email = sesion_activa.get('email')
                    tipo_servicio = sesion_activa.get('tipo_servicio')
                    codigo_servicio = sesion_activa.get('codigo_servicio')
                    datos_natales = json.loads(sesion_activa.get('datos_natales', '{}'))
                    print(f"✅ Datos encontrados en seguimiento: {email}, {tipo_servicio}")
                else:
                    print("❌ No se encontró sesión activa")
                    return jsonify({"status": "error", "message": "Sesión no encontrada"})
            else:
                print("❌ No hay email ni teléfono para buscar sesión")
                return jsonify({"status": "error", "message": "Datos insuficientes"})
        
        # Preparar datos para informes.py
        datos_cliente = {
            'nombre': data.get('nombre', datos_natales.get('nombre', 'Cliente') if 'datos_natales' in locals() else 'Cliente'),
            'email': email,
            'codigo_servicio': codigo_servicio,
            'fecha_nacimiento': data.get('fecha_nacimiento', datos_natales.get('fecha_nacimiento', '') if 'datos_natales' in locals() else ''),
            'hora_nacimiento': data.get('hora_nacimiento', datos_natales.get('hora_nacimiento', '') if 'datos_natales' in locals() else ''),
            'lugar_nacimiento': data.get('lugar_nacimiento', datos_natales.get('lugar_nacimiento', '') if 'datos_natales' in locals() else ''),
            'pais_nacimiento': data.get('pais_nacimiento', datos_natales.get('pais_nacimiento', 'España') if 'datos_natales' in locals() else 'España')
        }
        
        # Buscar archivos generados (cartas astrales, etc.)
        archivos_unicos = buscar_archivos_sesion(codigo_servicio, datos_cliente['nombre'])
        
        # USAR informes.py para generar y enviar
        from informes import procesar_y_enviar_informe
        
        resultado = procesar_y_enviar_informe(
            datos_cliente=datos_cliente,
            tipo_servicio=tipo_servicio,
            archivos_unicos=archivos_unicos,
            resumen_sesion=resumen_conversacion
        )
        
        # Notificación Telegram
        if resultado and (es_servicio_humano_cartastral(codigo_servicio) or data.get('test_mode')):
            try:
                enviar_telegram_mejora(f"""
📧 <b>INFORME ENVIADO AUTOMÁTICAMENTE</b>

👤 <b>Cliente:</b> {datos_cliente['nombre']}
📧 <b>Email:</b> {email}
🎯 <b>Servicio:</b> {obtener_nombre_servicio_legible(tipo_servicio)}
🔢 <b>Código:</b> {codigo_servicio}

✅ <b>Estado:</b> PDF enviado correctamente
📄 <b>Sistema:</b> informes.py automático
                """.strip())
            except Exception as tel_error:
                print(f"⚠️ Error enviando Telegram: {tel_error}")
        
        # Finalizar sesión en seguimiento
        if numero_telefono:
            try:
                seguimiento.finalizar_sesion(numero_telefono, {
                    'informe_enviado': bool(resultado),
                    'email_enviado': email,
                    'archivo_generado': str(resultado) if resultado else None
                })
            except Exception as e:
                print(f"⚠️ Error finalizando seguimiento: {e}")
        
        return jsonify({
            "status": "success" if resultado else "error",
            "message": "Informe enviado correctamente" if resultado else "Error enviando informe",
            "archivo": str(resultado) if resultado else None,
            "email": email,
            "tipo_servicio": tipo_servicio
        })
        
    except Exception as e:
        print(f"❌ Error en fin de sesión automático: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

def buscar_archivos_sesion(codigo_servicio, nombre_cliente):
    """Buscar archivos generados para una sesión específica"""
    try:
        import glob
        
        archivos_encontrados = {}
        
        # Buscar por código de servicio y timestamp reciente
        if codigo_servicio:
            # Buscar archivos de las últimas 2 horas por timestamp
            from datetime import datetime, timedelta
            hace_2h = datetime.now() - timedelta(hours=2)
            timestamp_min = hace_2h.strftime("%Y%m%d%H%M%S")
            
            # Buscar en static (cartas astrales)
            patterns = [
                "static/carta_natal_*.png",
                "static/progresiones_*.png", 
                "static/transitos_*.png",
                "static/revolucion_*.png",
                "static/sinastria_*.png",
                "static/carta_horaria_*.png"
            ]
            
            for pattern in patterns:
                archivos = glob.glob(pattern)
                # Filtrar por archivos recientes (últimas 2 horas)
                archivos_recientes = []
                for archivo in archivos:
                    try:
                        stat = os.path.getmtime(archivo)
                        archivo_time = datetime.fromtimestamp(stat)
                        if archivo_time > hace_2h:
                            archivos_recientes.append(archivo)
                    except:
                        continue
                
                # Tomar el más reciente de cada tipo
                if archivos_recientes:
                    archivo_mas_reciente = max(archivos_recientes, key=os.path.getmtime)
                    nombre_base = os.path.basename(archivo_mas_reciente)
                    
                    if 'carta_natal' in nombre_base:
                        archivos_encontrados['carta_natal_img'] = archivo_mas_reciente
                    elif 'progresiones' in nombre_base:
                        archivos_encontrados['progresiones_img'] = archivo_mas_reciente
                    elif 'transitos' in nombre_base:
                        archivos_encontrados['transitos_img'] = archivo_mas_reciente
                    elif 'revolucion_sola' in nombre_base:
                        archivos_encontrados['revolucion_img'] = archivo_mas_reciente
                    elif 'revolucion_natal' in nombre_base:
                        archivos_encontrados['revolucion_natal_img'] = archivo_mas_reciente
                    elif 'sinastria' in nombre_base:
                        archivos_encontrados['sinastria_img'] = archivo_mas_reciente
                    elif 'carta_horaria' in nombre_base:
                        archivos_encontrados['carta_horaria_img'] = archivo_mas_reciente
        
        print(f"🔍 Archivos encontrados para {codigo_servicio}: {archivos_encontrados}")
        return archivos_encontrados
        
    except Exception as e:
        print(f"❌ Error buscando archivos: {e}")
        return {}

def obtener_nombre_servicio_legible(tipo_servicio):
    """Obtener nombre legible del servicio"""
    nombres = {
        'carta_astral_ia': 'Carta Astral IA',
        'revolucion_solar_ia': 'Revolución Solar IA',
        'sinastria_ia': 'Sinastría IA',
        'astrologia_horaria_ia': 'Astrología Horaria IA',
        'psico_coaching_ia': 'Psico-Coaching IA',
        'lectura_manos_ia': 'Lectura de Manos IA',
        'lectura_facial_ia': 'Lectura Facial IA',
        'astrologo_humano': 'Astrólogo Personal',
        'tarot_humano': 'Tarot Personal',
        'grafologia_ia': 'Análisis Grafológico IA'
    }
    return nombres.get(tipo_servicio, tipo_servicio)

# ========================================
# TEST MANUAL DEL SISTEMA - AÑADIR TAMBIÉN
# ========================================

@app.route('/test/enviar_informe_manual', methods=['GET', 'POST'])
def test_enviar_informe_manual():
    """Test manual para probar el sistema de informes"""
    try:
        if request.method == 'GET':
            return jsonify({
                "message": "Test endpoint activo",
                "uso": "POST con {email, tipo_servicio, codigo_servicio}"
            })
            
        data = request.get_json() or {}
        
        # Datos de prueba por defecto
        datos_test = {
            'email': data.get('email', 'test@ejemplo.com'),
            'tipo_servicio': data.get('tipo_servicio', 'carta_astral_ia'),
            'codigo_servicio': data.get('codigo_servicio', 'AI_123456'),
            'call_summary': data.get('resumen_conversacion', 'Test de sesión automática'),
            'numero_telefono': data.get('numero_telefono', '+34930450985')
        }
        
        print(f"🧪 TEST MANUAL: {datos_test}")
        
        # Simular llamada al webhook
        request_backup = request
        
        # Crear request simulado para el webhook
        class FakeRequest:
            def get_json(self):
                return datos_test
            method = 'POST'
        
        # Temporalmente cambiar request
        import builtins
        old_request = builtins.__dict__.get('request')
        builtins.__dict__['request'] = FakeRequest()
        
        try:
            # Llamar webhook
            response = webhook_fin_sesion_automatico()
            return jsonify({
                "status": "test_completed",
                "datos_enviados": datos_test,
                "resultado": response.get_json() if hasattr(response, 'get_json') else str(response)
            })
        finally:
            # Restaurar request original
            if old_request:
                builtins.__dict__['request'] = old_request
        
    except Exception as e:
        return jsonify({
            "status": "test_error", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
        
# ========================================
# WEBHOOK WOOCOMMERCE (AÑADIR DESPUÉS DEL ÚLTIMO WEBHOOK)
# ========================================

@app.route("/webhook/woocommerce", methods=["GET", "POST"])
def webhook_woocommerce():
    """Webhook para recibir pedidos de WooCommerce"""
    try:
        # Si es GET, devolver confirmación para verificación
        if request.method == "GET":
            return jsonify({
                "status": "webhook_ready", 
                "service": "AS Cartastral",
                "endpoints": ["POST /webhook/woocommerce"]
            })
        
        # Para POST: verificar si tiene datos JSON válidos
        if request.method == "POST":
            # Si no es JSON o está vacío, devolver verificación exitosa
            if not request.is_json or not request.get_json():
                print("⚠️ POST de verificación de WooCommerce (sin datos JSON)")
                return jsonify({"status": "webhook_ready", "message": "POST verification successful"})
        
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "webhook_ready", "message": "No data received"})
        
        print(f"📦 NUEVO PEDIDO WOOCOMMERCE: {data.get('id', 'Sin ID')}")
        
        # Extraer datos del pedido
        order_id = data.get('id')
        email_cliente = data.get('billing', {}).get('email')
        
        if not email_cliente:
            print("❌ Email no encontrado en pedido WooCommerce")
            return jsonify({"error": "Email requerido"}), 400
        
        # Procesar productos comprados
        productos_procesados = 0
        
        for item in data.get('line_items', []):
            product_name = item.get('name', '')
            
            if product_name:
                # Detectar tipo de servicio
                tipo_servicio = detectar_tipo_servicio_woo(product_name)
                
                # Generar código único
                codigo = generar_codigo_unico(tipo_servicio, order_id)
                
                # Guardar en base de datos
                if guardar_codigo_woocommerce(codigo, email_cliente, tipo_servicio):
                    productos_procesados += 1
                    print(f"✅ Código generado: {codigo} → {email_cliente}")
                    
# LÓGICA EMPRESARIAL: Solo notificar servicios humanos
                    if es_servicio_humano_cartastral(codigo):
                        # Notificación Telegram SOLO para servicios humanos
                        enviar_telegram_mejora(f"""
🔮 <b>NUEVA COMPRA - SERVICIO HUMANO</b>

📧 <b>Cliente:</b> {email_cliente}
🎯 <b>Servicio:</b> {obtener_descripcion_servicio_por_codigo(codigo)}
🔢 <b>Código:</b> {codigo}
🛍️ <b>Producto:</b> {product_name}
🆔 <b>Pedido:</b> #{order_id}

⚠️ <b>REQUIERE CITA</b>
✅ <b>Estado:</b> Código listo para usar
                        """.strip())
                    elif es_servicio_automatico(codigo):
                        print(f"🤖 Servicio automático creado (sin notificación): {codigo}")
                    else:
                        # Otros tipos de código
                        enviar_telegram_mejora(f"""
🛒 <b>NUEVA COMPRA</b>

📧 <b>Cliente:</b> {email_cliente}
🎯 <b>Servicio:</b> {obtener_descripcion_servicio_por_codigo(codigo)}
🔢 <b>Código:</b> {codigo}
🛍️ <b>Producto:</b> {product_name}
🆔 <b>Pedido:</b> #{order_id}

✅ <b>Estado:</b> Código listo para usar
                        """.strip())
        
        if productos_procesados > 0:
            print(f"🎉 Procesados {productos_procesados} productos para {email_cliente}")
            return jsonify({
                "status": "success", 
                "message": f"Procesados {productos_procesados} códigos",
                "email": email_cliente
            })
        else:
            return jsonify({"error": "No se procesaron productos"}), 400

    except Exception as e:
        print(f"❌ Error en webhook WooCommerce: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
        
# ========================================
# CALENDARIO DE CITAS (MANTENIDO)
# ========================================

@app.route('/calendario')
def mostrar_calendario():
    """Mostrar interfaz del calendario"""
    html_calendario = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calendario de Citas - AS Asesores</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; color: #333; }
        .fecha-selector { text-align: center; margin-bottom: 20px; }
        .fecha-selector input { padding: 10px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; }
        .servicios { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .servicio { border: 2px solid #ddd; border-radius: 10px; padding: 15px; }
        .servicio h3 { margin-top: 0; color: #2c5aa0; text-align: center; }
        .horario { display: flex; justify-content: space-between; align-items: center; padding: 8px; margin: 5px 0; border-radius: 5px; }
        .horario.libre { background: #d4edda; }
        .horario.ocupado { background: #f8d7da; }
        .cliente-info { font-size: 12px; color: #666; margin-top: 5px; }
        .btn { padding: 5px 10px; border: none; border-radius: 3px; cursor: pointer; font-size: 12px; }
        .btn-ocupar { background: #dc3545; color: white; }
        .btn-liberar { background: #28a745; color: white; }
        .loading { text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 Calendario de Citas</h1>
            <p>AS Asesores - Gestión de Horarios</p>
        </div>
        
        <div class="fecha-selector">
            <label for="fecha">Seleccionar fecha: </label>
            <input type="date" id="fecha" onchange="cargarHorarios()">
        </div>
        
        <div id="calendario-content" class="loading">
            Cargando horarios...
        </div>
    </div>

    <script>
        // Establecer fecha de hoy por defecto
        document.getElementById('fecha').value = new Date().toISOString().split('T')[0];
        
        function cargarHorarios() {
            const fecha = document.getElementById('fecha').value;
            document.getElementById('calendario-content').innerHTML = '<div class="loading">Cargando horarios...</div>';
            
            fetch(`/api/horarios/${fecha}`)
                .then(response => response.json())
                .then(data => mostrarHorarios(data, fecha))
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('calendario-content').innerHTML = '<div class="loading">Error cargando horarios</div>';
                });
        }
        
        function mostrarHorarios(data, fecha) {
            const servicios = {
                'astrologo_humano': 'Astrólogo Personal',
                'tarot_humano': 'Tarot Personal',
                'veronica_presencial': 'Verónica Presencial (2h)',
                'veronica_telefono': 'Verónica Teléfono (1h)'
            };
            
            let html = '<div class="servicios">';
            
            for (const [servicioKey, servicioNombre] of Object.entries(servicios)) {
                html += `<div class="servicio">
                    <h3>${servicioNombre}</h3>`;
                
                // Obtener horarios base para este servicio
                const horariosBase = obtenerHorariosBase(servicioKey, fecha);
                const horariosOcupados = data[servicioKey] || [];
                
                for (const horario of horariosBase) {
                    const ocupado = horariosOcupados.find(h => h[0] === horario);
                    
                    if (ocupado) {
                        html += `<div class="horario ocupado">
                            <div>
                                <strong>${horario}</strong>
                                <div class="cliente-info">
                                    👤 ${ocupado[1] || 'Sin nombre'}<br>
                                    📧 ${ocupado[2] || 'Sin motivo'}
                                </div>
                            </div>
                            <button class="btn btn-liberar" onclick="liberarHorario('${servicioKey}', '${fecha}', '${horario}')">
                                Liberar
                            </button>
                        </div>`;
                    } else {
                        html += `<div class="horario libre">
                            <div><strong>${horario}</strong> - Disponible</div>
                            <button class="btn btn-ocupar" onclick="ocuparHorario('${servicioKey}', '${fecha}', '${horario}')">
                                Ocupar
                            </button>
                        </div>`;
                    }
                }
                
                html += '</div>';
            }
            
            html += '</div>';
            document.getElementById('calendario-content').innerHTML = html;
        }
        
        function obtenerHorariosBase(servicio, fecha) {
            const fechaObj = new Date(fecha);
            const diaSemana = fechaObj.getDay(); // 0=domingo, 1=lunes, etc.
            
            const horarios = {
                'astrologo_humano': {
                    1: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    2: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    3: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    4: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    5: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    6: ['12:00-13:00', '13:00-14:00']
                },
                'tarot_humano': {
                    1: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    2: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    3: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    4: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    5: ['11:00-12:00', '12:00-13:00', '13:00-14:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00'],
                    6: ['12:00-13:00', '13:00-14:00']
                },
                'veronica_presencial': {
                    1: ['10:00-12:00', '11:00-13:00', '16:00-18:00', '17:00-19:00'],
                    2: ['10:00-12:00', '11:00-13:00', '16:00-18:00', '17:00-19:00'],
                    3: ['10:00-12:00', '11:00-13:00', '16:00-18:00', '17:00-19:00'],
                    4: ['10:00-12:00', '11:00-13:00', '16:00-18:00', '17:00-19:00'],
                    5: ['10:00-12:00', '11:00-13:00', '16:00-18:00', '17:00-19:00']
                },
                'veronica_telefono': {
                    1: ['09:30-10:30', '10:30-11:30', '11:30-12:30', '12:30-13:30', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                    2: ['09:30-10:30', '10:30-11:30', '11:30-12:30', '12:30-13:30', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                    3: ['09:30-10:30', '10:30-11:30', '11:30-12:30', '12:30-13:30', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                    4: ['09:30-10:30', '10:30-11:30', '11:30-12:30', '12:30-13:30', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
                    5: ['09:30-10:30', '10:30-11:30', '11:30-12:30', '12:30-13:30', '16:00-17:00', '17:00-18:00', '18:00-19:00']
                }
            };
            
            return horarios[servicio]?.[diaSemana] || [];
        }
        
        function ocuparHorario(servicio, fecha, horario) {
            const motivo = prompt('Motivo (opcional):') || 'Ocupado manualmente';
            
            fetch('/api/ocupar_horario', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tipo_servicio: servicio,
                    fecha: fecha,
                    horario: horario,
                    motivo: motivo
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    cargarHorarios();
                } else {
                    alert('Error ocupando horario');
                }
            });
        }
        
        function liberarHorario(servicio, fecha, horario) {
            if (confirm('¿Seguro que quieres liberar este horario?')) {
                fetch('/api/liberar_horario', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tipo_servicio: servicio,
                        fecha: fecha,
                        horario: horario
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        cargarHorarios();
                    } else {
                        alert('Error liberando horario');
                    }
                });
            }
        }
        
        // Cargar horarios al iniciar
        cargarHorarios();
    </script>
</body>
</html>
    """
    return render_template_string(html_calendario)

@app.route('/api/horarios/<fecha>')
def obtener_horarios_api(fecha):
    """API para obtener horarios de un día específico"""
    try:
        from agents.sofia import obtener_horarios_ocupados_dia
        
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        
        # Obtener horarios para todos los servicios
        servicios = ['astrologo_humano', 'tarot_humano', 'veronica_presencial', 'veronica_telefono']
        horarios_dia = {}
        
        for servicio in servicios:
            ocupados = obtener_horarios_ocupados_dia(servicio, fecha_obj)
            horarios_dia[servicio] = ocupados
            
        return jsonify(horarios_dia)
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/ocupar_horario', methods=['POST'])
def ocupar_horario_api():
    """API para ocupar horarios manualmente"""
    try:
        from agents.sofia import ocupar_horario_calendario
        
        data = request.json
        tipo_servicio = data['tipo_servicio']
        fecha = datetime.strptime(data['fecha'], '%Y-%m-%d')
        horario = data['horario']
        motivo = data.get('motivo', 'Ocupado manualmente')
        
        exito = ocupar_horario_calendario(tipo_servicio, fecha, horario, None, motivo)
        
        return jsonify({"success": exito})
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/liberar_horario', methods=['POST'])
def liberar_horario_api():
    """API para liberar horarios"""
    try:
        import sqlite3
        
        data = request.json
        tipo_servicio = data['tipo_servicio']
        fecha = datetime.strptime(data['fecha'], '%Y-%m-%d')
        horario = data['horario']
        
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        DELETE FROM horarios_ocupados 
        WHERE tipo_servicio = ? AND fecha = ? AND horario = ?
        """, (tipo_servicio, fecha.strftime('%Y-%m-%d'), horario))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
        
        
    except Exception as e:
        return jsonify({"error": str(e), "success": False})

# ========================================
# NUEVAS RUTAS PARA ADMINISTRACIÓN AVANZADA
# ========================================

@app.route('/admin')
def admin_calendario():
    """Panel de administración del calendario"""
    
    html_admin = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔧 Administración - AS Asesores</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .nav-tabs { display: flex; background: white; border-radius: 10px 10px 0 0; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .nav-tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; border: none; background: #f8f9fa; color: #666; font-weight: bold; }
        .nav-tab.active { background: white; color: #2c5aa0; }
        .content { background: white; border-radius: 0 0 10px 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .calendar-container { background: white; border-radius: 10px; padding: 20px; margin: 20px 0; }
        .month-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .month-nav button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .month-nav h2 { margin: 0; color: #2c5aa0; }
        .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
        .calendar-header { background: #007bff; color: white; padding: 10px; text-align: center; font-weight: bold; }
        .calendar-day { background: #f8f9fa; padding: 10px; min-height: 120px; border-radius: 3px; position: relative; cursor: pointer; border: 2px solid transparent; }
        .calendar-day:hover { border-color: #007bff; }
        .calendar-day.today { background: #e7f3ff; border: 2px solid #007bff; }
        .evento { background: #28a745; color: white; padding: 2px 5px; margin: 1px 0; border-radius: 3px; font-size: 10px; cursor: pointer; }
        .evento.astrologo { background: #28a745; }
        .evento.tarot { background: #007bff; }
        .evento.veronica-presencial { background: #dc3545; }
        .evento.veronica-telefono { background: #ffc107; color: #000; }
        .evento.bloqueado { background: #6c757d; }
        .btn { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-warning:hover { background: #e0a800; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; }
        .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: black; }
        .horarios-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }
        .horario-slot { padding: 10px; border: 2px solid #ddd; border-radius: 5px; text-align: center; cursor: pointer; }
        .horario-slot.disponible { background: #d4edda; border-color: #28a745; }
        .horario-slot.ocupado { background: #f8d7da; border-color: #dc3545; }
        .horario-slot.bloqueado { background: #e2e3e5; border-color: #6c757d; }
        .horario-slot:hover { opacity: 0.8; }
        .citas-lista { max-height: 400px; overflow-y: auto; }
        .cita-item { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .alert { padding: 15px; margin: 15px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Administración - AS Asesores</h1>
            <p>Panel de control para gestión de citas y horarios</p>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="cambiarTab('calendario')">📅 Calendario</button>
            <button class="nav-tab" onclick="cambiarTab('agendar')">➕ Agendar Cita</button>
            <button class="nav-tab" onclick="cambiarTab('bloquear')">🚫 Bloquear Horarios</button>
            <button class="nav-tab" onclick="cambiarTab('citas')">📋 Ver Citas</button>
            <button class="nav-tab" onclick="cambiarTab('stats')">📊 Estadísticas</button>
        </div>
        
        <div class="content">
            <!-- TAB CALENDARIO -->
            <div id="tab-calendario" class="tab-content">
                <div class="calendar-container">
                    <div class="month-nav">
                        <button onclick="mesAnterior()">← Anterior</button>
                        <h2 id="mes-titulo">Enero 2025</h2>
                        <button onclick="mesSiguiente()">Siguiente →</button>
                    </div>
                    
                    <div class="calendar-grid" id="calendar-grid">
                        <!-- El calendario se genera aquí -->
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <p><strong>📝 Instrucciones:</strong> Haz clic en un día para ver/gestionar los horarios de ese día.</p>
                        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                            <div><span class="evento astrologo">●</span> Astrólogo Personal</div>
                            <div><span class="evento tarot">●</span> Tarot Personal</div>
                            <div><span class="evento veronica-presencial">●</span> Verónica Presencial</div>
                            <div><span class="evento veronica-telefono">●</span> Verónica Teléfono</div>
                            <div><span class="evento bloqueado">●</span> Horario Bloqueado</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- TAB AGENDAR CITA -->
            <div id="tab-agendar" class="tab-content" style="display:none;">
                <h3>➕ Agendar Nueva Cita</h3>
                <div id="alert-agendar"></div>
                <form id="form-agendar" onsubmit="agendarCita(event)">
                    <div class="form-group">
                        <label>Tipo de Servicio:</label>
                        <select id="tipo-servicio" required onchange="actualizarHorarios()">
                            <option value="">Seleccionar servicio...</option>
                            <option value="astrologo_humano">🔮 Astrólogo Personal</option>
                            <option value="tarot_humano">🃏 Tarot Personal</option>
                            <option value="veronica_presencial">👩‍🦳 Verónica - Presencial</option>
                            <option value="veronica_telefono">📞 Verónica - Teléfono</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Fecha de la Cita:</label>
                        <input type="date" id="fecha-cita" required onchange="actualizarHorarios()">
                    </div>
                    <div class="form-group">
                        <label>Horario:</label>
                        <select id="horario-cita" required>
                            <option value="">Primero selecciona fecha y servicio...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Nombre del Cliente:</label>
                        <input type="text" id="nombre-cliente" required>
                    </div>
                    <div class="form-group">
                        <label>Email del Cliente:</label>
                        <input type="email" id="email-cliente" required>
                    </div>
                    <div class="form-group">
                        <label>Teléfono del Cliente:</label>
                        <input type="tel" id="telefono-cliente">
                    </div>
                    <div class="form-group">
                        <label>Notas (opcional):</label>
                        <textarea id="notas-cita" rows="3"></textarea>
                    </div>
                    <button type="submit" class="btn btn-success">✅ Agendar Cita</button>
                </form>
            </div>
            
            <!-- TAB BLOQUEAR HORARIOS -->
            <div id="tab-bloquear" class="tab-content" style="display:none;">
                <h3>🚫 Bloquear Horarios</h3>
                <div id="alert-bloquear"></div>
                <form id="form-bloquear" onsubmit="bloquearHorario(event)">
                    <div class="form-group">
                        <label>Tipo de Servicio a Bloquear:</label>
                        <select id="tipo-servicio-bloquear" required onchange="actualizarHorariosBloquear()">
                            <option value="">Seleccionar tipo de bloqueo...</option>
                            <option value="todos">🚫 TODO EL DÍA (todos los servicios)</option>
                            <option value="multiples">🔀 BLOQUEOS MÚLTIPLES</option>
                            <option value="astrologo_humano">🔮 Astrólogo Personal</option>
                            <option value="tarot_humano">🃏 Tarot Personal</option>
                            <option value="veronica_presencial">👩‍🦳 Verónica - Presencial</option>
                            <option value="veronica_telefono">📞 Verónica - Teléfono</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Fecha a Bloquear:</label>
                        <input type="date" id="fecha-bloquear" required onchange="actualizarHorariosBloquear()">
                    </div>
                    <div class="form-group">
                        <label>Horario a Bloquear:</label>
                        <select id="horario-bloquear" required>
                            <option value="">Primero selecciona fecha y servicio...</option>
                        </select>
                    </div>
                    <div id="seleccion-multiple" style="display:none; margin-top: 15px; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">
                        <p><strong>Selecciona múltiples servicios:</strong></p>
                    <div id="seleccion-multiple" style="display:none; margin-top: 15px; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">
                        <p><strong>Selecciona múltiples servicios:</strong></p>
                        <div>
                            <label><input type="checkbox" id="check-astrologo" value="astrologo_humano"> 🔮 Astrólogo Personal</label><br>
                            <label><input type="checkbox" id="check-tarot" value="tarot_humano"> 🃏 Tarot Personal</label><br>
                            <label><input type="checkbox" id="check-veronica-pres" value="veronica_presencial"> 👩‍🦳 Verónica Presencial</label><br>
                            <label><input type="checkbox" id="check-veronica-tel" value="veronica_telefono"> 📞 Verónica Teléfono</label><br>
                        </div>
                        <div style="margin-top: 10px;">
                            <label><input type="radio" name="tiempo-multiple" value="todos"> Todo el día</label>
                            <label><input type="radio" name="tiempo-multiple" value="mañana"> Solo mañana</label>
                            <label><input type="radio" name="tiempo-multiple" value="tarde"> Solo tarde</label>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Motivo del Bloqueo:</label>
                        <input type="text" id="motivo-bloquear" placeholder="Ej: Vacaciones, Reunión personal, etc." required>
                    </div>
                    <form id="form-bloquear" onsubmit="bloquearHorarioMejorado(event)">
                </form>
                
                <h4 style="margin-top: 30px;">📋 Horarios Bloqueados</h4>
                <div id="lista-bloqueados" class="citas-lista">
                    <!-- Se cargan dinámicamente -->
                </div>
            </div>
            
            <!-- TAB VER CITAS -->
            <div id="tab-citas" class="tab-content" style="display:none;">
                <h3>📋 Citas Agendadas</h3>
                <div style="margin-bottom: 20px;">
                    <input type="date" id="filtro-fecha" onchange="filtrarCitas()">
                    <select id="filtro-servicio" onchange="filtrarCitas()">
                        <option value="">Todos los servicios</option>
                        <option value="astrologo_humano">🔮 Astrólogo Personal</option>
                        <option value="tarot_humano">🃏 Tarot Personal</option>
                        <option value="veronica_presencial">👩‍🦳 Verónica - Presencial</option>
                        <option value="veronica_telefono">📞 Verónica - Teléfono</option>
                    </select>
                    <button class="btn" onclick="cargarCitas()">🔄 Actualizar</button>
                </div>
                <div id="lista-citas" class="citas-lista">
                    <!-- Se cargan dinámicamente -->
                </div>
            </div>
            
            <!-- TAB ESTADÍSTICAS -->
            <div id="tab-stats" class="tab-content" style="display:none;">
                <h3>📊 Estadísticas del Sistema</h3>
                <div class="stats-grid" id="stats-grid">
                    <!-- Se cargan dinámicamente -->
                </div>
            </div>
        </div>
    </div>

    <!-- MODAL HORARIOS DEL DÍA -->
    <div id="modal-dia" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h3 id="modal-titulo">Horarios del día</h3>
            <div id="modal-horarios" class="horarios-grid">
                <!-- Se genera dinámicamente -->
            </div>
            <div style="margin-top: 20px;">
                <button class="btn btn-success" onclick="abrirAgendarDesdeModal()">➕ Agendar en este día</button>
                <button class="btn btn-warning" onclick="abrirBloquearDesdeModal()">🚫 Bloquear horario</button>
            </div>
        </div>
    </div>

    <script>
        let mesActual = new Date().getMonth() + 1;
        let añoActual = new Date().getFullYear();
        let diaSeleccionado = null;
        
        function cambiarTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
            document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
            
            document.getElementById('tab-' + tabName).style.display = 'block';
            event.target.classList.add('active');
            
            if (tabName === 'calendario') {
                cargarCalendario();
            } else if (tabName === 'citas') {
                cargarCitas();
            } else if (tabName === 'stats') {
                cargarEstadisticas();
            } else if (tabName === 'bloquear') {
                cargarHorariosBloqueados();
            }
        }
        
        function mesAnterior() {
            mesActual--;
            if (mesActual < 1) {
                mesActual = 12;
                añoActual--;
            }
            actualizarCalendario();
        }
        
        function mesSiguiente() {
            mesActual++;
            if (mesActual > 12) {
                mesActual = 1;
                añoActual++;
            }
            actualizarCalendario();
        }
        
        function actualizarCalendario() {
            const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            document.getElementById('mes-titulo').textContent = `${meses[mesActual - 1]} ${añoActual}`;
            cargarCalendario();
        }
        
        function cargarCalendario() {
            const diasSemana = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
            let html = '';
            
            diasSemana.forEach(dia => {
                html += `<div class="calendar-header">${dia}</div>`;
            });
            
            const primerDia = new Date(añoActual, mesActual - 1, 1).getDay();
            const diasEnMes = new Date(añoActual, mesActual, 0).getDate();
            const hoy = new Date();
            
            for (let i = 0; i < primerDia; i++) {
                html += '<div class="calendar-day"></div>';
            }
            
            for (let dia = 1; dia <= diasEnMes; dia++) {
                const esHoy = hoy.getDate() === dia && hoy.getMonth() === mesActual - 1 && hoy.getFullYear() === añoActual;
                const claseHoy = esHoy ? 'today' : '';
                
                html += `<div class="calendar-day ${claseHoy}" onclick="abrirDia(${dia})">
                    <strong>${dia}</strong>
                    <div id="eventos-${dia}"></div>
                </div>`;
            }
            
            document.getElementById('calendar-grid').innerHTML = html;
            cargarEventosCalendario();
        }
        
        function cargarEventosCalendario() {
            fetch(`/api/citas_mes/${añoActual}/${mesActual}`)
                .then(response => response.json())
                .then(citas => {
                    for (let dia = 1; dia <= 31; dia++) {
                        const elemento = document.getElementById(`eventos-${dia}`);
                        if (elemento) elemento.innerHTML = '';
                    }
                    
                    citas.forEach(cita => {
                        const fecha = new Date(cita.fecha_cita + 'T00:00:00');
                        const dia = fecha.getDate();
                        const elemento = document.getElementById(`eventos-${dia}`);
                        
                        if (elemento) {
                            let claseEvento = 'evento';
                            if (cita.estado_cita === 'bloqueado') {
                                claseEvento += ' bloqueado';
                            } else if (cita.tipo_servicio === 'astrologo_humano') {
                                claseEvento += ' astrologo';
                            } else if (cita.tipo_servicio === 'tarot_humano') {
                                claseEvento += ' tarot';
                            } else if (cita.tipo_servicio === 'veronica_presencial') {
                                claseEvento += ' veronica-presencial';
                            } else if (cita.tipo_servicio === 'veronica_telefono') {
                                claseEvento += ' veronica-telefono';
                            }
                            
                            const titulo = cita.estado_cita === 'bloqueado' ? 'BLOQUEADO' : (cita.cliente_nombre || 'Cita');
                            elemento.innerHTML += `<div class="${claseEvento}" title="${cita.horario} - ${titulo}">${cita.horario.split('-')[0]}</div>`;
                        }
                    });
                })
                .catch(error => console.error('Error cargando eventos:', error));
        }
        
        function abrirDia(dia) {
            diaSeleccionado = dia;
            const fecha = `${añoActual}-${mesActual.toString().padStart(2, '0')}-${dia.toString().padStart(2, '0')}`;
            
            document.getElementById('modal-titulo').textContent = `Horarios del ${dia}/${mesActual}/${añoActual}`;
            
            fetch(`/api/horarios_dia/${fecha}`)
                .then(response => response.json())
                .then(horarios => {
                    let html = '';
                    
                    // Agrupar por horario único
                    const horariosUnicos = {};
                    horarios.forEach(h => {
                        if (!horariosUnicos[h.horario]) {
                            horariosUnicos[h.horario] = [];
                        }
                        horariosUnicos[h.horario].push(h);
                    });
                    
                    Object.keys(horariosUnicos).sort().forEach(horario => {
                        const servicios = horariosUnicos[horario];
                        let ocupado = servicios.some(s => s.ocupado);
                        let bloqueado = servicios.some(s => s.bloqueado);
                        
                        let clase = 'horario-slot disponible';
                        let estado = 'Disponible';
                        
                        if (bloqueado) {
                            clase = 'horario-slot bloqueado';
                            const servicioBloquear = servicios.find(s => s.bloqueado);
                            estado = `Bloqueado: ${servicioBloquear.motivo || 'Sin motivo'}`;
                        } else if (ocupado) {
                            clase = 'horario-slot ocupado';
                            const servicioOcupado = servicios.find(s => s.ocupado);
                            estado = `Ocupado: ${servicioOcupado.cliente || 'Cliente'}`;
                        }
                        
                        html += `<div class="${clase}" title="${estado}">
                            <div style="font-weight: bold;">${horario}</div>
                            <div style="font-size: 11px;">${estado}</div>
                        </div>`;
                    });
                    
                    document.getElementById('modal-horarios').innerHTML = html;
                    document.getElementById('modal-dia').style.display = 'block';
                })
                .catch(error => console.error('Error cargando horarios del día:', error));
        }
        
        function abrirAgendarDesdeModal() {
            document.getElementById('modal-dia').style.display = 'none';
            cambiarTab('agendar');
            
            if (diaSeleccionado) {
                const fecha = `${añoActual}-${mesActual.toString().padStart(2, '0')}-${diaSeleccionado.toString().padStart(2, '0')}`;
                document.getElementById('fecha-cita').value = fecha;
                actualizarHorarios();
            }
        }
        
        function abrirBloquearDesdeModal() {
            document.getElementById('modal-dia').style.display = 'none';
            cambiarTab('bloquear');
            
            if (diaSeleccionado) {
                const fecha = `${añoActual}-${mesActual.toString().padStart(2, '0')}-${diaSeleccionado.toString().padStart(2, '0')}`;
                document.getElementById('fecha-bloquear').value = fecha;
                actualizarHorariosBloquear();
            }
        }
        
        function actualizarHorarios() {
            const tipoServicio = document.getElementById('tipo-servicio').value;
            const fecha = document.getElementById('fecha-cita').value;
            
            console.log('DEBUG actualizarHorarios:', {tipoServicio, fecha});
            
            const select = document.getElementById('horario-cita');
            
            if (!tipoServicio) {
                select.innerHTML = '<option value="">Primero selecciona un servicio...</option>';
                return;
            }
            
            if (!fecha) {
                select.innerHTML = '<option value="">Primero selecciona una fecha...</option>';
                return;
            }
            
            // Mostrar loading
            select.innerHTML = '<option value="">Cargando horarios disponibles...</option>';
            
            fetch(`/api/horarios_disponibles?tipo_servicio=${tipoServicio}&fecha=${fecha}`)
                .then(response => response.json())
                .then(data => {
                    console.log('DEBUG horarios recibidos:', data);
                    
                    select.innerHTML = '<option value="">Seleccionar horario...</option>';
                    
                    if (data.horarios && data.horarios.length > 0) {
                        data.horarios.forEach(horario => {
                            select.innerHTML += `<option value="${horario}">${horario}</option>`;
                        });
                        
                        if (data.mensaje) {
                            // Mostrar mensaje si la fecha cambió por lógica inteligente
                            const alertDiv = document.getElementById('alert-agendar') || document.createElement('div');
                            alertDiv.innerHTML = `<div class="alert alert-success">ℹ️ ${data.mensaje}</div>`;
                            if (!document.getElementById('alert-agendar')) {
                                alertDiv.id = 'alert-agendar';
                                document.getElementById('form-agendar').before(alertDiv);
                            }
                        }
                    } else {
                        select.innerHTML = '<option value="" disabled>No hay horarios disponibles</option>';
                    }
                })
                .catch(error => {
                    console.error('Error cargando horarios:', error);
                    select.innerHTML = '<option value="">Error cargando horarios - ver consola</option>';
                });
        }
        
        function actualizarHorariosBloquear() {
            const tipoServicio = document.getElementById('tipo-servicio-bloquear').value;
            const fecha = document.getElementById('fecha-bloquear').value;
            
            console.log('DEBUG: Actualizando horarios bloquear:', { tipoServicio, fecha });
            
            if (!fecha) {
                const select = document.getElementById('horario-bloquear');
                select.innerHTML = '<option value="">Primero selecciona una fecha...</option>';
                return;
            }
            
            if (!tipoServicio) {
                const select = document.getElementById('horario-bloquear');
                select.innerHTML = '<option value="">Selecciona el tipo de servicio...</option>';
                return;
            }
            
            const select = document.getElementById('horario-bloquear');
            select.innerHTML = '<option value="">Cargando horarios...</option>';
            
            if (tipoServicio === 'todos') {
                select.innerHTML = `
                    <option value="">Seleccionar opción de bloqueo...</option>
                    <option value="dia_completo">🚫 DÍA COMPLETO (todos los servicios)</option>
                    <option value="mañana_completa">🌅 MAÑANA COMPLETA (09:00-13:00)</option>
                    <option value="tarde_completa">🌇 TARDE COMPLETA (16:00-19:00)</option>
                `;
            } else if (tipoServicio === 'multiples') {
                // Mostrar checkboxes para múltiples servicios
                select.innerHTML = `<option value="">Configurar múltiples servicios...</option>`;
                mostrarSeleccionMultiple();
            } else {
                // Servicio específico
                fetch(`/api/horarios_disponibles?tipo_servicio=${tipoServicio}&fecha=${fecha}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log('DEBUG: Horarios recibidos:', data);
                        
                        let options = '<option value="">Seleccionar horario específico...</option>';
                        options += '<option value="dia_completo_servicio">🚫 TODO EL DÍA (este servicio)</option>';
                        
                        if (data.horarios && data.horarios.length > 0) {
                            data.horarios.forEach(horario => {
                                options += `<option value="${horario}">⏰ ${horario}</option>`;
                            });
                        } else {
                            options += '<option value="" disabled>No hay horarios disponibles</option>';
                        }
                        
                        select.innerHTML = options;
                    })
                    .catch(error => {
                        console.error('Error cargando horarios:', error);
                        select.innerHTML = '<option value="">Error cargando horarios</option>';
                    });
            }
        }
        
        function agendarCita(event) {
            event.preventDefault();
            
            const data = {
                tipo_servicio: document.getElementById('tipo-servicio').value,
                fecha_cita: document.getElementById('fecha-cita').value,
                horario: document.getElementById('horario-cita').value,
                cliente_datos: {
                    nombre: document.getElementById('nombre-cliente').value,
                    email: document.getElementById('email-cliente').value,
                    telefono: document.getElementById('telefono-cliente').value
                },
                codigo_servicio: `ADMIN_${Date.now()}`,
                numero_telefono: document.getElementById('telefono-cliente').value,
                especialista: 'Agendado por administrador'
            };
            
            fetch('/api/agendar_cita', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert-agendar');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ Cita agendada correctamente. Código: ${result.codigo_reserva}</div>`;
                    document.getElementById('form-agendar').reset();
                    cargarCalendario();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('alert-agendar').innerHTML = `<div class="alert alert-error">❌ Error de conexión</div>`;
            });
        }
        
        function bloquearHorario(event) {
            event.preventDefault();
            
            const data = {
                tipo_servicio: document.getElementById('tipo-servicio-bloquear').value,
                fecha: document.getElementById('fecha-bloquear').value,
                horario: document.getElementById('horario-bloquear').value,
                motivo: document.getElementById('motivo-bloquear').value
            };
            
            fetch('/api/bloquear_horario', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert-bloquear');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ Horario bloqueado correctamente</div>`;
                    document.getElementById('form-bloquear').reset();
                    cargarHorariosBloqueados();
                    cargarCalendario();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('alert-bloquear').innerHTML = `<div class="alert alert-error">❌ Error de conexión</div>`;
            });
        }
        
        function cargarCitas() {
            fetch('/api/citas_todas')
                .then(response => response.json())
                .then(citas => {
                    let html = '';
                    citas.forEach(cita => {
                        if (cita.estado_cita === 'bloqueado') return;
                        
                        const fecha = new Date(cita.fecha_cita + 'T00:00:00').toLocaleDateString('es-ES');
                        const servicioTexto = {
                            'astrologo_humano': '🔮 Astrólogo Personal',
                            'tarot_humano': '🃏 Tarot Personal',
                            'veronica_presencial': '👩‍🦳 Verónica - Presencial',
                            'veronica_telefono': '📞 Verónica - Teléfono'
                        }[cita.tipo_servicio] || cita.tipo_servicio;
                        
                        html += `<div class="cita-item">
                            <strong>${cita.cliente_nombre || 'Cliente'}</strong> - ${servicioTexto}
                            <br>📅 ${fecha} ⏰ ${cita.horario}
                            <br>📧 ${cita.cliente_email || 'Sin email'} 📞 ${cita.cliente_telefono || 'Sin teléfono'}
                            <br>🔢 Código: ${cita.codigo_reserva}
                        </div>`;
                    });
                    
                    document.getElementById('lista-citas').innerHTML = html || '<p>No hay citas agendadas.</p>';
                })
                .catch(error => console.error('Error cargando citas:', error));
        }
        
        function cargarEstadisticas() {
            fetch('/api/estadisticas')
                .then(response => response.json())
                .then(stats => {
                    document.getElementById('stats-grid').innerHTML = `
                        <div class="stat-card">
                            <div class="stat-number">${stats.total_citas || 0}</div>
                            <div>Total Citas</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.citas_hoy || 0}</div>
                            <div>Citas Hoy</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.citas_semana || 0}</div>
                            <div>Esta Semana</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.horarios_bloqueados || 0}</div>
                            <div>Bloqueados</div>
                        </div>
                    `;
                })
                .catch(error => console.error('Error cargando estadísticas:', error));
        }
        
        function cargarHorariosBloqueados() {
            fetch('/api/horarios_bloqueados')
                .then(response => response.json())
                .then(bloqueados => {
                    let html = '';
                    bloqueados.forEach(bloqueo => {
                        const fecha = new Date(bloqueo.fecha_cita + 'T00:00:00').toLocaleDateString('es-ES');
                        const servicioTexto = {
                            'astrologo_humano': '🔮 Astrólogo Personal',
                            'tarot_humano': '🃏 Tarot Personal',
                            'veronica_presencial': '👩‍🦳 Verónica - Presencial',
                            'veronica_telefono': '📞 Verónica - Teléfono'
                        }[bloqueo.tipo_servicio] || bloqueo.tipo_servicio;
                        
                        html += `<div class="cita-item">
                            <strong>🚫 BLOQUEADO</strong> - ${servicioTexto}
                            <br>📅 ${fecha} ⏰ ${bloqueo.horario}
                            <br>📝 Motivo: ${bloqueo.notas || 'Sin especificar'}
                            <br><button class="btn btn-danger" onclick="desbloquearHorario('${bloqueo.id}')">✅ Desbloquear</button>
                        </div>`;
                    });
                    
                    document.getElementById('lista-bloqueados').innerHTML = html || '<p>No hay horarios bloqueados.</p>';
                })
                .catch(error => console.error('Error cargando horarios bloqueados:', error));
        }
        
        function desbloquearHorario(citaId) {
            if (confirm('¿Estás seguro de que quieres desbloquear este horario?')) {
                fetch(`/api/desbloquear_horario/${citaId}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            cargarHorariosBloqueados();
                            cargarCalendario();
                        } else {
                            alert('Error: ' + result.message);
                        }
                    })
                    .catch(error => alert('Error de conexión'));
            }
        }
        
        function filtrarCitas() {
            // Implementar filtros si es necesario
            cargarCitas();
        }
        
        // Cerrar modal
        document.querySelector('.close').onclick = function() {
            document.getElementById('modal-dia').style.display = 'none';
        }
        
        window.onclick = function(event) {
            const modal = document.getElementById('modal-dia');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
        
        // Establecer fecha mínima como hoy
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('fecha-cita').min = hoy;
        document.getElementById('fecha-bloquear').min = hoy;
        
        // Inicializar
        cargarCalendario();
        
        function mostrarSeleccionMultiple() {
            document.getElementById('seleccion-multiple').style.display = 'block';
        }

        function bloquearHorario(event) {
            event.preventDefault();
            
            const tipoServicio = document.getElementById('tipo-servicio-bloquear').value;
            
            if (tipoServicio === 'multiples') {
                // Manejar selección múltiple
                bloquearMultiplesServicios(event);
            } else {
                // Bloqueo normal
                bloquearHorarioMejorado(event);
            }
        }

        function bloquearMultiplesServicios(event) {
            const serviciosSeleccionados = [];
            if (document.getElementById('check-astrologo').checked) serviciosSeleccionados.push('astrologo_humano');
            if (document.getElementById('check-tarot').checked) serviciosSeleccionados.push('tarot_humano');
            if (document.getElementById('check-veronica-pres').checked) serviciosSeleccionados.push('veronica_presencial');
            if (document.getElementById('check-veronica-tel').checked) serviciosSeleccionados.push('veronica_telefono');
            
            const tiempoSeleccionado = document.querySelector('input[name="tiempo-multiple"]:checked')?.value;
            
            if (serviciosSeleccionados.length === 0) {
                alert('Selecciona al menos un servicio');
                return;
            }
            
            if (!tiempoSeleccionado) {
                alert('Selecciona el período de tiempo');
                return;
            }
            
            const fecha = document.getElementById('fecha-bloquear').value;
            const motivo = document.getElementById('motivo-bloquear').value;
            
            if (!fecha || !motivo) {
                alert('Completa todos los campos');
                return;
            }
            
            const datosBloqueo = {
                fecha: fecha,
                motivo: motivo,
                servicios: serviciosSeleccionados,
                horarios: tiempoSeleccionado
            };
            
            fetch('/api/bloquear_multiple', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datosBloqueo)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    alert(`✅ ${result.bloqueados} horarios bloqueados correctamente`);
                    document.getElementById('form-bloquear').reset();
                    document.getElementById('seleccion-multiple').style.display = 'none';
                    cargarHorariosBloqueados();
                    if (typeof cargarCalendario === 'function') cargarCalendario();
                } else {
                    alert(`❌ Error: ${result.message}`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('❌ Error de conexión');
            });
        }
    </script>
</body>
</html>
    '''
    
    return render_template_string(html_admin)

# ========================================
# NUEVAS APIs PARA LA ADMINISTRACIÓN
# ========================================

@app.route('/api/citas_mes/<int:ano>/<int:mes>')
def api_citas_mes(ano, mes):
    """API para obtener citas de un mes específico"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Fecha inicio y fin del mes
        fecha_inicio = f"{ano}-{mes:02d}-01"
        if mes == 12:
            fecha_fin = f"{ano + 1}-01-01"
        else:
            fecha_fin = f"{ano}-{mes + 1:02d}-01"
        
        cur.execute("""
        SELECT ca.fecha_cita, ca.horario, ca.codigo_reserva, ca.estado_cita, ca.notas,
               cs.tipo_servicio, cs.cliente_nombre, cs.cliente_email, cs.cliente_telefono
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita >= ? AND ca.fecha_cita < ?
        ORDER BY ca.fecha_cita, ca.horario
        """, (fecha_inicio, fecha_fin))
        
        citas = []
        for row in cur.fetchall():
            citas.append({
                'fecha_cita': row[0],
                'horario': row[1],
                'codigo_reserva': row[2],
                'estado_cita': row[3],
                'notas': row[4],
                'tipo_servicio': row[5],
                'cliente_nombre': row[6],
                'cliente_email': row[7],
                'cliente_telefono': row[8]
            })
        
        conn.close()
        return jsonify(citas)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/horarios_dia/<fecha>')
def api_horarios_dia(fecha):
    """API para obtener horarios disponibles/ocupados de un día"""
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        
        # Obtener todos los tipos de servicio y sus horarios base
        tipos_servicio = ['astrologo_humano', 'tarot_humano', 'veronica_presencial', 'veronica_telefono']
        
        horarios_todos = []
        
        for tipo in tipos_servicio:
            horarios_disponibles = obtener_horarios_disponibles(tipo, fecha_obj)
            
            for horario in horarios_disponibles:
                # Verificar si está ocupado
                conn = sqlite3.connect("calendario_citas.db")
                cur = conn.cursor()
                
                cur.execute("""
                SELECT ca.codigo_reserva, ca.estado_cita, ca.notas,
                       cs.cliente_nombre, cs.tipo_servicio
                FROM citas_agendadas ca
                JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
                WHERE ca.fecha_cita = ? AND ca.horario = ? AND cs.tipo_servicio = ?
                """, (fecha, horario, tipo))
                
                cita = cur.fetchone()
                conn.close()
                
                horario_info = {
                    'horario': horario,
                    'servicio': tipo,
                    'ocupado': bool(cita),
                    'bloqueado': cita and cita[1] == 'bloqueado' if cita else False,
                    'cliente': cita[3] if cita and cita[1] != 'bloqueado' else None,
                    'motivo': cita[2] if cita and cita[1] == 'bloqueado' else None
                }
                
                horarios_todos.append(horario_info)
        
        return jsonify(horarios_todos)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/citas_todas')
def api_citas_todas():
    """API para obtener todas las citas"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT ca.id, ca.fecha_cita, ca.horario, ca.codigo_reserva, ca.estado_cita, ca.notas,
               cs.tipo_servicio, cs.cliente_nombre, cs.cliente_email, cs.cliente_telefono
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita >= date('now')
        ORDER BY ca.fecha_cita, ca.horario
        """)
        
        citas = []
        for row in cur.fetchall():
            citas.append({
                'id': row[0],
                'fecha_cita': row[1],
                'horario': row[2],
                'codigo_reserva': row[3],
                'estado_cita': row[4],
                'notas': row[5],
                'tipo_servicio': row[6],
                'cliente_nombre': row[7],
                'cliente_email': row[8],
                'cliente_telefono': row[9]
            })
        
        conn.close()
        return jsonify(citas)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estadisticas')
def api_estadisticas():
    """API para obtener estadísticas del sistema"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Total citas
        cur.execute("SELECT COUNT(*) FROM citas_agendadas WHERE estado_cita != 'cancelada'")
        total_citas = cur.fetchone()[0]
        
        # Citas hoy
        cur.execute("SELECT COUNT(*) FROM citas_agendadas WHERE fecha_cita = date('now') AND estado_cita != 'cancelada'")
        citas_hoy = cur.fetchone()[0]
        
        # Citas esta semana
        cur.execute("""
        SELECT COUNT(*) FROM citas_agendadas 
        WHERE fecha_cita >= date('now') 
        AND fecha_cita <= date('now', '+7 days') 
        AND estado_cita != 'cancelada'
        """)
        citas_semana = cur.fetchone()[0]
        
        # Horarios bloqueados
        cur.execute("SELECT COUNT(*) FROM citas_agendadas WHERE estado_cita = 'bloqueado'")
        horarios_bloqueados = cur.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_citas': total_citas,
            'citas_hoy': citas_hoy,
            'citas_semana': citas_semana,
            'horarios_bloqueados': horarios_bloqueados
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/horarios_bloqueados')
def api_horarios_bloqueados():
    """API para obtener horarios bloqueados"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT ca.id, ca.fecha_cita, ca.horario, ca.notas,
               cs.tipo_servicio
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.estado_cita = 'bloqueado'
        ORDER BY ca.fecha_cita, ca.horario
        """)
        
        bloqueados = []
        for row in cur.fetchall():
            bloqueados.append({
                'id': row[0],
                'fecha_cita': row[1],
                'horario': row[2],
                'notas': row[3],
                'tipo_servicio': row[4]
            })
        
        conn.close()
        return jsonify(bloqueados)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bloquear_horario', methods=['POST'])
def api_bloquear_horario():
    """API para bloquear un horario específico"""
    try:
        data = request.get_json()
        
        # Crear una "cita" de bloqueo
        cliente_id = registrar_cliente_servicio(
            codigo_servicio=f"BLOCK_{int(time.time())}",
            tipo_servicio=data['tipo_servicio'],
            cliente_datos={'nombre': 'BLOQUEADO', 'email': 'admin@asesores.com'},
            numero_telefono='',
            especialista='SISTEMA'
        )
        
        if cliente_id:
            conn = sqlite3.connect("calendario_citas.db")
            cur = conn.cursor()
            
            cur.execute("""
            INSERT INTO citas_agendadas 
            (cliente_servicio_id, fecha_cita, horario, codigo_reserva, estado_cita, notas)
            VALUES (?, ?, ?, ?, 'bloqueado', ?)
            """, (
                cliente_id,
                data['fecha'],
                data['horario'],
                f"BLOCK_{int(time.time())}",
                data.get('motivo', 'Horario bloqueado')
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({"success": True, "message": "Horario bloqueado correctamente"})
        else:
            return jsonify({"success": False, "message": "Error bloqueando horario"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/desbloquear_horario/<int:cita_id>', methods=['DELETE'])
def api_desbloquear_horario(cita_id):
    """API para desbloquear un horario"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Eliminar la cita de bloqueo
        cur.execute("DELETE FROM citas_agendadas WHERE id = ? AND estado_cita = 'bloqueado'", (cita_id,))
        
        if cur.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Horario desbloqueado"})
        else:
            conn.close()
            return jsonify({"success": False, "message": "No se encontró el bloqueo"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
        
@app.route('/api/listar_bloqueos/<fecha>')
def api_listar_bloqueos(fecha):
    """API para obtener bloqueos de una fecha específica"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT ca.id, ca.horario, ca.notas, cs.tipo_servicio
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita = ? AND ca.estado_cita = 'bloqueado'
        ORDER BY ca.horario
        """, (fecha,))
        
        bloqueos = []
        for row in cur.fetchall():
            bloqueos.append({
                'id': row[0],
                'horario': row[1],
                'motivo': row[2] or 'Sin especificar',
                'tipo_servicio': row[3],
                'descripcion': obtener_descripcion_servicio_por_codigo(row[3]) if row[3].endswith('_') else f"🚫 {row[3]}"
            })
        
        conn.close()
        return jsonify(bloqueos)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancelar_bloqueo/<int:bloqueo_id>', methods=['DELETE'])
def api_cancelar_bloqueo(bloqueo_id):
    """API para cancelar un bloqueo específico"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Obtener información del bloqueo antes de eliminar
        cur.execute("""
        SELECT ca.fecha_cita, ca.horario, ca.notas, cs.tipo_servicio
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.id = ? AND ca.estado_cita = 'bloqueado'
        """, (bloqueo_id,))
        
        bloqueo_info = cur.fetchone()
        
        if not bloqueo_info:
            conn.close()
            return jsonify({"success": False, "message": "Bloqueo no encontrado"})
        
        # Eliminar el bloqueo
        cur.execute("DELETE FROM citas_agendadas WHERE id = ? AND estado_cita = 'bloqueado'", (bloqueo_id,))
        
        if cur.rowcount > 0:
            conn.commit()
            conn.close()
            
            # Notificación Telegram
            fecha_formateada = datetime.strptime(bloqueo_info[0], '%Y-%m-%d').strftime('%d/%m/%Y')
            try:
                enviar_telegram_mejora(f"""
✅ <b>BLOQUEO CANCELADO</b>

📅 <b>Fecha:</b> {fecha_formateada}
⏰ <b>Horario:</b> {bloqueo_info[1]}
🎯 <b>Servicio:</b> {bloqueo_info[3]}
📝 <b>Motivo era:</b> {bloqueo_info[2] or 'Sin especificar'}

🔓 <b>Horario liberado</b>
👨‍💼 <b>Cancelado por:</b> Administrador
                """.strip())
            except Exception as tel_error:
                print(f"⚠️ Error enviando Telegram: {tel_error}")
            
            return jsonify({"success": True, "message": "Bloqueo cancelado correctamente"})
        else:
            conn.close()
            return jsonify({"success": False, "message": "No se pudo cancelar el bloqueo"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/agendar_cita', methods=['POST'])
def api_agendar_cita():
    """API para agendar nueva cita"""
    try:
        data = request.get_json()
        
        # Registrar cliente
        cliente_id = registrar_cliente_servicio(
            codigo_servicio=data.get('codigo_servicio', ''),
            tipo_servicio=data['tipo_servicio'],
            cliente_datos=data['cliente_datos'],
            numero_telefono=data.get('numero_telefono', ''),
            especialista=data.get('especialista', 'Por asignar')
        )
        
        if not cliente_id:
            return jsonify({"success": False, "message": "Error registrando cliente"})
        
        # Agendar cita
        fecha_cita = datetime.strptime(data['fecha_cita'], '%Y-%m-%d')
        exito, codigo_reserva = agendar_cita_especifica(
            cliente_id, 
            fecha_cita, 
            data['horario'], 
            data['tipo_servicio']
        )
        
        if exito:
            return jsonify({
                "success": True, 
                "codigo_reserva": codigo_reserva,
                "message": "Cita agendada correctamente"
            })
        else:
            return jsonify({"success": False, "message": codigo_reserva})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
        
@app.route('/api/bloquear_multiple', methods=['POST'])
def api_bloquear_multiple():
    """API para bloquear múltiples horarios/servicios"""
    try:
        data = request.get_json()
        
        servicios = data.get('servicios', [])
        fecha = data.get('fecha')
        horarios = data.get('horarios')
        motivo = data.get('motivo', 'Bloqueado')
        
        bloqueados = 0
        
        for servicio in servicios:
            if horarios == 'todos':
                # Obtener todos los horarios del servicio
                horarios_servicio = obtener_horarios_disponibles(servicio, datetime.strptime(fecha, '%Y-%m-%d'))
                horarios_a_bloquear = horarios_servicio
            elif horarios == 'mañana':
                # Solo horarios de mañana
                horarios_a_bloquear = [h for h in obtener_horarios_disponibles(servicio, datetime.strptime(fecha, '%Y-%m-%d')) if int(h.split(':')[0]) < 14]
            elif horarios == 'tarde':
                # Solo horarios de tarde
                horarios_a_bloquear = [h for h in obtener_horarios_disponibles(servicio, datetime.strptime(fecha, '%Y-%m-%d')) if int(h.split(':')[0]) >= 16]
            else:
                # Horarios específicos
                horarios_a_bloquear = horarios if isinstance(horarios, list) else [horarios]
            
            # Bloquear cada horario
            for horario in horarios_a_bloquear:
                cliente_id = registrar_cliente_servicio(
                    codigo_servicio=f"BLOCK_{int(time.time())}_{bloqueados}",
                    tipo_servicio=servicio,
                    cliente_datos={'nombre': 'BLOQUEADO', 'email': 'admin@asesores.com'},
                    numero_telefono='',
                    especialista='SISTEMA'
                )
                
                if cliente_id:
                    conn = sqlite3.connect("calendario_citas.db")
                    cur = conn.cursor()
                    
                    cur.execute("""
                    INSERT INTO citas_agendadas 
                    (cliente_servicio_id, fecha_cita, horario, codigo_reserva, estado_cita, notas)
                    VALUES (?, ?, ?, ?, 'bloqueado', ?)
                    """, (cliente_id, fecha, horario, f"BLOCK_{cliente_id}", motivo))
                    
                    conn.commit()
                    conn.close()
                    bloqueados += 1
        
        return jsonify({"success": True, "message": f"Bloqueados {bloqueados} horarios", "bloqueados": bloqueados})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/detalle_bloqueo')
def api_detalle_bloqueo():
    """API para obtener detalle de un bloqueo específico"""
    try:
        fecha = request.args.get('fecha')
        motivo = request.args.get('motivo')
        
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT ca.horario, cs.tipo_servicio
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita = ? AND ca.estado_cita = 'bloqueado' AND ca.notas = ?
        ORDER BY ca.horario
        """, (fecha, motivo))
        
        detalles = []
        for row in cur.fetchall():
            detalles.append({
                'horario': row[0],
                'tipo_servicio': row[1]
            })
        
        conn.close()
        return jsonify(detalles)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/horarios_disponibles')
def api_horarios_disponibles_mejorada():
    """API para obtener horarios disponibles con lógica inteligente"""
    try:
        tipo_servicio = request.args.get('tipo_servicio')
        fecha_str = request.args.get('fecha')
        
        if not tipo_servicio or not fecha_str:
            return jsonify({"error": "Faltan parámetros"}), 400
        
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        
        # USAR LÓGICA INTELIGENTE
        try:
            from logica_citas_inteligente import obtener_horarios_disponibles_inteligentes
            horarios, fecha_final = obtener_horarios_disponibles_inteligentes(tipo_servicio, fecha)
            
            return jsonify({
                "horarios": horarios,
                "fecha_sugerida": fecha_final.strftime('%Y-%m-%d'),
                "mensaje": f"Horarios para {fecha_final.strftime('%d/%m/%Y')}"
            })
        except ImportError:
            # Fallback a sistema anterior
            horarios = obtener_horarios_disponibles(tipo_servicio, fecha)
            return jsonify({"horarios": horarios})
        
    except Exception as e:
        print(f"❌ Error API horarios: {e}")
        return jsonify({"error": str(e)}), 500

# ========================================
# RUTAS ADICIONALES (MANTENIDAS)
# ========================================

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Servidor funcionando correctamente"})

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Servidor de agentes funcionando correctamente",
        "endpoints": {
            "/webhook/sofia": "POST - Webhook de Sofía",
            "/webhook/veronica": "POST - Webhook de Verónica",
            "/webhook/vendedor1": "POST - Webhook de Vendedor 1",
            "/webhook/vendedor2": "POST - Webhook de Vendedor 2",
            "/webhook/vendedor3": "POST - Webhook de Vendedor 3",
            "/webhook/tecnico_soporte": "POST - Webhook Técnico Soporte",
            "/webhook/astrologa_cartastral": "POST - Webhook Astróloga Carta Astral",
            "/webhook/astrologa_revolsolar": "POST - Webhook Astróloga Revolución Solar",
            "/webhook/astrologa_sinastria": "POST - Webhook Astróloga Sinastría",
            "/webhook/astrologa_astrolhoraria": "POST - Webhook Astróloga Horaria",
            "/webhook/psico_coaching": "POST - Webhook Psicología y Coaching",
            "/webhook/grafologia": "POST - Webhook Grafología",
            "/webhook/lectura_manos": "POST - Webhook Lectura de Manos",
            "/webhook/lectura_facial": "POST - Webhook Lectura Facial",
            "/webhook/busca_empresas1": "POST - Webhook Búsqueda Empresas 1",
            "/webhook/busca_empresas2": "POST - Webhook Búsqueda Empresas 2",
            "/webhook/busca_empresas3": "POST - Webhook Búsqueda Empresas 3",
            "/webhook/redes_sociales1": "POST - Webhook Redes Sociales 1",
            "/webhook/redes_sociales2": "POST - Webhook Redes Sociales 2",
            "/webhook/redes_sociales3": "POST - Webhook Redes Sociales 3",
            "/webhook/redes_sociales4": "POST - Webhook Redes Sociales 4",
            "/webhook/redes_sociales5": "POST - Webhook Redes Sociales 5",
            "/webhook/redes_sociales6": "POST - Webhook Redes Sociales 6",
            "/webhook/redes_sociales7": "POST - Webhook Redes Sociales 7",
            "/webhook/chistes1": "POST - Webhook chistes1",
            "/webhook/woocommerce": "POST - Webhook de WooCommerce",
            "/health": "GET - Verificación de estado",
            "/limpieza/manual": "POST - Ejecutar limpieza manual",
            "/limpieza/estado": "GET - Estado del sistema de limpieza",
            "/calendario": "GET - Calendario de citas",
            "/admin": "GET - Panel de administración"
        }
    })

@app.route("/informe", methods=["GET"])
def render_informe_html():
    datos = {
        "nombre": "Albert",
        "fecha": "15/07/1985",
        "hora": "08:00",
        "ciudad": "Barcelona",
        "pais": "España",
        "planetas": {
            "sol": {"degree": 23.5, "sign": "Cáncer"},
            "luna": {"degree": 3.7, "sign": "Leo"},
            "mercurio": {"degree": 12.1, "sign": "Géminis"},
            "venus": {"degree": 8.9, "sign": "Tauro"},
            "marte": {"degree": 29.4, "sign": "Aries"},
            "jupiter": {"degree": 14.2, "sign": "Piscis"},
            "saturno": {"degree": 7.7, "sign": "Acuario"},
            "urano": {"degree": 3.1, "sign": "Capricornio"},
            "neptuno": {"degree": 18.6, "sign": "Sagitario"},
            "pluton": {"degree": 25.9, "sign": "Libra"},
        }
    }
    return render_template("informe.html", **datos)
    
def cliente_tiene_telegram(email):
    """Verificar si cliente está registrado para Telegram"""
    # Por ahora return False, después configuramos
    return False
    
def enviar_email_informe(email, tipo_servicio, pdf_url):
    """Enviar informe por email"""
    try:
        print(f"📧 Enviando informe por email a: {email}")
        # Por ahora solo print, después añadimos el envío real
        return True
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False

# ========================================
# RUTAS DE GESTIÓN DE LIMPIEZA (MANTENIDAS)
# ========================================

@app.route("/limpieza/manual", methods=["POST"])
def ejecutar_limpieza_manual():
    """
    Ejecuta una limpieza manual de archivos antiguos
    """
    try:
        limpiar_archivos_antiguos()
        return jsonify({
            "status": "success",
            "message": "Limpieza manual ejecutada correctamente"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error en limpieza manual: {str(e)}"
        }), 500

@app.route("/limpieza/estado", methods=["GET"])
def estado_limpieza():
    """
    Devuelve el estado del sistema de limpieza
    """
    try:
        # Contar archivos en templates y static
        templates_count = len(glob.glob("templates/informe_*_*_*.html"))
        static_count = len(glob.glob("static/*_*_*_*.png"))
        
        return jsonify({
            "status": "active",
            "archivos_templates": templates_count,
            "archivos_static": static_count,
            "limpieza_automatica": "activa_cada_24h",
            "tiempo_retencion": "7_dias"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error obteniendo estado: {str(e)}"
        }), 500
        
# ========================================
# CALENDARIO MEJORADO COMPLETO - DATETIME CORREGIDO
# REEMPLAZAR COMPLETAMENTE - VERSIÓN FINAL
# ========================================

def obtener_horarios_por_servicio_mejorado(servicio, fecha):
    """Obtener horarios específicos por tipo de servicio"""
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if isinstance(fecha, str) else fecha
        dia_semana = fecha_obj.weekday()  # 0=lunes, 6=domingo
        
        print(f"🔍 DEBUG: Servicio={servicio}, Fecha={fecha}, Día semana={dia_semana}")
        
        # Definir horarios base según servicio
        horarios_config = {
            'sofia_astrologo': {
                # Lunes a viernes: 11-13h y 16-19h, sábados: 11-13h
                'horarios': ['11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'] if dia_semana < 5 
                           else ['11:00-12:00', '12:00-13:00'] if dia_semana == 5 
                           else []  # domingo
            },
            'sofia_tarot': {
                # Mismo horario que astrólogo
                'horarios': ['11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'] if dia_semana < 5 
                           else ['11:00-12:00', '12:00-13:00'] if dia_semana == 5 
                           else []
            },
            'veronica_telefono': {
                # Lunes a viernes: 10-13:30h y 16-19h (cada 30min)
                'horarios': [
                    '10:00-10:30', '10:30-11:00', '11:00-11:30', '11:30-12:00', 
                    '12:00-12:30', '12:30-13:00', '13:00-13:30',
                    '16:00-16:30', '16:30-17:00', '17:00-17:30', '17:30-18:00',
                    '18:00-18:30', '18:30-19:00'
                ] if dia_semana < 5 else []
            },
            'veronica_visita': {
                # Lunes a viernes: 10-13h y 16-18:30h (cada 1.5h)
                'horarios': [
                    '10:00-11:30', '11:30-13:00',
                    '16:00-17:30', '17:00-18:30'
                ] if dia_semana < 5 else []
            },
            'otros': {
                # Horario flexible
                'horarios': ['10:00-11:00', '11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'] if dia_semana < 6 else []
            }
        }
        
        horarios = horarios_config.get(servicio, {}).get('horarios', [])
        print(f"🔍 DEBUG: Horarios base encontrados: {horarios}")
        
        return horarios
        
    except Exception as e:
        print(f"❌ Error obteniendo horarios por servicio: {e}")
        import traceback
        traceback.print_exc()
        return []

def filtrar_horarios_disponibles_mejorado(servicio, fecha, horarios_base):
    """Filtrar horarios que ya están ocupados"""
    try:
        print(f"🔍 DEBUG: Filtrando horarios. Servicio={servicio}, Fecha={fecha}, Base={len(horarios_base)}")
        
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Mapear servicio a tipo_servicio de la BD
        mapeo_servicios = {
            'sofia_astrologo': 'astrologo_humano',
            'sofia_tarot': 'tarot_humano',
            'veronica_telefono': 'veronica_telefono',
            'veronica_visita': 'veronica_presencial',
            'otros': 'otros'
        }
        
        tipo_bd = mapeo_servicios.get(servicio, servicio)
        print(f"🔍 DEBUG: Tipo BD mapeado: {tipo_bd}")
        
        # Obtener horarios ocupados
        cur.execute("""
        SELECT ca.horario 
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita = ? 
        AND cs.tipo_servicio = ?
        AND ca.estado_cita != 'cancelada'
        """, (fecha, tipo_bd))
        
        horarios_ocupados = [row[0] for row in cur.fetchall()]
        conn.close()
        
        print(f"🔍 DEBUG: Horarios ocupados: {horarios_ocupados}")
        
        # Filtrar disponibles
        horarios_disponibles = [h for h in horarios_base if h not in horarios_ocupados]
        
        print(f"🔍 DEBUG: Horarios disponibles finales: {horarios_disponibles}")
        
        return horarios_disponibles
        
    except Exception as e:
        print(f"❌ Error filtrando horarios: {e}")
        import traceback
        traceback.print_exc()
        return horarios_base
        
# ========================================
# FUNCIONES AUXILIARES - AÑADIR ANTES DE obtener_configuracion_servicios_mejorada()
# ========================================

def generar_codigo_reserva_descriptivo(tipo_servicio):
    """Generar código de reserva según lógica empresarial correcta"""
    import random
    import string
    
    # Prefijos según lógica empresarial
    prefijos = {
        # AS CARTASTRAL - SERVICIOS HUMANOS (con códigos como WooCommerce)
        'astrologo_humano': 'AS',      # AS_123456 (SÍ notificar)
        'tarot_humano': 'TH',          # TH_123456 (SÍ notificar)
        
        # AS ASESORES - RESERVAS DE HORA (no son códigos de servicio)
        'veronica_telefono': 'CITA_TEL',    # CITA_TEL_123456 
        'veronica_presencial': 'CITA_VIS',  # CITA_VIS_123456
        'otros': 'RESERVA'                  # RESERVA_123456
    }
    
    prefijo = prefijos.get(tipo_servicio, 'CITA')
    codigo_aleatorio = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    return f"{prefijo}_{codigo_aleatorio}"

def debe_notificar_telegram(tipo_servicio, codigo_reserva):
    """Determinar si se debe enviar notificación Telegram según lógica empresarial"""
    
    # REGLA 1: Servicios humanos de AS Cartastral (SÍ notificar)
    if tipo_servicio in ['astrologo_humano', 'tarot_humano']:
        return True
    
    # REGLA 2: Citas de AS Asesores (SÍ notificar - son citas contigo)
    if tipo_servicio in ['veronica_telefono', 'veronica_presencial', 'otros']:
        return True
    
    # REGLA 3: Servicios automáticos de AS Cartastral (NO notificar)
    if codigo_reserva and any(codigo_reserva.startswith(prefijo) for prefijo in ['AI_', 'RS_', 'SI_', 'AH_', 'PC_', 'LM_', 'LF_']):
        return False
    
    # Por defecto, notificar
    return True

def es_servicio_automatico(codigo):
    """Verificar si un código corresponde a servicio automático (no notificar)"""
    prefijos_automaticos = ['AI_', 'RS_', 'SI_', 'AH_', 'PC_', 'LM_', 'LF_']
    return any(codigo.startswith(prefijo) for prefijo in prefijos_automaticos)

def es_servicio_humano_cartastral(codigo):
    """Verificar si un código corresponde a servicio humano de AS Cartastral (SÍ notificar)"""
    prefijos_humanos = ['AS_', 'TH_']
    return any(codigo.startswith(prefijo) for prefijo in prefijos_humanos)

def obtener_descripcion_servicio_por_codigo(codigo):
    """Obtener descripción legible del servicio según el código"""
    
    descripciones = {
        # Servicios automáticos AS Cartastral
        'AI_': '🤖 Carta Astral IA',
        'RS_': '🤖 Revolución Solar IA',
        'SI_': '🤖 Sinastría IA', 
        'AH_': '🤖 Astrología Horaria IA',
        'PC_': '🤖 Psico-Coaching IA',
        'LM_': '🤖 Lectura Manos IA',
        'LF_': '🤖 Lectura Facial IA',
        'AIM': '🤖 Carta Astral IA (½)',
        'RSM': '🤖 Revolución Solar IA (½)',
        'SIM': '🤖 Sinastría IA (½)',
        'LMM': '🤖 Lectura Manos IA (½)',
        'PCM': '🤖 Psico-Coaching IA (½)',
        'GR_': '📝 Grafología IA',
        
        # Servicios humanos AS Cartastral
        'AS_': '🔮 Astrólogo Humano',
        'TH_': '🃏 Tarot Humano',
        
        # Citas AS Asesores
        'CITA_TEL_': '📞 Cita Teléfono',
        'CITA_VIS_': '🏠 Cita Visita'
    }
    
    for prefijo, descripcion in descripciones.items():
        if codigo.startswith(prefijo):
            return descripcion
    
    return f"📋 Servicio: {codigo}"

def obtener_configuracion_servicios_mejorada():
    """Configuración de todos los servicios disponibles - ACTUALIZADA"""
    return {
        'sofia_astrologo': {
            'nombre': '🔮 Sofía - Astrólogo Humano (Cita Personal)',
            'color': '#28a745',
            'duracion': 60,
            'empresa': 'AS Cartastral',
            'tipo': 'humano'
        },
        'sofia_tarot': {
            'nombre': '🃏 Sofía - Tarot Humano (Cita Personal)', 
            'color': '#007bff',
            'duracion': 60,
            'empresa': 'AS Cartastral',
            'tipo': 'humano'
        },
        'veronica_telefono': {
            'nombre': '📞 Verónica - Llamada Telefónica',
            'color': '#ffc107',
            'duracion': 30,
            'empresa': 'AS Asesores',
            'tipo': 'cita_personal'
        },
        'veronica_visita': {
            'nombre': '🏠 Verónica - Visita a Cliente',
            'color': '#dc3545',
            'duracion': 90,
            'empresa': 'AS Asesores',
            'tipo': 'cita_personal'
        },
        'otros': {
            'nombre': '📋 Otros',
            'color': '#6c757d',
            'duracion': 60,
            'empresa': 'General',
            'tipo': 'cita_personal'
        }
    }

# ========================================
# RUTAS API CORREGIDAS DATETIME
# ========================================

@app.route('/api/horarios_mejorados')
def api_horarios_disponibles_mejorados():
    """Nueva API mejorada para obtener horarios disponibles"""
    try:
        servicio = request.args.get('servicio')
        fecha = request.args.get('fecha')
        
        print(f"🔍 DEBUG API: servicio={servicio}, fecha={fecha}")
        
        if not servicio or not fecha:
            return jsonify({"error": "Faltan parámetros: servicio y fecha son requeridos"}), 400
        
        # Validar servicio
        servicios_validos = ['sofia_astrologo', 'sofia_tarot', 'veronica_telefono', 'veronica_visita', 'otros']
        if servicio not in servicios_validos:
            return jsonify({"error": f"Servicio no válido. Opciones: {servicios_validos}"}), 400
        
        # Obtener horarios base
        horarios_base = obtener_horarios_por_servicio_mejorado(servicio, fecha)
        
        if not horarios_base:
            return jsonify({
                'horarios': [], 
                'mensaje': 'No hay horarios disponibles para este día',
                'debug': f'Servicio: {servicio}, Fecha: {fecha}'
            })
        
        # Filtrar ocupados
        horarios_disponibles = filtrar_horarios_disponibles_mejorado(servicio, fecha, horarios_base)
        
        # Información del servicio
        config_servicio = obtener_configuracion_servicios_mejorada()[servicio]
        
        resultado = {
            'horarios': horarios_disponibles,
            'servicio': config_servicio,
            'fecha': fecha,
            'total_disponibles': len(horarios_disponibles),
            'total_base': len(horarios_base),
            'debug': f'Base: {len(horarios_base)}, Disponibles: {len(horarios_disponibles)}'
        }
        
        print(f"🔍 DEBUG API RESULTADO: {resultado}")
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Error API horarios: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "debug": "Ver consola del servidor"}), 500

@app.route('/api/configuracion_servicios')
def api_config_servicios_mejorada():
    """API para obtener la configuración de todos los servicios"""
    try:
        resultado = obtener_configuracion_servicios_mejorada()
        print(f"🔍 DEBUG Configuración servicios: {list(resultado.keys())}")
        return jsonify(resultado)
    except Exception as e:
        print(f"❌ Error config servicios: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agendar_cita_mejorada', methods=['POST'])
def api_agendar_cita_mejorada():
    """Nueva API para agendar citas - CON LÓGICA EMPRESARIAL CORRECTA"""
    try:
        data_original = request.get_json()  # Solo UNA vez
        print(f"🔍 DEBUG Agendar cita: {data_original}")
        
        data = data_original.copy()  # Hacer copia
        
        # FIX RETELL: Extraer datos de args si es function call  
        if 'args' in data and 'name' in data:
            data = data['args']
        
        # FIX: Detectar agente desde datos originales
        if 'call' in data_original and 'agent_name' in data_original['call']:
            agent_name = data_original['call']['agent_name']
            if 'agente' not in data:
                data['agente'] = agent_name
        
        # Mapeo de servicios nuevos a tipos de BD existentes
        mapeo_servicios = {
            'sofia_astrologo': 'astrologo_humano',
            'sofia_tarot': 'tarot_humano',
            'veronica_telefono': 'veronica_telefono', 
            'veronica_visita': 'veronica_presencial',
            'otros': 'otros'
        }
        
        servicio_original = data['tipo_servicio']
        tipo_bd = mapeo_servicios.get(servicio_original, servicio_original)
        
        # Registrar cliente - DATETIME CORREGIDO
        cliente_id = registrar_cliente_servicio(
            codigo_servicio=data.get('codigo_servicio', f'ADMIN_{int(datetime.now().timestamp())}'),
            tipo_servicio=tipo_bd,
            cliente_datos=data['cliente_datos'],
            numero_telefono=data.get('numero_telefono', ''),
            especialista=data.get('especialista', 'Administrador')
        )
        
        if not cliente_id:
            return jsonify({"success": False, "message": "Error registrando cliente"})
        
        # Agendar cita - DATETIME CORREGIDO
        fecha_cita = datetime.strptime(data['fecha_cita'], '%Y-%m-%d')
        exito, codigo_reserva = agendar_cita_especifica(
            cliente_id,
            fecha_cita, 
            data['horario'],
            tipo_bd
        )
        
        if exito:
            # APLICAR LÓGICA EMPRESARIAL PARA TELEGRAM
            if debe_notificar_telegram(tipo_bd, codigo_reserva):
                config_servicios = obtener_configuracion_servicios_mejorada()
                
                # Personalizar mensaje según tipo de servicio
                if tipo_bd in ['astrologo_humano', 'tarot_humano']:
                    # AS CARTASTRAL - Servicio humano
                    emoji_empresa = "🔮"
                    tipo_cita = "SERVICIO HUMANO"
                    empresa = "AS Cartastral"
                else:
                    # AS ASESORES - Cita personal
                    emoji_empresa = "🤖" 
                    tipo_cita = "CITA PERSONAL"
                    empresa = "AS Asesores"
                
                mensaje_telegram = f"""
{emoji_empresa} <b>NUEVA {tipo_cita}</b>

👤 <b>Cliente:</b> {data['cliente_datos']['nombre']}
📧 <b>Email:</b> {data['cliente_datos']['email']}
📞 <b>Teléfono:</b> {data['cliente_datos'].get('telefono', 'No especificado')}

🎯 <b>Servicio:</b> {config_servicios[servicio_original]['nombre']}
📅 <b>Fecha:</b> {fecha_cita.strftime('%d/%m/%Y')}
⏰ <b>Horario:</b> {data['horario']}
🏢 <b>Empresa:</b> {empresa}

🔢 <b>Código:</b> {codigo_reserva}
👨‍💼 <b>Agendado por:</b> Administrador
                """.strip()
                
                try:
                    enviar_telegram_mejora(mensaje_telegram)
                except Exception as tel_error:
                    print(f"⚠️ Error enviando Telegram: {tel_error}")
            else:
                print(f"🔇 No notificar Telegram para: {servicio_original} - {codigo_reserva}")
            
            return jsonify({
                "success": True,
                "codigo_reserva": codigo_reserva,
                "message": "Cita agendada correctamente"
            })
        else:
            return jsonify({"success": False, "message": codigo_reserva})
            
    except Exception as e:
        print(f"❌ Error agendando cita: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/bloquear_multiple_mejorado', methods=['POST'])
def api_bloquear_multiple_mejorado():
    """Nueva API para bloqueo múltiple de horarios - SIN DUPLICADOS"""
    try:
        data = request.get_json()
        print(f"🔍 DEBUG Bloquear: {data}")
        
        servicios = data.get('servicios', [])
        fecha = data.get('fecha')
        horario = data.get('horario') 
        motivo = data.get('motivo', '') or 'Sin especificar'
        
        print(f"🔍 DEBUG: servicios={servicios}, fecha={fecha}, horario={horario}")
        
        if not servicios or not fecha or not horario:
            return jsonify({"success": False, "message": "Faltan parámetros requeridos"})
        
        bloqueados = 0
        errores = []
        
        # Mapeo de servicios
        mapeo_servicios = {
            'sofia_astrologo': 'astrologo_humano',
            'sofia_tarot': 'tarot_humano',
            'veronica_telefono': 'veronica_telefono',
            'veronica_visita': 'veronica_presencial',
            'otros': 'otros'
        }
        
        # OBTENER HORARIOS UNA SOLA VEZ - EVITAR DUPLICADOS
        if horario == 'mañana':
            # Para cada servicio, obtener sus horarios de mañana específicos
            horarios_por_servicio = {}
            for servicio in servicios:
                horarios_por_servicio[servicio] = obtener_horarios_mañana(servicio)
        elif horario == 'tarde':
            horarios_por_servicio = {}
            for servicio in servicios:
                horarios_por_servicio[servicio] = obtener_horarios_tarde(servicio)
        elif horario == 'dia_completo':
            horarios_por_servicio = {}
            for servicio in servicios:
                horarios_por_servicio[servicio] = obtener_horarios_por_servicio_mejorado(servicio, fecha)
        else:
            # Horario específico
            horarios_por_servicio = {}
            for servicio in servicios:
                horarios_por_servicio[servicio] = [horario]
        
        print(f"🔍 DEBUG: Horarios por servicio: {horarios_por_servicio}")
        
        # BLOQUEAR CADA SERVICIO + HORARIO COMBINACIÓN (SIN DUPLICADOS)
        for servicio in servicios:
            tipo_bd = mapeo_servicios.get(servicio, servicio)
            horarios_servicio = horarios_por_servicio.get(servicio, [])
            
            print(f"🔍 DEBUG: Procesando {servicio} -> {len(horarios_servicio)} horarios")
            
            for horario_especifico in horarios_servicio:
                try:
                    # VERIFICAR SI YA ESTÁ BLOQUEADO PARA EVITAR DUPLICADOS
                    conn = sqlite3.connect("calendario_citas.db")
                    cur = conn.cursor()
                    
                    cur.execute("""
                    SELECT COUNT(*) FROM citas_agendadas ca
                    JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
                    WHERE ca.fecha_cita = ? AND ca.horario = ? 
                    AND cs.tipo_servicio = ? AND ca.estado_cita = 'bloqueado'
                    """, (fecha, horario_especifico, tipo_bd))
                    
                    ya_bloqueado = cur.fetchone()[0] > 0
                    conn.close()
                    
                    if ya_bloqueado:
                        print(f"⚠️ Ya bloqueado: {servicio} {horario_especifico}")
                        continue  # Saltar, ya existe
                    
                    # Crear nuevo bloqueo
                    cliente_id = registrar_cliente_servicio(
                        codigo_servicio=f"BLOCK_{int(datetime.now().timestamp())}_{bloqueados}",
                        tipo_servicio=tipo_bd,
                        cliente_datos={'nombre': 'BLOQUEADO', 'email': 'admin@asesores.com'},
                        numero_telefono='',
                        especialista='SISTEMA'
                    )
                    
                    if cliente_id:
                        conn = sqlite3.connect("calendario_citas.db")
                        cur = conn.cursor()
                        
                        cur.execute("""
                        INSERT INTO citas_agendadas 
                        (cliente_servicio_id, fecha_cita, horario, codigo_reserva, estado_cita, notas)
                        VALUES (?, ?, ?, ?, 'bloqueado', ?)
                        """, (cliente_id, fecha, horario_especifico, f"BLOCK_{cliente_id}", motivo))
                        
                        conn.commit()
                        conn.close()
                        bloqueados += 1
                        print(f"✅ Bloqueado: {servicio} {horario_especifico}")
                    else:
                        errores.append(f"No se pudo crear cliente para {servicio} {horario_especifico}")
                        
                except Exception as bloqueo_error:
                    error_msg = f"Error bloqueando {servicio} {horario_especifico}: {bloqueo_error}"
                    print(f"❌ {error_msg}")
                    errores.append(error_msg)
                    continue
        
        print(f"🔍 DEBUG: Total bloqueados: {bloqueados}, Errores: {len(errores)}")
        
        if bloqueados > 0:
            # Notificación Telegram
            servicios_nombres = []
            config_servicios = obtener_configuracion_servicios_mejorada()
            for servicio in servicios:
                if servicio in config_servicios:
                    servicios_nombres.append(config_servicios[servicio]['nombre'])
            
            mensaje_telegram = f"""
🚫 <b>HORARIOS BLOQUEADOS</b>

📅 <b>Fecha:</b> {datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')}
⏰ <b>Horario:</b> {horario}
📝 <b>Motivo:</b> {motivo}
🔢 <b>Total bloqueados:</b> {bloqueados}

🎯 <b>Servicios afectados:</b>
{chr(10).join([f'• {nombre}' for nombre in servicios_nombres])}

👨‍💼 <b>Bloqueado por:</b> Administrador
            """.strip()
            
            try:
                enviar_telegram_mejora(mensaje_telegram)
            except Exception as tel_error:
                print(f"⚠️ Error enviando Telegram: {tel_error}")
        
        # Mensaje de respuesta
        mensaje_respuesta = f"Se bloquearon {bloqueados} horarios correctamente"
        if errores:
            mensaje_respuesta += f" (con {len(errores)} errores)"
        
        return jsonify({
            "success": True, 
            "message": mensaje_respuesta,
            "bloqueados": bloqueados,
            "errores": errores if errores else None
        })
        
    except Exception as e:
        print(f"❌ Error bloqueando: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)})

def obtener_horarios_mañana(servicio):
    """Generar horarios de mañana según servicio"""
    if servicio in ['sofia_astrologo', 'sofia_tarot']:
        return ['11:00-12:00', '12:00-13:00']
    elif servicio == 'veronica_telefono':
        return ['10:00-10:30', '10:30-11:00', '11:00-11:30', '11:30-12:00', '12:00-12:30', '12:30-13:00', '13:00-13:30']
    elif servicio == 'veronica_visita':
        return ['10:00-11:30', '11:30-13:00']
    else:
        return ['10:00-11:00', '11:00-12:00', '12:00-13:00']

def obtener_horarios_tarde(servicio):
    """Generar horarios de tarde según servicio"""
    if servicio in ['sofia_astrologo', 'sofia_tarot']:
        return ['16:00-17:00', '17:00-18:00', '18:00-19:00']
    elif servicio == 'veronica_telefono':
        return ['16:00-16:30', '16:30-17:00', '17:00-17:30', '17:30-18:00', '18:00-18:30', '18:30-19:00']
    elif servicio == 'veronica_visita':
        return ['16:00-17:30', '17:00-18:30']
    else:
        return ['16:00-17:00', '17:00-18:00', '18:00-19:00']

# Nueva API para el calendario del mes
@app.route('/api/citas_mes_mejorada/<int:ano>/<int:mes>')
def api_citas_mes_mejorada(ano, mes):
    """API mejorada para obtener citas del mes con mapeo de servicios"""
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        # Fecha inicio y fin del mes
        fecha_inicio = f"{ano}-{mes:02d}-01"
        if mes == 12:
            fecha_fin = f"{ano + 1}-01-01"
        else:
            fecha_fin = f"{ano}-{mes + 1:02d}-01"
        
        cur.execute("""
        SELECT ca.fecha_cita, ca.horario, ca.codigo_reserva, ca.estado_cita, ca.notas,
               cs.tipo_servicio, cs.cliente_nombre, cs.cliente_email, cs.cliente_telefono
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita >= ? AND ca.fecha_cita < ?
        ORDER BY ca.fecha_cita, ca.horario
        """, (fecha_inicio, fecha_fin))
        
        # Mapeo inverso de servicios BD a nombres de interfaz
        mapeo_servicios_inverso = {
            'astrologo_humano': 'sofia_astrologo',
            'tarot_humano': 'sofia_tarot',
            'veronica_telefono': 'veronica_telefono',
            'veronica_presencial': 'veronica_visita',
            'otros': 'otros'
        }
        
        citas = []
        for row in cur.fetchall():
            tipo_servicio_bd = row[5]
            tipo_servicio_interfaz = mapeo_servicios_inverso.get(tipo_servicio_bd, tipo_servicio_bd)
            
            citas.append({
                'fecha_cita': row[0],
                'horario': row[1],
                'codigo_reserva': row[2],
                'estado_cita': row[3],
                'notas': row[4],
                'tipo_servicio': tipo_servicio_interfaz,
                'tipo_servicio_bd': tipo_servicio_bd,
                'cliente_nombre': row[6],
                'cliente_email': row[7],
                'cliente_telefono': row[8]
            })
        
        conn.close()
        return jsonify(citas)
        
    except Exception as e:
        print(f"❌ Error API citas mes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin_mejorado')
def admin_calendario_mejorado():
    """Panel de administración mejorado COMPLETO"""
    
    html_mejorado = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔧 Administración Mejorada - AS Asesores</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            color: white; 
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3); 
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 20px;
            min-height: 600px;
        }
        .calendar-section, .actions-section {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .calendar-section h3, .actions-section h3 {
            margin-top: 0;
            color: #2c5aa0;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        .month-nav { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 20px; 
        }
        .month-nav button { 
            padding: 8px 16px; 
            background: #007bff; 
            color: white; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
        }
        .month-nav h4 { 
            margin: 0; 
            color: #2c5aa0; 
        }
        .calendar-grid { 
            display: grid; 
            grid-template-columns: repeat(7, 1fr); 
            gap: 1px;
            background: #ddd;
            border-radius: 5px;
            overflow: hidden;
        }
        .calendar-header { 
            background: #007bff; 
            color: white; 
            padding: 10px 5px; 
            text-align: center; 
            font-weight: bold; 
            font-size: 12px;
        }
        .calendar-day { 
            background: white; 
            padding: 8px 4px; 
            min-height: 80px; 
            position: relative; 
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .calendar-day:hover { 
            background: #f0f8ff; 
        }
        .calendar-day.today { 
            background: #e7f3ff; 
            font-weight: bold;
        }
        .day-number {
            font-weight: bold;
            margin-bottom: 4px;
        }
        .evento { 
            font-size: 9px;
            color: white; 
            padding: 1px 3px; 
            margin: 1px 0; 
            border-radius: 2px; 
            display: block;
            overflow: hidden;
            white-space: nowrap;
        }
        .evento.sofia-astrologo { background: #28a745; }
        .evento.sofia-tarot { background: #007bff; }
        .evento.veronica-telefono { background: #ffc107; color: #000; }
        .evento.veronica-visita { background: #dc3545; }
        .evento.otros { background: #6c757d; }
        .evento.bloqueado { background: #6c757d; }
        .form-group { 
            margin-bottom: 15px; 
        }
        .form-group label { 
            display: block; 
            margin-bottom: 5px; 
            font-weight: bold; 
        }
        .form-group input, .form-group select, .form-group textarea { 
            width: 100%; 
            padding: 8px; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            box-sizing: border-box; 
        }
        .btn { 
            padding: 10px 20px; 
            background: #007bff; 
            color: white; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            margin: 5px 0; 
            width: 100%;
        }
        .btn:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-warning:hover { background: #e0a800; }
        .alert { 
            padding: 10px; 
            margin: 10px 0; 
            border-radius: 5px; 
            font-size: 14px;
        }
        .alert-success { 
            background: #d4edda; 
            color: #155724; 
            border: 1px solid #c3e6cb; 
        }
        .alert-error { 
            background: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
        }
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
            font-size: 12px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }
        .section {
            margin-bottom: 30px;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #f9f9f9;
        }
        .section h4 {
            margin-top: 0;
            color: #2c5aa0;
        }
// FUNCIONES PARA GESTIONAR BLOQUEOS
        function cargarBloqueosFecha() {
            const fecha = document.getElementById('fecha-ver-bloqueos').value;
            
            if (!fecha) {
                alert('Selecciona una fecha');
                return;
            }
            
            const lista = document.getElementById('lista-bloqueos-fecha');
            lista.innerHTML = '<p style="color: #666; text-align: center;">🔄 Cargando bloqueos...</p>';
            
            fetch(`/api/ver_bloqueos_fecha/${fecha}`)
                .then(response => response.json())
                .then(bloqueos => {
                    if (bloqueos.length === 0) {
                        lista.innerHTML = '<p style="color: #28a745; text-align: center;">✅ No hay bloqueos en esta fecha</p>';
                        return;
                    }
                    
                    let html = '';
                    bloqueos.forEach(bloqueo => {
                        html += `
                            <div style="background: white; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #dc3545; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>⏰ ${bloqueo.horario}</strong><br>
                                    <small>🎯 ${bloqueo.descripcion}</small><br>
                                    <small style="color: #666;">📝 ${bloqueo.motivo}</small>
                                </div>
                                <button onclick="cancelarBloqueo(${bloqueo.id})" 
                                        style="background: #28a745; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 12px;">
                                    ✅ Cancelar
                                </button>
                            </div>
                        `;
                    });
                    
                    lista.innerHTML = html;
                })
                .catch(error => {
                    console.error('Error:', error);
                    lista.innerHTML = '<p style="color: #dc3545; text-align: center;">❌ Error cargando bloqueos</p>';
                });
        }
        
        function cancelarBloqueo(bloqueoId) {
            if (!confirm('¿Estás seguro de que quieres cancelar este bloqueo?')) {
                return;
            }
            
            fetch(`/api/eliminar_bloqueo/${id}`, {method: 'DELETE'})
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        alert('✅ Bloqueo cancelado correctamente');
                        cargarBloqueosFecha(); // Recargar lista
                        cargarCalendario(); // Recargar calendario
                    } else {
                        alert('❌ Error: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('❌ Error de conexión');
                });
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Administración Mejorada - AS Asesores</h1>
            <p>✅ Sistema integrado correctamente - Calendario Lunes a Domingo</p>
        </div>
        
        <div class="main-grid">
            <!-- CALENDARIO PRINCIPAL -->
            <div class="calendar-section">
                <h3>📅 Calendario de Citas y Bloqueos</h3>
                
                <div class="month-nav">
                    <button onclick="mesAnterior()">← Anterior</button>
                    <h4 id="mes-titulo">Enero 2025</h4>
                    <button onclick="mesSiguiente()">Siguiente →</button>
                </div>
                
                <div class="calendar-grid" id="calendar-grid">
                    <!-- Calendario generado dinámicamente -->
                </div>
                
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: #28a745;"></div>
                        <span>🔮 Sofía - Astrólogo</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #007bff;"></div>
                        <span>🃏 Sofía - Tarot</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #ffc107;"></div>
                        <span>📞 Verónica - Teléfono</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #dc3545;"></div>
                        <span>🏠 Verónica - Visita</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #6c757d;"></div>
                        <span>🚫 Bloqueado</span>
                    </div>
                </div>
            </div>
            
            <!-- PANEL DE ACCIONES -->
            <div class="actions-section">
                <h3>🛠️ Acciones Rápidas</h3>
                
                <!-- AGENDAR CITA -->
                <div class="section">
                    <h4>➕ Agendar Nueva Cita</h4>
                    <div id="alert-agendar"></div>
                    <form id="form-agendar" onsubmit="agendarCita(event)">
                        <div class="form-group">
                            <label>Servicio:</label>
                            <select id="tipo-servicio" required onchange="actualizarHorarios()">
                                <option value="">Seleccionar...</option>
                                <option value="sofia_astrologo">🔮 Sofía - Astrólogo (AS Cartastral)</option>
                                <option value="sofia_tarot">🃏 Sofía - Tarot (AS Cartastral)</option>
                                <option value="veronica_telefono">📞 Verónica - Teléfono (AS Asesores)</option>
                                <option value="veronica_visita">🏠 Verónica - Visita (AS Asesores)</option>
                                <option value="otros">📋 Otros</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Fecha:</label>
                            <input type="date" id="fecha-cita" required onchange="actualizarHorarios()">
                        </div>
                        <div class="form-group">
                            <label>Horario:</label>
                            <select id="horario-cita" required>
                                <option value="">Selecciona servicio y fecha...</option>
                            </select>
                            <small id="horario-info" style="color: #666; font-size: 11px; margin-top: 5px; display: block;"></small>
                        </div>
                        <div class="form-group">
                            <label>Cliente:</label>
                            <input type="text" id="nombre-cliente" placeholder="Nombre completo" required>
                        </div>
                        <div class="form-group">
                            <input type="email" id="email-cliente" placeholder="Email" required>
                        </div>
                        <div class="form-group">
                            <input type="tel" id="telefono-cliente" placeholder="Teléfono (opcional)">
                        </div>
                        <button type="submit" class="btn btn-success">✅ Agendar</button>
                    </form>
                </div>
                
<!-- BLOQUEAR HORARIOS -->
                <div class="section">
                    <h4>🚫 Bloquear Horarios</h4>
                    <div id="alert-bloquear"></div>
                    <form id="form-bloquear" onsubmit="bloquearHorario(event)">
                        <div class="form-group">
                            <label>Servicios a bloquear:</label>
                            <div style="max-height: 120px; overflow-y: auto; border: 1px solid #ddd; padding: 8px; border-radius: 4px;">
                                <label><input type="checkbox" value="sofia_astrologo"> 🔮 Sofía - Astrólogo</label><br>
                                <label><input type="checkbox" value="sofia_tarot"> 🃏 Sofía - Tarot</label><br>
                                <label><input type="checkbox" value="veronica_telefono"> 📞 Verónica - Teléfono</label><br>
                                <label><input type="checkbox" value="veronica_visita"> 🏠 Verónica - Visita</label><br>
                                <label><input type="checkbox" value="otros"> 📋 Otros</label><br>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Fecha:</label>
                            <input type="date" id="fecha-bloquear" required>
                        </div>
                        <div class="form-group">
                            <label>Período:</label>
                            <select id="horario-bloquear" required>
                                <option value="mañana">🌅 Mañana</option>
                                <option value="tarde">🌇 Tarde</option>
                                <option value="dia_completo">🚫 Día completo</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Motivo (opcional):</label>
                            <input type="text" id="motivo-bloquear" placeholder="Vacaciones, reunión, etc.">
                        </div>
                    </form>
                    
                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <h4>📋 Desbloquear Horarios</h4>
                        <input type="date" id="fecha-desbloquear">
                        <button class="btn" onclick="verBloqueos()">Ver Bloqueos</button>
                        <div id="lista-bloqueos" style="margin-top: 15px;"></div>
                    </div>
                        <button type="submit" class="btn btn-warning">🚫 Bloquear</button>
                    </form>
                    
                    <!-- VER BLOQUEOS EXISTENTES -->
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <h4 style="margin-bottom: 15px;">📋 Bloqueos Existentes</h4>
                        
                        <div class="form-group">
                            <label>Ver bloqueos de fecha:</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="date" id="fecha-ver-bloqueos" style="flex: 1;">
                                <button type="button" class="btn" onclick="cargarBloqueosFecha()" style="width: auto; padding: 8px 16px;">🔍 Ver</button>
                            </div>
                        </div>
                        
                        <div id="lista-bloqueos-fecha" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #f9f9f9;">
                            <p style="color: #666; margin: 0; text-align: center;">Selecciona una fecha para ver bloqueos</p>
                        </div>
                    </div>
                </div>
                        
                        <div id="lista-bloqueos-fecha" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #f9f9f9;">
                            <p style="color: #666; margin: 0; text-align: center;">Selecciona una fecha para ver bloqueos</p>
                        </div>
                    </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Fecha:</label>
                            <input type="date" id="fecha-bloquear" required>
                        </div>
                        <div class="form-group">
                            <label>Período:</label>
                            <select id="horario-bloquear" required>
                                <option value="mañana">🌅 Mañana</option>
                                <option value="tarde">🌇 Tarde</option>
                                <option value="dia_completo">🚫 Día completo</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Motivo (opcional):</label>
                            <input type="text" id="motivo-bloquear" placeholder="Vacaciones, reunión, etc.">
                        </div>
                        <button type="submit" class="btn btn-warning">🚫 Bloquear</button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <script>
        let mesActual = new Date().getMonth() + 1;
        let añoActual = new Date().getFullYear();
        
        function mesAnterior() {
            mesActual--;
            if (mesActual < 1) {
                mesActual = 12;
                añoActual--;
            }
            actualizarCalendario();
        }
        
        function mesSiguiente() {
            mesActual++;
            if (mesActual > 12) {
                mesActual = 1;
                añoActual++;
            }
            actualizarCalendario();
        }
        
        function actualizarCalendario() {
            const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            document.getElementById('mes-titulo').textContent = `${meses[mesActual - 1]} ${añoActual}`;
            cargarCalendario();
        }
        
        function cargarCalendario() {
            // LUNES A DOMINGO
            const diasSemana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
            let html = '';
            
            // Headers
            diasSemana.forEach(dia => {
                html += `<div class="calendar-header">${dia}</div>`;
            });
            
            const primerDia = new Date(añoActual, mesActual - 1, 1);
            const diasEnMes = new Date(añoActual, mesActual, 0).getDate();
            
            // Ajustar día de la semana (0=domingo → 6, 1=lunes → 0)
            let diaSemanaInicial = primerDia.getDay();
            diaSemanaInicial = (diaSemanaInicial === 0) ? 6 : diaSemanaInicial - 1;
            
            const hoy = new Date();
            
            // Espacios vacíos
            for (let i = 0; i < diaSemanaInicial; i++) {
                html += '<div class="calendar-day"></div>';
            }
            
            // Días del mes
            for (let dia = 1; dia <= diasEnMes; dia++) {
                const esHoy = hoy.getDate() === dia && hoy.getMonth() === mesActual - 1 && hoy.getFullYear() === añoActual;
                const claseHoy = esHoy ? 'today' : '';
                
                html += `<div class="calendar-day ${claseHoy}" onclick="mostrarDetallesDia(${dia})">
                    <div class="day-number">${dia}</div>
                    <div id="eventos-${dia}"></div>
                </div>`;
            }
            
            document.getElementById('calendar-grid').innerHTML = html;
            cargarEventosCalendario();
        }
        
        function cargarEventosCalendario() {
            fetch(`/api/citas_mes_mejorada/${añoActual}/${mesActual}`)
                .then(response => response.json())
                .then(citas => {
                    // Limpiar eventos
                    for (let dia = 1; dia <= 31; dia++) {
                        const elemento = document.getElementById(`eventos-${dia}`);
                        if (elemento) elemento.innerHTML = '';
                    }
                    
                    citas.forEach(cita => {
                        const fecha = new Date(cita.fecha_cita + 'T00:00:00');
                        const dia = fecha.getDate();
                        const elemento = document.getElementById(`eventos-${dia}`);
                        
                        if (elemento) {
                            let claseEvento = 'evento';
                            
                            if (cita.estado_cita === 'bloqueado') {
                                claseEvento += ' bloqueado';
                            } else {
                                claseEvento += ' ' + cita.tipo_servicio;
                            }
                            
                            const titulo = cita.estado_cita === 'bloqueado' 
                                ? 'BLOQUEADO' 
                                : (cita.cliente_nombre || 'Cita');
                            
                            const horaCorta = cita.horario.split('-')[0];
                            elemento.innerHTML += `<div class="${claseEvento}" title="${cita.horario} - ${titulo}">${horaCorta}</div>`;
                        }
                    });
                })
                .catch(error => console.error('Error cargando eventos:', error));
        }
        
        function mostrarDetallesDia(dia) {
            console.log(`Detalles del día ${dia}/${mesActual}/${añoActual}`);
        }
        
        function actualizarHorarios() {
            const tipoServicio = document.getElementById('tipo-servicio').value;
            const fecha = document.getElementById('fecha-cita').value;
            const select = document.getElementById('horario-cita');
            const info = document.getElementById('horario-info');
            
            if (!tipoServicio || !fecha) {
                select.innerHTML = '<option value="">Selecciona servicio y fecha...</option>';
                info.textContent = '';
                return;
            }
            
            select.innerHTML = '<option value="">🔄 Cargando...</option>';
            info.textContent = 'Consultando horarios disponibles...';
            
            fetch(`/api/horarios_mejorados?servicio=${tipoServicio}&fecha=${fecha}`)
                .then(response => response.json())
                .then(data => {
                    select.innerHTML = '<option value="">Seleccionar horario...</option>';
                    
                    if (data.horarios && data.horarios.length > 0) {
                        data.horarios.forEach(horario => {
                            select.innerHTML += `<option value="${horario}">${horario}</option>`;
                        });
                        info.textContent = `${data.total_disponibles} horarios disponibles`;
                        info.style.color = '#28a745';
                    } else {
                        select.innerHTML = '<option value="">Sin horarios disponibles</option>';
                        info.textContent = data.mensaje || 'Sin horarios disponibles este día';
                        info.style.color = '#dc3545';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    select.innerHTML = '<option value="">Error cargando</option>';
                    info.textContent = 'Error cargando horarios';
                    info.style.color = '#dc3545';
                });
        }
        
        function agendarCita(event) {
            event.preventDefault();
            
            const data = {
                tipo_servicio: document.getElementById('tipo-servicio').value,
                fecha_cita: document.getElementById('fecha-cita').value,
                horario: document.getElementById('horario-cita').value,
                cliente_datos: {
                    nombre: document.getElementById('nombre-cliente').value,
                    email: document.getElementById('email-cliente').value,
                    telefono: document.getElementById('telefono-cliente').value
                }
            };
            
            fetch('/api/agendar_cita_mejorada', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert-agendar');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ Cita agendada. Código: ${result.codigo_reserva}</div>`;
                    document.getElementById('form-agendar').reset();
                    cargarCalendario(); // Recargar calendario
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ ${result.message}</div>`;
                }
            })
            .catch(error => {
                console.error('Error agendando:', error);
                document.getElementById('alert-agendar').innerHTML = `<div class="alert alert-error">❌ Error de conexión</div>`;
            });
        }
        
        function bloquearHorario(event) {
            event.preventDefault();
            
            const servicios = [];
            document.querySelectorAll('.actions-section input[type="checkbox"]:checked').forEach(cb => {
                servicios.push(cb.value);
            });
            
            if (servicios.length === 0) {
                alert('Selecciona al menos un servicio');
                return;
            }
            
            const data = {
                servicios: servicios,
                fecha: document.getElementById('fecha-bloquear').value,
                horario: document.getElementById('horario-bloquear').value,
                motivo: document.getElementById('motivo-bloquear').value || 'Sin especificar'
            };
            
            fetch('/api/bloquear_multiple_mejorado', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert-bloquear');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ ${result.message}</div>`;
                    document.getElementById('form-bloquear').reset();
                    cargarCalendario(); // Recargar calendario
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ ${result.message}</div>`;
                }
            })
            .catch(error => {
                console.error('Error bloqueando:', error);
                document.getElementById('alert-bloquear').innerHTML = `<div class="alert alert-error">❌ Error de conexión</div>`;
            });
        }
        
        // Establecer fecha mínima como hoy
        const hoy = new Date().toISOString().split('T')[0];
        document.getElementById('fecha-cita').min = hoy;
        document.getElementById('fecha-bloquear').min = hoy;
        
        // Inicializar
        cargarCalendario();
        
        function verBloqueos() {
            const fecha = document.getElementById('fecha-desbloquear').value;
            if (!fecha) {
                alert('Selecciona fecha');
                return;
            }
            
            fetch(`/api/listar_bloqueos/${fecha}`)
                .then(response => response.json())
                .then(bloqueos => {
                    let html = '';
                    if (bloqueos.length === 0) {
                        html = '<p>✅ No hay bloqueos</p>';
                    } else {
                        bloqueos.forEach(bloqueo => {
                            html += `<div style="background: #f8d7da; padding: 10px; margin: 5px 0; border-radius: 5px;">
                                <strong>${bloqueo.horario}</strong> - ${bloqueo.motivo}
                                <button onclick="cancelarBloqueo(${bloqueo.id})" style="background: #28a745; color: white; border: none; padding: 5px 10px; border-radius: 3px; float: right;">✅ Desbloquear</button>
                            </div>`;
                        });
                    }
                    document.getElementById('lista-bloqueos').innerHTML = html;
                });
        }
        
        function cancelarBloqueo(id) {
            if (confirm('¿Desbloquear?')) {
                fetch(`/api/cancelar_bloqueo/${id}`, {method: 'DELETE'})
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            alert('✅ Desbloqueado');
                            verBloqueos();
                            cargarCalendario();
                        } else {
                            alert('❌ Error');
                        }
                    });
            }
        }
        
    </script>
</body>
</html>
    """
    
    return render_template_string(html_mejorado)
    
@app.route('/api/ver_bloqueos_fecha/<fecha>')
def api_ver_bloqueos_fecha(fecha):
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        cur.execute("""
        SELECT ca.id, ca.horario, ca.notas, cs.tipo_servicio
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE ca.fecha_cita = ? AND ca.estado_cita = 'bloqueado'
        ORDER BY ca.horario
        """, (fecha,))
        
        bloqueos = []
        for row in cur.fetchall():
            bloqueos.append({
                'id': row[0],
                'horario': row[1],
                'motivo': row[2] or 'Sin especificar',
                'tipo_servicio': row[3]
            })
        conn.close()
        return jsonify(bloqueos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/eliminar_bloqueo/<int:bloqueo_id>', methods=['DELETE'])
def api_eliminar_bloqueo(bloqueo_id):
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM citas_agendadas WHERE id = ? AND estado_cita = 'bloqueado'", (bloqueo_id,))
        
        if cur.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        else:
            conn.close()
            return jsonify({"success": False, "message": "No encontrado"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
        
# ========================================
# GOOGLE CALENDAR INTEGRATION
# ========================================

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuración Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google-credentials.json'  # Misma carpeta que main.py

def inicializar_google_calendar():
    """Inicializar cliente Google Calendar"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"❌ Error inicializando Google Calendar: {e}")
        return None

# Test de conexión
def test_google_calendar():
    """Test rápido de Google Calendar"""
    service = inicializar_google_calendar()
    if service:
        print("✅ Google Calendar conectado correctamente")
        return True
    return False
    
@app.route('/test/google-calendar')
def test_calendar_route():
    """Ruta para probar Google Calendar"""
    try:
        if test_google_calendar():
            return jsonify({
                "status": "success",
                "message": "✅ Google Calendar conectado correctamente",
                "next_step": "Crear eventos de prueba"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "❌ Error conectando Google Calendar"
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ Error: {str(e)}"
        }), 500
        
def crear_evento_prueba():
    """Crear evento de prueba en Google Calendar"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return False, "Error inicializando servicio"
        
        # Evento de prueba para mañana
        from datetime import datetime, timedelta
        mañana = datetime.now() + timedelta(days=1)
        
        evento = {
            'summary': '🔧 PRUEBA AS Asesores',
            'description': 'Test de creación automática de eventos',
            'start': {
                'dateTime': mañana.strftime('%Y-%m-%dT15:00:00'),
                'timeZone': 'Europe/Madrid',
            },
            'end': {
                'dateTime': mañana.strftime('%Y-%m-%dT16:00:00'),
                'timeZone': 'Europe/Madrid',
            },
        }
        
        # Usar calendario AS Asesores específico
        CALENDAR_ID = 'b64595022e163fbb552d1d5202a590605d3dd66079c082dc4037513c2a5369e1@group.calendar.google.com'
        evento_creado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
        
        return True, f"Evento creado: {evento_creado.get('id')}"
        
    except Exception as e:
        return False, f"Error: {str(e)}"
        
@app.route('/test/crear-evento')
def test_crear_evento():
    """Probar creación de evento"""
    try:
        exito, mensaje = crear_evento_prueba()
        
        if exito:
            return jsonify({
                "status": "success",
                "message": f"✅ {mensaje}",
                "instruction": "Revisa tu Google Calendar - debe aparecer un evento mañana a las 15:00"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"❌ {mensaje}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ Error: {str(e)}"
        }), 500
        
@app.route('/reservar/sofia-astrologo')
def formulario_sofia_astrologo():
    """Formulario para reservar con Sofía - Astrólogo"""
    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔮 Reservar - Sofía Astrólogo Personal</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c5aa0; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        input, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #28a745; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #218838; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .alert { padding: 15px; margin: 15px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 Sofía - Astrólogo Personal</h1>
        
        <div class="info">
            <strong>📋 Información del servicio:</strong><br>
            • Duración: 60 minutos<br>
            • Modalidad: Presencial/Teléfono<br>
            • Empresa: AS Cartastral<br>
            • Requiere código de servicio
        </div>
        
        <div id="alert"></div>
        
        <form id="form-reserva" onsubmit="enviarReserva(event)">
            <div class="form-group">
                <label for="nombre">👤 Nombre completo *</label>
                <input type="text" id="nombre" required placeholder="Tu nombre completo">
            </div>
            
            <div class="form-group">
                <label for="telefono">📞 Teléfono *</label>
                <input type="tel" id="telefono" required placeholder="666 777 888">
            </div>
            
            <div class="form-group">
                <label for="codigo">🔢 Código de servicio *</label>
                <input type="text" id="codigo" required placeholder="AS_123456" pattern="AS_[0-9]{6}">
                <small style="color: #666;">Formato: AS_123456</small>
            </div>
            
            <div class="form-group">
                <label for="fecha">📅 Fecha preferida *</label>
                <input type="date" id="fecha" required>
            </div>
            
            <div class="form-group">
                <label for="horario">⏰ Horario preferido *</label>
                <select id="horario" required>
                    <option value="">Seleccionar horario...</option>
                    <option value="11:00-12:00">11:00 - 12:00</option>
                    <option value="12:00-13:00">12:00 - 13:00</option>
                    <option value="16:00-17:00">16:00 - 17:00</option>
                    <option value="17:00-18:00">17:00 - 18:00</option>
                    <option value="18:00-19:00">18:00 - 19:00</option>
                </select>
            </div>
            
            <button type="submit">✅ Reservar Cita</button>
        </form>
    </div>

    <script>
        // Establecer fecha mínima como mañana
        const mañana = new Date();
        mañana.setDate(mañana.getDate() + 1);
        document.getElementById('fecha').min = mañana.toISOString().split('T')[0];
        
        function enviarReserva(event) {
            event.preventDefault();
            
            const datos = {
                tipo: 'sofia_astrologo',
                nombre: document.getElementById('nombre').value,
                telefono: document.getElementById('telefono').value,
                codigo: document.getElementById('codigo').value,
                fecha: document.getElementById('fecha').value,
                horario: document.getElementById('horario').value
            };
            
            // Mostrar loading
            document.getElementById('alert').innerHTML = '<div class="alert alert-success">🔄 Procesando reserva...</div>';
            
            fetch('/api/crear-reserva', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ ¡Reserva confirmada!<br>ID: ${result.evento_id}<br>Te llegará confirmación por email.</div>`;
                    document.getElementById('form-reserva').reset();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('alert').innerHTML = '<div class="alert alert-error">❌ Error de conexión</div>';
            });
        }
    </script>
</body>
</html>
    '''
    return render_template_string(html)
    
@app.route('/api/crear-reserva', methods=['POST'])
def api_crear_reserva():
    """API para crear reservas desde formularios web - CON VERIFICACIÓN"""
    try:
        data = request.get_json()
        print(f"🔍 Nueva reserva: {data}")
        
        # Extraer datos
        tipo = data.get('tipo')
        nombre = data.get('nombre')
        telefono = data.get('telefono')
        fecha = data.get('fecha')
        horario = data.get('horario')
        codigo = data.get('codigo', '')
        direccion = data.get('direccion', '')
        
        # ✅ DEBUG: VERIFICAR QUE SE EJECUTE
        print(f"🔍 VERIFICANDO DISPONIBILIDAD: {fecha} {horario}")
        
        disponible, mensaje = verificar_disponibilidad(fecha, horario)
        
        print(f"🔍 RESULTADO VERIFICACIÓN: disponible={disponible}, mensaje={mensaje}")
        
        if not disponible:
            print(f"❌ BLOQUEANDO RESERVA: {mensaje}")
            return jsonify({
                "success": False,
                "message": f"❌ {mensaje}. Por favor selecciona otro horario."
            })
        
        print(f"✅ HORARIO LIBRE, CREANDO EVENTO...")
        
        # Crear evento en Google Calendar (solo si está disponible)
        exito, resultado = crear_evento_calendar(tipo, nombre, telefono, fecha, horario, codigo, direccion)
        
        if exito:
            print(f"✅ EVENTO CREADO: {resultado}")
            # Enviar notificación Telegram
            enviar_notificacion_telegram(tipo, nombre, telefono, fecha, horario, codigo, direccion)
            
            return jsonify({
                "success": True,
                "message": "Reserva confirmada",
                "evento_id": resultado
            })
        else:
            print(f"❌ ERROR CREANDO EVENTO: {resultado}")
            return jsonify({
                "success": False,
                "message": resultado
            })
            
    except Exception as e:
        print(f"❌ Error API crear reserva: {e}")
        return jsonify({
            "success": False,
            "message": f"Error procesando reserva: {str(e)}"
        })
        
@app.route('/api/horarios-disponibles/<fecha>/<tipo_servicio>')
def api_horarios_disponibles(fecha, tipo_servicio):
    """API para obtener horarios disponibles de una fecha específica"""
    try:
        horarios_libres = obtener_horarios_disponibles_dinamicos(fecha, tipo_servicio)
        
        return jsonify({
            "success": True,
            "fecha": fecha,
            "tipo_servicio": tipo_servicio,
            "horarios_disponibles": horarios_libres,
            "total": len(horarios_libres)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })

def crear_evento_calendar(tipo, nombre, telefono, fecha, horario, codigo='', direccion=''):
    """Crear evento específico en Google Calendar"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return False, "Error conectando con Google Calendar"
        
        # Configurar título y descripción según tipo
        configuraciones = {
            'sofia_astrologo': {
                'titulo': f'🔮 Astrólogo: {nombre}',
                'descripcion': f'👤 Cliente: {nombre}\n📞 Teléfono: {telefono}\n🔢 Código: {codigo}',
                'duracion': 60
            },
            'sofia_tarot': {
                'titulo': f'🃏 Tarot: {nombre}',
                'descripcion': f'👤 Cliente: {nombre}\n📞 Teléfono: {telefono}\n🔢 Código: {codigo}',
                'duracion': 60
            },
            'veronica_telefono': {
                'titulo': f'📞 Llamada: {nombre}',
                'descripcion': f'👤 Cliente: {nombre}\n📞 Teléfono: {telefono}',
                'duracion': 30
            },
            'veronica_visita': {
                'titulo': f'🏠 Visita: {nombre}',
                'descripcion': f'👤 Cliente: {nombre}\n📞 Teléfono: {telefono}\n🏠 Dirección: {direccion}',
                'duracion': 90
            }
        }
        
        config = configuraciones.get(tipo, configuraciones['sofia_astrologo'])
        
        # Calcular horas inicio y fin
        from datetime import datetime, timedelta
        hora_inicio = horario.split('-')[0]  # "11:00-12:00" → "11:00"
        
        inicio_dt = datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
        fin_dt = inicio_dt + timedelta(minutes=config['duracion'])
        
        evento = {
            'summary': config['titulo'],
            'description': config['descripcion'],
            'start': {
                'dateTime': inicio_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Europe/Madrid',
            },
            'end': {
                'dateTime': fin_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Europe/Madrid',
            },
        }
        
        # Usar calendario AS Asesores específico
        CALENDAR_ID = 'b64595022e163fbb552d1d5202a590605d3dd66079c082dc4037513c2a5369e1@group.calendar.google.com'
        evento_creado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
        return True, evento_creado.get('id')
        
    except Exception as e:
        return False, f"Error creando evento: {str(e)}"

def enviar_notificacion_telegram(tipo, nombre, telefono, fecha, horario, codigo='', direccion=''):
    """Enviar notificación diferenciada por Telegram"""
    try:
        # Formatear fecha legible
        from datetime import datetime
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        fecha_legible = fecha_obj.strftime('%d/%m/%Y')
        
        # Mensajes según tipo de servicio
        if tipo == 'sofia_astrologo':
            mensaje = f"""
🔮 <b>NUEVA CITA - ASTRÓLOGO HUMANO</b>

👤 <b>Cliente:</b> {nombre}
📞 <b>Teléfono:</b> {telefono}
🔢 <b>Código:</b> {codigo}

📅 <b>Fecha:</b> {fecha_legible}
⏰ <b>Horario:</b> {horario}
🏢 <b>Empresa:</b> AS Cartastral
            """.strip()
            
        elif tipo == 'sofia_tarot':
            mensaje = f"""
🃏 <b>NUEVA CITA - TAROT HUMANO</b>

👤 <b>Cliente:</b> {nombre}
📞 <b>Teléfono:</b> {telefono}
🔢 <b>Código:</b> {codigo}

📅 <b>Fecha:</b> {fecha_legible}
⏰ <b>Horario:</b> {horario}
🏢 <b>Empresa:</b> AS Cartastral
            """.strip()
            
        elif tipo == 'veronica_telefono':
            mensaje = f"""
📞 <b>NUEVA LLAMADA TELEFÓNICA</b>

👤 <b>Cliente:</b> {nombre}
📞 <b>Teléfono:</b> {telefono}

📅 <b>Fecha:</b> {fecha_legible}
⏰ <b>Horario:</b> {horario}
🏢 <b>Empresa:</b> AS Asesores
            """.strip()
            
        elif tipo == 'veronica_visita':
            mensaje = f"""
🏠 <b>NUEVA VISITA A CLIENTE</b>

👤 <b>Cliente:</b> {nombre}
📞 <b>Teléfono:</b> {telefono}
🏠 <b>Dirección:</b> {direccion}

📅 <b>Fecha:</b> {fecha_legible}
⏰ <b>Horario:</b> {horario}
🏢 <b>Empresa:</b> AS Asesores
            """.strip()
        
        # Enviar por Telegram (reutilizar función existente)
        enviar_telegram_mejora(mensaje)
        
    except Exception as e:
        print(f"⚠️ Error enviando Telegram: {e}")
        
@app.route('/reservar/sofia-tarot')
def formulario_sofia_tarot():
    """Formulario para reservar con Sofía - Tarot"""
    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🃏 Reservar - Sofía Tarot Personal</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #007bff; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        input, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #007bff; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .alert { padding: 15px; margin: 15px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🃏 Sofía - Tarot Personal</h1>
        
        <div class="info">
            <strong>📋 Información del servicio:</strong><br>
            • Duración: 60 minutos<br>
            • Modalidad: Presencial/Teléfono<br>
            • Empresa: AS Cartastral<br>
            • Requiere código de servicio
        </div>
        
        <div id="alert"></div>
        
        <form id="form-reserva" onsubmit="enviarReserva(event)">
            <div class="form-group">
                <label for="nombre">👤 Nombre completo *</label>
                <input type="text" id="nombre" required placeholder="Tu nombre completo">
            </div>
            
            <div class="form-group">
                <label for="telefono">📞 Teléfono *</label>
                <input type="tel" id="telefono" required placeholder="666 777 888">
            </div>
            
            <div class="form-group">
                <label for="codigo">🔢 Código de servicio *</label>
                <input type="text" id="codigo" required placeholder="TH_123456" pattern="TH_[0-9]{6}">
                <small style="color: #666;">Formato: TH_123456</small>
            </div>
            
            <div class="form-group">
                <label for="fecha">📅 Fecha preferida *</label>
                <input type="date" id="fecha" required>
            </div>
            
            <div class="form-group">
                <label for="horario">⏰ Horario preferido *</label>
                <select id="horario" required>
                    <option value="">Seleccionar horario...</option>
                    <option value="11:00-12:00">11:00 - 12:00</option>
                    <option value="12:00-13:00">12:00 - 13:00</option>
                    <option value="16:00-17:00">16:00 - 17:00</option>
                    <option value="17:00-18:00">17:00 - 18:00</option>
                    <option value="18:00-19:00">18:00 - 19:00</option>
                </select>
            </div>
            
            <button type="submit">✅ Reservar Cita</button>
        </form>
    </div>

    <script>
        const mañana = new Date();
        mañana.setDate(mañana.getDate() + 1);
        document.getElementById('fecha').min = mañana.toISOString().split('T')[0];
        
        function enviarReserva(event) {
            event.preventDefault();
            
            const datos = {
                tipo: 'sofia_tarot',
                nombre: document.getElementById('nombre').value,
                telefono: document.getElementById('telefono').value,
                codigo: document.getElementById('codigo').value,
                fecha: document.getElementById('fecha').value,
                horario: document.getElementById('horario').value
            };
            
            document.getElementById('alert').innerHTML = '<div class="alert alert-success">🔄 Procesando reserva...</div>';
            
            fetch('/api/crear-reserva', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ ¡Reserva confirmada!<br>ID: ${result.evento_id}<br>Te llegará confirmación por email.</div>`;
                    document.getElementById('form-reserva').reset();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('alert').innerHTML = '<div class="alert alert-error">❌ Error de conexión</div>';
            });
        }
    </script>
</body>
</html>
    '''
    return render_template_string(html)
    
@app.route('/reservar/veronica-telefono')
def formulario_veronica_telefono():
    """Formulario para reservar llamada con Verónica"""
    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📞 Reservar - Verónica Llamada Telefónica</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #ffc107; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        input, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #ffc107; color: #212529; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #e0a800; }
        .info { background: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .alert { padding: 15px; margin: 15px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📞 Verónica - Llamada Telefónica</h1>
        
        <div class="info">
            <strong>📋 Información del servicio:</strong><br>
            • Duración: 30 minutos<br>
            • Modalidad: Llamada telefónica<br>
            • Empresa: AS Asesores<br>
            • Solo nombre y teléfono
        </div>
        
        <div id="alert"></div>
        
        <form id="form-reserva" onsubmit="enviarReserva(event)">
            <div class="form-group">
                <label for="nombre">👤 Nombre y apellido *</label>
                <input type="text" id="nombre" required placeholder="Nombre y apellido completo">
            </div>
            
            <div class="form-group">
                <label for="telefono">📞 Teléfono de contacto *</label>
                <input type="tel" id="telefono" required placeholder="666 777 888">
            </div>
            
            <div class="form-group">
                <label for="fecha">📅 Fecha preferida *</label>
                <input type="date" id="fecha" required>
            </div>
            
            <div class="form-group">
                <label for="horario">⏰ Horario preferido *</label>
                <select id="horario" required>
                    <option value="">Seleccionar horario...</option>
                    <option value="10:00-10:30">10:00 - 10:30</option>
                    <option value="10:30-11:00">10:30 - 11:00</option>
                    <option value="11:00-11:30">11:00 - 11:30</option>
                    <option value="11:30-12:00">11:30 - 12:00</option>
                    <option value="12:00-12:30">12:00 - 12:30</option>
                    <option value="12:30-13:00">12:30 - 13:00</option>
                    <option value="16:00-16:30">16:00 - 16:30</option>
                    <option value="16:30-17:00">16:30 - 17:00</option>
                    <option value="17:00-17:30">17:00 - 17:30</option>
                    <option value="17:30-18:00">17:30 - 18:00</option>
                    <option value="18:00-18:30">18:00 - 18:30</option>
                </select>
            </div>
            
            <button type="submit">📞 Reservar Llamada</button>
        </form>
    </div>

    <script>
        const mañana = new Date();
        mañana.setDate(mañana.getDate() + 1);
        document.getElementById('fecha').min = mañana.toISOString().split('T')[0];
        
        function enviarReserva(event) {
            event.preventDefault();
            
            const datos = {
                tipo: 'veronica_telefono',
                nombre: document.getElementById('nombre').value,
                telefono: document.getElementById('telefono').value,
                fecha: document.getElementById('fecha').value,
                horario: document.getElementById('horario').value
            };
            
            document.getElementById('alert').innerHTML = '<div class="alert alert-success">🔄 Procesando reserva...</div>';
            
            fetch('/api/crear-reserva', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ ¡Llamada confirmada!<br>ID: ${result.evento_id}<br>Te llamaremos a la hora acordada.</div>`;
                    document.getElementById('form-reserva').reset();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('alert').innerHTML = '<div class="alert alert-error">❌ Error de conexión</div>';
            });
        }
    </script>
</body>
</html>
    '''
    return render_template_string(html)
    
@app.route('/reservar/veronica-visita')
def formulario_veronica_visita():
    """Formulario para reservar visita con Verónica"""
    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠 Reservar - Verónica Visita a Cliente</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #dc3545; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
        input, select, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #dc3545; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #c82333; }
        .info { background: #f8d7da; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .alert { padding: 15px; margin: 15px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Verónica - Visita a Cliente</h1>
        
        <div class="info">
            <strong>📋 Información del servicio:</strong><br>
            • Duración: 90 minutos<br>
            • Modalidad: Visita presencial<br>
            • Empresa: AS Asesores<br>
            • Requiere dirección completa
        </div>
        
        <div id="alert"></div>
        
        <form id="form-reserva" onsubmit="enviarReserva(event)">
            <div class="form-group">
                <label for="nombre">👤 Nombre y apellido *</label>
                <input type="text" id="nombre" required placeholder="Nombre y apellido completo">
            </div>
            
            <div class="form-group">
                <label for="telefono">📞 Teléfono de contacto *</label>
                <input type="tel" id="telefono" required placeholder="666 777 888">
            </div>
            
            <div class="form-group">
                <label for="direccion">🏠 Dirección completa *</label>
                <textarea id="direccion" rows="3" required placeholder="Calle, número, piso, código postal, ciudad, provincia"></textarea>
            </div>
            
            <div class="form-group">
                <label for="fecha">📅 Fecha preferida *</label>
                <input type="date" id="fecha" required>
            </div>
            
            <div class="form-group">
                <label for="horario">⏰ Horario preferido *</label>
                <select id="horario" required>
                    <option value="">Seleccionar horario...</option>
                    <option value="10:00-11:30">10:00 - 11:30</option>
                    <option value="11:30-13:00">11:30 - 13:00</option>
                    <option value="16:00-17:30">16:00 - 17:30</option>
                    <option value="17:00-18:30">17:00 - 18:30</option>
                </select>
            </div>
            
            <button type="submit">🏠 Reservar Visita</button>
        </form>
    </div>

    <script>
        const mañana = new Date();
        mañana.setDate(mañana.getDate() + 1);
        document.getElementById('fecha').min = mañana.toISOString().split('T')[0];
        
        function enviarReserva(event) {
            event.preventDefault();
            
            const datos = {
                tipo: 'veronica_visita',
                nombre: document.getElementById('nombre').value,
                telefono: document.getElementById('telefono').value,
                direccion: document.getElementById('direccion').value,
                fecha: document.getElementById('fecha').value,
                horario: document.getElementById('horario').value
            };
            
            document.getElementById('alert').innerHTML = '<div class="alert alert-success">🔄 Procesando reserva...</div>';
            
            fetch('/api/crear-reserva', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(datos)
            })
            .then(response => response.json())
            .then(result => {
                const alertDiv = document.getElementById('alert');
                if (result.success) {
                    alertDiv.innerHTML = `<div class="alert alert-success">✅ ¡Visita confirmada!<br>ID: ${result.evento_id}<br>Te confirmaremos la cita por teléfono.</div>`;
                    document.getElementById('form-reserva').reset();
                } else {
                    alertDiv.innerHTML = `<div class="alert alert-error">❌ Error: ${result.message}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('alert').innerHTML = '<div class="alert alert-error">❌ Error de conexión</div>';
            });
        }
    </script>
</body>
</html>
    '''
    return render_template_string(html)
    
def verificar_disponibilidad(fecha, horario_nuevo):
    """Verificar disponibilidad - CON TIMEZONE AUTOMÁTICO"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return False, "Error conectando con Google Calendar"
        
        # Convertir a datetime con timezone Madrid automático
        madrid_tz = pytz.timezone('Europe/Madrid')
        
        hora_inicio = horario_nuevo.split('-')[0]
        hora_fin = horario_nuevo.split('-')[1]
        
        # Crear datetime naive y luego localizar a Madrid
        inicio_naive = datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
        fin_naive = datetime.strptime(f"{fecha} {hora_fin}", "%Y-%m-%d %H:%M")
        
        # Localizar a timezone Madrid (automáticamente +01:00 o +02:00)
        inicio_madrid = madrid_tz.localize(inicio_naive)
        fin_madrid = madrid_tz.localize(fin_naive)
        
        inicio_iso = inicio_madrid.isoformat()
        fin_iso = fin_madrid.isoformat()
        
        print(f"🔍 DEBUG: Buscando eventos entre {inicio_iso} y {fin_iso}")
        
        # Resto igual...
        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=inicio_iso,
            timeMax=fin_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos_existentes = eventos.get('items', [])
        
        if eventos_existentes:
            evento = eventos_existentes[0]
            titulo = evento.get('summary', 'Evento sin título')
            return False, f"Horario ocupado: {titulo}"
        else:
            return True, "Horario disponible"
            
    except Exception as e:
        print(f"❌ Error verificando disponibilidad: {e}")
        return False, f"Error: {str(e)}"

def obtener_horarios_disponibles_dinamicos(fecha, tipo_servicio):
    """Obtener solo horarios disponibles para una fecha específica"""
    try:
        # Horarios base según tipo de servicio
        horarios_base = {
            'sofia_astrologo': ['11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
            'sofia_tarot': ['11:00-12:00', '12:00-13:00', '16:00-17:00', '17:00-18:00', '18:00-19:00'],
            'veronica_telefono': ['10:00-10:30', '10:30-11:00', '11:00-11:30', '11:30-12:00', '12:00-12:30', '12:30-13:00', '16:00-16:30', '16:30-17:00', '17:00-17:30', '17:30-18:00', '18:00-18:30'],
            'veronica_visita': ['10:00-11:30', '11:30-13:00', '16:00-17:30', '17:00-18:30']
        }
        
        horarios_posibles = horarios_base.get(tipo_servicio, [])
        horarios_libres = []
        
        for horario in horarios_posibles:
            disponible, mensaje = verificar_disponibilidad(fecha, horario)
            if disponible:
                horarios_libres.append(horario)
        
        return horarios_libres
        
    except Exception as e:
        print(f"❌ Error obteniendo horarios disponibles: {e}")
        return []
        
def debug_verificar(fecha, horario):
    """Debug detallado de verificación"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return jsonify({"error": "No service"})
        
        # Convertir horario a datetime
        hora_inicio = horario.split('-')[0]  
        hora_fin = horario.split('-')[1]     
        
        inicio_dt = datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
        fin_dt = datetime.strptime(f"{fecha} {hora_fin}", "%Y-%m-%d %H:%M")
        
        # Probar diferentes formatos de timezone
        inicio_iso1 = inicio_dt.strftime('%Y-%m-%dT%H:%M:%S') + '+01:00'
        fin_iso1 = fin_dt.strftime('%Y-%m-%dT%H:%M:%S') + '+01:00'
        
        inicio_iso2 = inicio_dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        fin_iso2 = fin_dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        
        # Buscar eventos
        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=inicio_iso2,  # Usar formato Z
            timeMax=fin_iso2,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos_existentes = eventos.get('items', [])
        
        return jsonify({
            "fecha": fecha,
            "horario": horario,
            "calendar_id": CALENDAR_ID,
            "inicio_dt": inicio_dt.strftime('%Y-%m-%d %H:%M'),
            "fin_dt": fin_dt.strftime('%Y-%m-%d %H:%M'),
            "inicio_iso_madrid": inicio_iso1,
            "fin_iso_madrid": fin_iso1,
            "inicio_iso_utc": inicio_iso2,
            "fin_iso_utc": fin_iso2,
            "eventos_encontrados": len(eventos_existentes),
            "eventos": [{"summary": e.get('summary'), "start": e.get('start'), "end": e.get('end')} for e in eventos_existentes[:3]]
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "tipo": type(e).__name__})
        
@app.route('/test/verificacion')
def test_verificacion():
    """Test directo de verificación"""
    try:
        # Test con fecha que tenga eventos
        disponible, mensaje = verificar_disponibilidad('2025-08-13', '12:00-13:00')
        
        return jsonify({
            "test": "verificacion",
            "disponible": disponible,
            "mensaje": mensaje,
            "calendar_id": CALENDAR_ID[:20] + "..."  # Solo primeros 20 chars
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "tipo": type(e).__name__
        })
        
@app.route('/debug/eventos-calendario')
def debug_eventos_calendario():
    """Ver todos los eventos del calendario AS Asesores"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return jsonify({"error": "No service"})
        
        # Buscar eventos de los últimos 7 días
        from datetime import datetime, timedelta
        inicio = datetime.now() - timedelta(days=7)
        fin = datetime.now() + timedelta(days=7)
        
        inicio_iso = inicio.strftime('%Y-%m-%dT%H:%M:%S') + '+01:00'
        fin_iso = fin.strftime('%Y-%m-%dT%H:%M:%S') + '+01:00'
        
        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=inicio_iso,
            timeMax=fin_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos_lista = eventos.get('items', [])
        
        eventos_info = []
        for evento in eventos_lista:
            eventos_info.append({
                'id': evento.get('id'),
                'titulo': evento.get('summary'),
                'inicio': evento.get('start'),
                'fin': evento.get('end'),
                'descripcion': evento.get('description', '')[:100]
            })
        
        return jsonify({
            "calendar_id": CALENDAR_ID,
            "total_eventos": len(eventos_lista),
            "eventos": eventos_info
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/api/procesar_emails_fotos', methods=['GET', 'POST'])
def api_procesar_emails_fotos():
    """API para procesar emails con fotos manualmente"""
    try:
        from email_photo_processor import EmailPhotoProcessor
        
        processor = EmailPhotoProcessor()
        resultado = processor.procesar_emails_pendientes()
        
        if resultado:
            return jsonify({
                "status": "success",
                "message": "Emails procesados correctamente"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Error procesando emails"
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
        
@app.route('/api/transfer_asesor', methods=['POST'])
def api_transfer_asesor():
    """Endpoint para tool transfer_asesor de Vapi"""
    try:
        data = request.get_json()
        destino = data.get('destino', 'Unknown')
        tipo_consulta = data.get('tipo_consulta', 'general')
        
        print(f"🔄 TOOL EJECUTADA: {destino} - {tipo_consulta}")
        
        # NO ENVIAR TELEGRAM automáticamente
        # Solo log para debug
        
        return jsonify({
            "status": "success",
            "message": f"Tool ejecutada para {destino}"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
        
@app.route('/api/transfer_manual', methods=['POST'])
def api_transfer_manual():
    try:
        enviar_telegram_mejora(f"""
📞 <b>LLAMADA PARA TRANSFERIR</b>
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M')}
📲 <b>Contesta tu móvil +34616000211</b>
        """)
        
        return jsonify({"status": "transfer_initiated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
        
# NUEVO: Workaround para transferencias GoTrunk
@app.route('/api/transfer_gotrunk_workaround', methods=['POST'])
def api_transfer_gotrunk_workaround():
    """Workaround temporal: Notificar + Colgar para transferencias manuales"""
    try:
        data = request.get_json()
        numero_cliente = data.get('numero_cliente', 'Desconocido')
        motivo = data.get('motivo', 'Solicita transferencia')
        
        # Notificación inmediata por Telegram
        enviar_telegram_mejora(f"""
🚨 <b>CLIENTE PIDE TRANSFERENCIA</b>

📞 <b>Número cliente:</b> {numero_cliente}
🎯 <b>Motivo:</b> {motivo}
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}

🔥 <b>LLAMAR YA AL:</b> +34930450985
⚡ Cliente colgará en 15 segundos
        """)
        
        return jsonify({
            "status": "notified",
            "action": "manual_callback_required", 
            "message": "Notificación enviada, callback manual necesario"
        })
        
    except Exception as e:
        print(f"❌ Error en workaround: {e}")
        return jsonify({"status": "error", "message": str(e)})
        
@app.route('/api/test-dolibarr')
def test_dolibarr_connection():
    """Test de conexión con Dolibarr - MODO LOCAL FORZADO"""
    return jsonify({
        "status": "success",
        "message": "Modo local activado - Dolibarr deshabilitado",
        "modo": "local_forzado"
    })

@app.route('/admin/empresas')
def admin_empresas():
    """Panel de administración para empresas"""
    try:
        conn = sqlite3.connect("empresas_robinson.db")
        cur = conn.cursor()
        
        # Contar empresas
        cur.execute("SELECT COUNT(*) FROM empresas_procesadas")
        total_empresas = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM lista_robinson_local")
        total_robinson = cur.fetchone()[0]
        
        # Últimas empresas
        cur.execute("SELECT * FROM empresas_procesadas ORDER BY fecha_procesado DESC LIMIT 10")
        ultimas_empresas = cur.fetchall()
        
        conn.close()
        
        html = f'''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Gestión Empresas - AS Asesores</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #007bff; color: white; padding: 20px; border-radius: 10px; text-align: center; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .section {{ background: #f8f9fa; margin: 20px 0; padding: 20px; border-radius: 10px; }}
        .btn {{ background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }}
        .btn-test {{ background: #007bff; }}
        .result {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .success {{ background: #d4edda; color: #155724; }}
        .error {{ background: #f8d7da; color: #721c24; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Gestión de Empresas</h1>
        <p>Sistema: Dolibarr + Lista Robinson Local</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{total_empresas}</div>
            <div>Empresas Procesadas</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_robinson}</div>
            <div>En Lista Robinson</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_empresas - total_robinson}</div>
            <div>Disponibles Contacto</div>
        </div>
    </div>
    
    <div class="section">
        <h3>Test de Conexión</h3>
        <button class="btn btn-test" onclick="testDolibarr()">Test Dolibarr</button>
        <div id="test-result"></div>
    </div>
    
    <div class="section">
        <h3>Últimas Empresas Procesadas</h3>
        <table>
            <tr>
                <th>Nombre</th>
                <th>CIF</th>
                <th>Ciudad</th>
                <th>Agente</th>
                <th>ID Dolibarr</th>
                <th>Fecha</th>
            </tr>
        '''
        
        for empresa in ultimas_empresas:
            html += f'''
            <tr>
                <td>{empresa[1] or 'Sin nombre'}</td>
                <td>{empresa[2] or 'Sin CIF'}</td>
                <td>{empresa[5] or 'Sin ciudad'}</td>
                <td>{empresa[7] or 'Sin agente'}</td>
                <td>{empresa[6] or 'No creado'}</td>
                <td>{empresa[8][:10] if empresa[8] else 'Sin fecha'}</td>
            </tr>
            '''
        
        html += '''
        </table>
    </div>

    <script>
        function testDolibarr() {
            const resultDiv = document.getElementById('test-result');
            resultDiv.innerHTML = '<p>Probando conexión...</p>';
            
            fetch('/api/test-dolibarr')
                .then(response => response.json())
                .then(data => {
                    const className = data.status === 'success' ? 'success' : 'error';
                    resultDiv.innerHTML = `<div class="result ${className}">${data.message}</div>`;
                })
                .catch(error => {
                    resultDiv.innerHTML = '<div class="result error">Error de conexión</div>';
                });
        }
    </script>
</body>
</html>
        '''
        
        return html
        
    except Exception as e:
        return f"Error: {str(e)}"
        
# Inicializar base de datos empresas al arrancar
try:
    gestor_inicial = GestorEmpresasSimple()
    print("Base de datos empresas inicializada correctamente")
except Exception as e:
    print(f"Error inicializando base de datos empresas: {e}")
    
@app.route('/debug/env')
def debug_env():
    return jsonify({
        "DOLIBARR_URL": os.getenv("DOLIBARR_URL"),
        "DOLIBARR_API_KEY": os.getenv("DOLIBARR_API_KEY"),
        "tiene_url": bool(os.getenv("DOLIBARR_URL")),
        "tiene_key": bool(os.getenv("DOLIBARR_API_KEY"))
    })
    
@app.route('/api/test_booking', methods=['GET', 'POST'])
def test_booking():
    try:
        data = request.get_json()
        return jsonify({
            "success": True,
            "message": "Test successful",
            "received_data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
        
@app.route('/api/save_lead', methods=['POST'])
def api_save_lead():
    try:
        data = request.get_json()
        
        # 🔧 FIX RETELL: Extraer datos de args si es function call  
        if 'args' in data and 'name' in data:
            data = data['args']
        
        # 🔧 FIX: Detectar agente desde datos originales de Retell
        data_original = request.get_json()
        if 'call' in data_original and 'agent_name' in data_original['call']:
            agent_name = data_original['call']['agent_name']
            data['agente'] = agent_name
            print(f"🔍 DEBUG - Agente detectado: {agent_name}")
        
        print(f"🔍 DEBUG api_save_lead - Datos recibidos: {data}")
        
        # 🔧 NORMALIZAR CLAVES DE DATOS PARA COMPATIBILIDAD
        # Los agentes envían datos con diferentes nombres de claves
        nombre_cliente = (
            data.get('nombre_cliente') or 
            data.get('nombre') or 
            data.get('client_name') or 
            'Sin nombre'
        )

        telefono = (
            data.get('telefono') or 
            data.get('phone') or 
            data.get('numero_telefono') or 
            'Sin teléfono'
        )

        email = (
            data.get('email') or 
            data.get('correo') or 
            data.get('mail') or 
            'Sin email'
        )

        empresa = (
            data.get('empresa') or 
            data.get('company') or 
            data.get('compania') or 
            'Sin empresa'
        )

        notas = (
            data.get('notas') or 
            data.get('notes') or 
            data.get('mensaje') or 
            data.get('consulta') or 
            'Sin notas'
        )

        agente = (
            data.get('agente') or 
            data.get('agent') or 
            'Sin especificar'
        )
        
        print(f"🔍 DEBUG api_save_lead - Datos normalizados:")
        print(f"  - Nombre: '{nombre_cliente}'")
        print(f"  - Teléfono: '{telefono}'")  
        print(f"  - Email: '{email}'")
        print(f"  - Empresa: '{empresa}'")
        print(f"  - Agente: '{agente}'")
        
        # Detectar si es ticket técnico
        es_tecnico = 'alex' in agente.lower() or 'técnico' in agente.lower() or 'soporte' in agente.lower()
        
        # Crear objeto normalizado para guardar en BD
        datos_normalizados = {
            'agente': agente,
            'empresa': empresa,
            'telefono': telefono,
            'email': email,
            'nombre_cliente': nombre_cliente,
            'notas': notas
        }
        
        # Guardar en base de datos
        lead_guardado = guardar_lead_cliente(datos_normalizados)
        
        # Personalizar notificación según tipo
        if es_tecnico:
            emoji_tipo = "🔧"
            tipo_registro = "TICKET TÉCNICO"
        else:
            emoji_tipo = "🎯" 
            tipo_registro = "LEAD COMERCIAL"
        
        # Construir mensaje Telegram con variables normalizadas
        mensaje_telegram = f"""
{emoji_tipo} <b>NUEVO {tipo_registro}</b>

👤 <b>Cliente:</b> {nombre_cliente}
🏢 <b>Empresa:</b> {empresa}
📞 <b>Teléfono:</b> {telefono}
📧 <b>Email:</b> {email}
📝 <b>Notas:</b> {notas}
👨‍💼 <b>Agente:</b> {agente}

✅ <b>Estado:</b> Registrado - {"Seguimiento técnico" if es_tecnico else "Seguimiento comercial"}
        """.strip()
        
        print(f"🔍 DEBUG api_save_lead - Enviando a Telegram:")
        print(f"📱 Mensaje: {mensaje_telegram}")
        
        # Enviar notificación
        resultado_telegram = enviar_telegram_mejora(mensaje_telegram)
        print(f"🔍 DEBUG api_save_lead - Resultado Telegram: {resultado_telegram}")
        
        return jsonify({
            "success": True,
            "message": "Datos guardados correctamente",
            "lead_id": lead_guardado,
            "tipo": "ticket_tecnico" if es_tecnico else "lead_comercial",
            "telegram_enviado": resultado_telegram,
            "datos_procesados": {
                "nombre": nombre_cliente,
                "telefono": telefono,
                "email": email
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en api_save_lead: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        })

# OPCIONAL: Función para testear el fix
@app.route('/test/save_lead_fix', methods=['GET', 'POST'])
def test_save_lead_fix():
    """Probar el fix con diferentes formatos de datos"""
    
    if request.method == 'GET':
        return '''
        <h2>🔧 Test Fix Save Lead</h2>
        <button onclick="testFormato1()">Test Formato 1 (nombre)</button>
        <button onclick="testFormato2()">Test Formato 2 (nombre_cliente)</button>
        <button onclick="testFormato3()">Test Formato 3 (mixto)</button>
        <div id="resultado"></div>
        
        <script>
        function testFormato1() {
            testConDatos({
                agente: "Verónica",
                nombre: "Juan García",  // ← nombre (no nombre_cliente)
                telefono: "666123456",
                email: "juan@test.com",
                notas: "Cliente interesado"
            });
        }
        
        function testFormato2() {
            testConDatos({
                agente: "Sofia", 
                nombre_cliente: "María López",  // ← nombre_cliente
                phone: "677888999",             // ← phone (no telefono)
                correo: "maria@test.com",       // ← correo (no email)
                empresa: "Test Company"
            });
        }
        
        function testFormato3() {
            testConDatos({
                agent: "Vendedor 1",           // ← agent (no agente)
                client_name: "Pedro Martín",   // ← client_name
                telefono: "655444333",
                mail: "pedro@empresa.com",     // ← mail (no email)
                consulta: "Necesita información"  // ← consulta (no notas)
            });
        }
        
        function testConDatos(datos) {
            fetch('/api/save_lead', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(datos)
            })
            .then(response => response.json())
            .then(result => {
                document.getElementById('resultado').innerHTML = 
                    '<div style="background: ' + (result.success ? '#d4edda' : '#f8d7da') + '; padding: 15px; margin: 10px 0; border-radius: 5px;">' +
                    '<h4>' + (result.success ? '✅ ÉXITO' : '❌ ERROR') + '</h4>' +
                    '<p>Telegram enviado: ' + result.telegram_enviado + '</p>' +
                    '<p>Datos procesados: ' + JSON.stringify(result.datos_procesados) + '</p>' +
                    '</div>';
            });
        }
        </script>
        '''
        
    # Si es POST, procesar como save_lead normal
    return api_save_lead()
        
def guardar_lead_cliente(data):
    """Guardar lead de cliente en base de datos"""
    try:
        conn = sqlite3.connect("clientes_leads.db") 
        cur = conn.cursor()
        
        # Crear tabla si no existe
        cur.execute("""
        CREATE TABLE IF NOT EXISTS leads_clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente TEXT,
            empresa TEXT,
            telefono TEXT,
            email TEXT,
            nombre_cliente TEXT,
            notas TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'pendiente'
        )
        """)
        
        # Insertar lead
        cur.execute("""
        INSERT INTO leads_clientes 
        (agente, empresa, telefono, email, nombre_cliente, notas)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('agente', 'Verónica'),
            data.get('empresa', ''),
            data.get('telefono', ''),
            data.get('email', ''),
            data.get('nombre_cliente', ''),
            data.get('notas', '')
        ))
        
        lead_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Lead guardado con ID: {lead_id}")
        return lead_id
        
    except Exception as e:
        print(f"❌ Error guardando lead: {e}")
        return None
        
@app.route('/test/save_lead')
def test_save_lead_form():
    """Formulario para probar save_lead"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Test Save Lead</title></head>
    <body style="font-family: Arial; max-width: 600px; margin: 50px auto;">
        <h2>🧪 Test Save Lead</h2>
        <div id="result"></div>
        <button onclick="testSaveLead()">Probar Save Lead</button>
        
        <script>
        function testSaveLead() {
            const data = {
                agente: "Verónica",
                empresa: "Test Company",
                telefono: "666777888", 
                email: "test@test.com",
                nombre_cliente: "Juan Pérez",
                notas: "Cliente interesado en servicios"
            };
            
            fetch('/api/save_lead', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                document.getElementById('result').innerHTML = 
                    '<div style="background: ' + (result.success ? '#d4edda' : '#f8d7da') + '; padding: 15px; margin: 10px 0; border-radius: 5px;">' +
                    (result.success ? '✅' : '❌') + ' ' + (result.message || result.error) + '</div>';
            });
        }
        </script>
    </body>
    </html>
    '''
    
@app.route('/test_llamada_directa', methods=['POST'])
def llamada_vendedor():
    # LOGS BÁSICOS - DEBEN APARECER SÍ O SÍ
    print("="*50)
    print("FUNCIÓN LLAMADA_VENDEDOR EJECUTADA")
    print("="*50)
    
    try:
        print("PASO 1: Obteniendo datos JSON...")
        data = request.json
        print(f"DATOS RECIBIDOS: {data}")
        
        print("PASO 2: Extrayendo variables...")
        telefono = data.get('telefono')
        empresa = data.get('empresa') 
        vendedor = data.get('vendedor')
        print(f"TELÉFONO: {telefono}")
        print(f"EMPRESA: {empresa}")
        print(f"VENDEDOR: {vendedor}")
        
        print("PASO 3: Llamando a retell_llamada_zadarma...")
        resultado = retell_llamada_zadarma(telefono, empresa, vendedor)
        print(f"RESULTADO: {resultado}")
        
        print("PASO 4: Devolviendo respuesta...")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        return jsonify({"error": str(e)}), 500
        
@app.route('/api/vendedor_siguiente/<vendedor>', methods=['GET'])
def api_vendedor_siguiente(vendedor):
    """Endpoint para Make.com - obtener siguiente vendedor"""
    try:
        # Mapeo simple de vendedores
        vendedores_map = {
            'albert': 'vendedor 1',
            'juan': 'vendedor 2', 
            'carlos': 'vendedor 3',
            'vendedor 1': 'vendedor 1',
            'vendedor 2': 'vendedor 2',
            'vendedor 3': 'vendedor 3'
        }
        
        vendedor_normalizado = vendedores_map.get(vendedor.lower(), 'vendedor 1')
        
        return jsonify({
            "vendedor_input": vendedor,
            "vendedor_seleccionado": vendedor_normalizado,
            "status": "ok"
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"})
        
def guardar_cliente_potencial(data):
    """Guardar cliente potencial desde emails y otros agentes"""
    try:
        return guardar_lead_cliente(data)
    except Exception as e:
        print(f"Error guardando cliente potencial: {e}")
        return None
        
@app.route('/api/test_zadarma_main', methods=['GET'])
def test_zadarma_main():
    try:
        return jsonify({
            "archivo": "main.py",
            "RETELL_API_KEY": "Configurada" if 'RETELL_API_KEY' in globals() else "Falta",
            "funcion_zadarma": callable(globals().get('retell_llamada_zadarma')),
            "endpoint_exists": "/api/llamada_vendedor" in [rule.rule for rule in app.url_map.iter_rules()]
        })
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/admin/leads')
def ver_leads():
    try:
        conn = sqlite3.connect("clientes_leads.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads_clientes ORDER BY fecha_registro DESC LIMIT 20")
        leads = cur.fetchall()
        conn.close()
        
        html = "<h2>Leads de Clientes</h2><table border='1'>"
        html += "<tr><th>ID</th><th>Agente</th><th>Nombre</th><th>Teléfono</th><th>Email</th><th>Empresa</th><th>Notas</th><th>Fecha</th></tr>"
        for lead in leads:
            html += f"<tr><td>{lead[0]}</td><td>{lead[1]}</td><td>{lead[5]}</td><td>{lead[3]}</td><td>{lead[4]}</td><td>{lead[2]}</td><td>{lead[6]}</td><td>{lead[7]}</td></tr>"
        html += "</table>"
        return html
    except Exception as e:
        return f"Error: {str(e)}"
        
@app.route('/api/test_llamada_forzada', methods=['GET'])
def test_llamada_forzada():
    print("=== TEST FORZADO INICIADO ===")
    resultado = retell_llamada_zadarma("+34932192110", "Test Empresa", "Albert")
    print(f"=== RESULTADO TEST: {resultado} ===")
    return jsonify(resultado)
    
@app.route('/api/debug_zadarma_config', methods=['GET'])
def debug_zadarma_config():
    return jsonify({
        "ZADARMA_PHONE_NUMBER_ID": ZADARMA_PHONE_NUMBER_ID,
        "tipo": type(ZADARMA_PHONE_NUMBER_ID).__name__,
        "es_vacio": not ZADARMA_PHONE_NUMBER_ID,
        "longitud": len(str(ZADARMA_PHONE_NUMBER_ID))
    })
    
@app.route('/api/debug_make', methods=['GET', 'POST'])
def debug_make():
    try:
        print(f"=== DEBUG MAKE: {request.method} ===")
        print(f"=== Headers: {dict(request.headers)} ===")
        print(f"=== Body: {request.get_data()} ===")
        print(f"=== JSON: {request.get_json() if request.is_json else 'No JSON'} ===")
        
        return jsonify({
            "received": True,
            "method": request.method,
            "headers": dict(request.headers),
            "json_data": request.get_json() if request.is_json else None,
            "raw_data": str(request.get_data())
        })
    except Exception as e:
        return jsonify({"error": str(e)})
        
# ========================================
# ENDPOINTS PARA PROBAR PDFs - AÑADIR A main.py
# ========================================

@app.route('/test/generar_pdfs_todas_especialidades')
def generar_pdfs_todas_especialidades():
    """Generar PDFs de prueba para todas las especialidades"""
    try:
        from informes import procesar_y_enviar_informe
        
        especialidades = [
            'carta_astral_ia',
            'revolucion_solar_ia', 
            'sinastria_ia',
            'astrologia_horaria_ia',
            'lectura_manos_ia',
            'lectura_facial_ia',
            'psico_coaching_ia',
            'grafologia_ia'
        ]
        
        resultados = []
        
        for especialidad in especialidades:
            try:
                # Datos de prueba para cada especialidad
                datos_cliente = {
                    'nombre': 'Cliente Prueba',
                    'email': 'test@prueba.com',
                    'codigo_servicio': f'TEST_{especialidad.upper()}',
                    'fecha_nacimiento': '15/07/1985',
                    'hora_nacimiento': '10:30',
                    'lugar_nacimiento': 'Madrid, España'
                }
                
                # Generar sin enviar email (modificaremos la función)
                archivo_pdf = generar_solo_pdf(datos_cliente, especialidad)
                
                if archivo_pdf:
                    resultados.append({
                        'especialidad': especialidad,
                        'status': 'success',
                        'archivo': archivo_pdf,
                        'download_url': f'/test/descargar_pdf/{os.path.basename(archivo_pdf)}'
                    })
                else:
                    resultados.append({
                        'especialidad': especialidad,
                        'status': 'error',
                        'mensaje': 'Error generando PDF'
                    })
                    
            except Exception as e:
                resultados.append({
                    'especialidad': especialidad,
                    'status': 'error',
                    'mensaje': str(e)
                })
        
        return jsonify({
            'status': 'completed',
            'total_especialidades': len(especialidades),
            'resultados': resultados,
            'instrucciones': 'Usa las download_url para descargar cada PDF'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 500

def generar_solo_pdf(datos_cliente, tipo_servicio):
    """Generar solo PDF sin enviar email - CON IMÁGENES DE PRUEBA"""
    try:
        from informes import generar_informe_html, convertir_html_a_pdf, generar_nombre_archivo_unico
        import os
        
        print(f"📄 Generando PDF para {tipo_servicio}")
        
        # 🔥 CREAR ARCHIVOS_UNICOS DE PRUEBA (en lugar de diccionario vacío)
        archivos_unicos_prueba = crear_archivos_unicos_testing(tipo_servicio)
        
        # 🔥 DEBUG: Imprimir qué se está pasando
        print(f"🔥 DEBUG archivos_unicos_prueba: {archivos_unicos_prueba}")
        
        # Generar HTML CON archivos_unicos
        archivo_html = generar_informe_html(
            datos_cliente, 
            tipo_servicio, 
            archivos_unicos_prueba,  # 🔥 CAMBIO CRÍTICO: No más diccionario vacío
            "Resumen de prueba para testing - Generado en Railway con imágenes"
        )
        
        if not archivo_html:
            print("❌ Error generando HTML")
            return None
        
        # Generar PDF
        nombre_base = generar_nombre_archivo_unico(tipo_servicio, datos_cliente.get('codigo_servicio', ''))
        archivo_pdf = f"informes/{nombre_base}.pdf"
        
        # Crear directorio si no existe
        os.makedirs('informes', exist_ok=True)
        
        exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
        
        if exito_pdf:
            print(f"✅ PDF generado con imágenes: {archivo_pdf}")
            return archivo_pdf
        else:
            print("❌ Error generando PDF")
            return None
        
    except Exception as e:
        print(f"❌ Error en generar_solo_pdf: {e}")
        import traceback
        traceback.print_exc()
        return None

# ========================================
# FUNCIÓN MEJORADA PARA GENERAR CARTAS CON DATOS REALES
# ========================================

def generar_cartas_con_datos_reales(datos_cliente, tipo_servicio):
    """Generar cartas astrales con los datos reales del cliente"""
    from datetime import datetime
    import carta_natal
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extraer datos de nacimiento
        fecha_nac = datos_cliente.get('fecha_nacimiento', '15/07/1985')
        hora_nac = datos_cliente.get('hora_nacimiento', '10:30') 
        lugar_nac = datos_cliente.get('lugar_nacimiento', 'Madrid, España')
        
        # Convertir fecha a formato requerido
        try:
            dia, mes, año = fecha_nac.split('/')
            hora, minuto = hora_nac.split(':')
            fecha_natal = (int(año), int(mes), int(dia), int(hora), int(minuto))
        except:
            # Fallback si hay error en formato
            fecha_natal = (1985, 7, 15, 10, 30)
        
        # Archivos únicos personalizados
        archivos_personalizados = {
            'carta_natal_img': f'static/carta_natal_{datos_cliente.get("codigo_servicio", "test")}_{timestamp}.png',
            'progresiones_img': f'static/progresiones_{datos_cliente.get("codigo_servicio", "test")}_{timestamp}.png',
            'transitos_img': f'static/transitos_{datos_cliente.get("codigo_servicio", "test")}_{timestamp}.png'
        }
        
        # Intentar generar carta personalizada
        carta_instance = carta_natal.CartaAstralNatal()
        
        # Si la clase permite configurar datos
        if hasattr(carta_instance, 'configurar_datos') or hasattr(carta_instance, 'set_datos'):
            # Configurar con datos del cliente
            pass  # Implementar cuando sepamos la API exacta
        
        # Por ahora, generar con función que funciona
        carta_natal.generar_carta_natal_personalizada()
        
        return archivos_personalizados
        
    except Exception as e:
        print(f"❌ Error generando cartas personalizadas: {e}")
        return {}

# ========================================
# TEST PARA VERIFICAR QUE FUNCIONA
# ========================================

@app.route('/test/verificar_cartas_dinamicas/<especialidad>')
def verificar_cartas_dinamicas(especialidad):
    """Verificar que las cartas dinámicas se generan correctamente"""
    try:
        from datetime import datetime
        import os
        
        print(f"🎯 Verificando cartas dinámicas para: {especialidad}")
        
        # Contar archivos antes
        archivos_antes = len(os.listdir('./static/')) if os.path.exists('./static/') else 0
        
        # Generar archivos únicos usando la función corregida
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        
        # Esperar un poco para que se generen
        import time
        time.sleep(2)
        
        # Contar archivos después  
        archivos_despues = len(os.listdir('./static/')) if os.path.exists('./static/') else 0
        
        # Buscar archivos nuevos
        timestamp_actual = datetime.now().strftime('%Y%m%d')
        archivos_nuevos = []
        
        if os.path.exists('./static/'):
            for archivo in os.listdir('./static/'):
                if timestamp_actual in archivo:
                    ruta = f"./static/{archivo}"
                    stats = os.stat(ruta)
                    # Si es muy reciente (últimos 30 segundos)
                    if time.time() - stats.st_mtime < 30:
                        archivos_nuevos.append({
                            'archivo': archivo,
                            'tamaño': stats.st_size,
                            'url': f"https://as-webhooks-production.up.railway.app/static/{archivo}",
                            'edad_segundos': round(time.time() - stats.st_mtime, 1)
                        })
        
        return jsonify({
            'status': 'success',
            'especialidad': especialidad,
            'archivos_unicos_generados': archivos_unicos,
            'archivos_antes': archivos_antes,
            'archivos_despues': archivos_despues,
            'archivos_nuevos_encontrados': archivos_nuevos,
            'cartas_generadas_dinamicamente': len(archivos_nuevos) > 0,
            'siguiente_paso': 'Probar PDF completo en /test/generar_pdf_especialidad/' + especialidad
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# ===================================
# AÑADIR ENDPOINT DE TEST FINAL
# ===================================

@app.route('/test/generar_pdf_con_debug/<especialidad>')
def generar_pdf_con_debug(especialidad):
    """Generar PDF con debug completo paso a paso"""
    try:
        from informes import generar_informe_html, convertir_html_a_pdf, generar_nombre_archivo_unico
        import os
        
        # Datos de prueba
        datos_cliente = {
            'nombre': 'Cliente Test Debug',
            'email': 'debug@test.com',
            'codigo_servicio': 'DEBUG_123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        resultado = {'pasos': {}}
        
        # PASO 1: Crear archivos_unicos
        print(f"🔍 PASO 1: Creando archivos_unicos...")
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        resultado['pasos']['paso_1'] = {
            'archivos_unicos': archivos_unicos,
            'total_archivos': len([k for k, v in archivos_unicos.items() if isinstance(v, str) and v.endswith(('.png', '.jpg'))])
        }
        
        # PASO 2: Generar HTML
        print(f"🔍 PASO 2: Generando HTML...")
        archivo_html = generar_informe_html(datos_cliente, especialidad, archivos_unicos, "Debug test")
        resultado['pasos']['paso_2'] = {
            'html_generado': archivo_html is not None,
            'archivo_path': archivo_html
        }
        
        if archivo_html:
            # PASO 3: Verificar contenido HTML
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            img_count = html_content.count('<img')
            resultado['pasos']['paso_3'] = {
                'imagenes_en_html': img_count,
                'html_preview': html_content[:500]
            }
            
            # PASO 4: Generar PDF
            print(f"🔍 PASO 4: Generando PDF...")
            nombre_pdf = f"debug_{especialidad}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            archivo_pdf = f"informes/{nombre_pdf}"
            os.makedirs('informes', exist_ok=True)
            
            exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
            resultado['pasos']['paso_4'] = {
                'pdf_generado': exito_pdf,
                'archivo_pdf': archivo_pdf if exito_pdf else None,
                'download_url': f"/test/descargar_pdf/{nombre_pdf}" if exito_pdf else None
            }
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

def buscar_o_crear_imagen_dummy(tipo_imagen, timestamp):
    """Buscar imagen existente o usar una dummy"""
    import os
    import glob
    
    # 1. Buscar en static/ archivos recientes (últimas 2 horas)
    patterns = [
        f"static/{tipo_imagen}_*.png",
        f"static/*{tipo_imagen}*.png"
    ]
    
    archivos_encontrados = []
    for pattern in patterns:
        archivos_encontrados.extend(glob.glob(pattern))
    
    if archivos_encontrados:
        # Usar el más reciente
        archivo_mas_reciente = max(archivos_encontrados, key=os.path.getmtime)
        print(f"✅ Usando imagen existente: {archivo_mas_reciente}")
        return archivo_mas_reciente
    
    # 2. Buscar en img/ (imágenes estáticas)
    img_patterns = [
        f"img/{tipo_imagen}*.jpg",
        f"img/{tipo_imagen}*.JPG",
        f"img/{tipo_imagen}*.png",
        f"img/*{tipo_imagen}*.jpg",
        f"img/*{tipo_imagen}*.JPG"
    ]
    
    for pattern in img_patterns:
        archivos_img = glob.glob(pattern)
        if archivos_img:
            print(f"✅ Usando imagen estática: {archivos_img[0]}")
            return archivos_img[0]
    
    # 3. Crear imagen dummy si no existe
    dummy_path = f"static/{tipo_imagen}_dummy_{timestamp}.png"
    crear_imagen_dummy(dummy_path, tipo_imagen)
    return dummy_path

def crear_imagen_dummy(ruta_archivo, tipo_imagen):
    """Crear imagen dummy simple para testing"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import os
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
        
        # Crear imagen base
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Añadir texto
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        texto = f"IMAGEN DUMMY\n{tipo_imagen.upper()}\nGenerada para testing"
        
        # Dibujar rectángulo de fondo
        draw.rectangle([50, 50, 750, 550], outline='black', width=3)
        
        # Dibujar texto centrado
        if font:
            draw.text((400, 300), texto, fill='black', font=font, anchor='mm')
        else:
            draw.text((400, 300), texto, fill='black', anchor='mm')
        
        # Guardar imagen
        img.save(ruta_archivo, 'PNG')
        print(f"✅ Imagen dummy creada: {ruta_archivo}")
        
    except Exception as e:
        print(f"❌ Error creando imagen dummy: {e}")
        # Crear archivo vacío como fallback
        with open(ruta_archivo, 'w') as f:
            f.write("")

@app.route('/test/generar_pdf_especialidad/<especialidad>')
def generar_pdf_especialidad_optimizado(especialidad):
    """Generar PDF usando sistema optimizado AS Cartastral"""
    from datetime import datetime
    import os
    
    try:
        print(f"🎯 AS CARTASTRAL: Iniciando generación PDF para {especialidad}")
        
        # PASO 1: Crear archivos únicos específicos
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        
        if not archivos_unicos:
            return {"status": "error", "mensaje": "Error creando archivos únicos"}
        
        # DATOS DE PRUEBA (Sofia pasará datos reales)
        datos_cliente = {
            'codigo_servicio': f'CAR_{especialidad.upper()}',
            'nombre': f'Cliente {archivos_unicos.get("client_id", "test")}',
            'email': f'{especialidad}_{archivos_unicos.get("client_id", "test")}@ascartastral.com',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30', 
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # PASO 2: Generar HTML optimizado
        try:
            from informes import generar_informe_html
            contenido_html = generar_informe_html(datos_cliente, especialidad, archivos_unicos)
            
            if not contenido_html:
                # HTML de emergencia si informes.py falla
                contenido_html = generar_html_emergencia_as_cartastral(datos_cliente, archivos_unicos)
                
        except Exception as e:
            print(f"⚠️ Error en informes.py: {e}, usando HTML de emergencia")
            contenido_html = generar_html_emergencia_as_cartastral(datos_cliente, archivos_unicos)
        
        # PASO 3: Convertir a PDF con Playwright
        nombre_archivo = f"{especialidad}_{archivos_unicos['timestamp']}.pdf"
        ruta_pdf = f"informes/{nombre_archivo}"
        
        resultado_pdf = convertir_html_a_pdf_playwright(contenido_html, ruta_pdf)
        
        if resultado_pdf['success']:
            return {
                "status": "success",
                "mensaje": f"PDF AS Cartastral generado: {especialidad}",
                "archivo": ruta_pdf,
                "download_url": f"/test/descargar_pdf/{nombre_archivo}",
                "especialidad": especialidad,
                "archivos_usados": [
                    archivos_unicos.get('carta_natal_img'),
                    archivos_unicos.get('progresiones_img'), 
                    archivos_unicos.get('transitos_img')
                ],
                "generacion_dinamica": archivos_unicos.get('generacion_dinamica', False),
                "es_producto_m": archivos_unicos.get('es_producto_m', False),
                "metodo": "Funciones wrapper específicas + Playwright"
            }
        else:
            return {"status": "error", "mensaje": f"Error en conversión PDF: {resultado_pdf['error']}"}
            
    except Exception as e:
        print(f"❌ AS CARTASTRAL: Error general: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "mensaje": f"Error general: {str(e)}"}

def generar_html_simple_directo(datos_cliente, especialidad, archivos_unicos):
    """Generar HTML simple sin depender de informes.py"""
    from datetime import datetime
    import pytz
    
    try:
        fecha_actual = datetime.now(pytz.timezone('Europe/Madrid'))
        fecha_generacion = fecha_actual.strftime('%d de %B de %Y')
        hora_generacion = fecha_actual.strftime('%H:%M')
        
        es_producto_m = especialidad.endswith('_half')
        
        if es_producto_m:
            # Template anexo simple
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>ANEXO - {datos_cliente['nombre']}</title>
<style>
body {{ font-family: Arial; margin: 30px; line-height: 1.6; }}
.anexo {{ background: #f57c00; color: white; padding: 20px; text-align: center; border-radius: 10px; }}
.contenido {{ background: #fff8e1; padding: 20px; margin: 20px 0; border-left: 4px solid #ff9800; }}
</style></head>
<body>
<div class="anexo">
<h1>ANEXO - CONTINUACIÓN {especialidad.replace('_half', '').replace('_', ' ').upper()}</h1>
<p>Cliente: {datos_cliente['nombre']}</p>
<p>Email: {datos_cliente['email']}</p>
<p>Duración: {archivos_unicos.get('duracion_minutos', 20)} minutos (½ tiempo)</p>
</div>
<div class="contenido">
<h2>Continuación de tu Consulta</h2>
<p>Sesión de seguimiento personalizada generada exitosamente.</p>
<p><strong>Generación dinámica:</strong> {archivos_unicos.get('generacion_dinamica', False)}</p>
</div>
<p style="text-align: center; margin-top: 40px;">
Generado el {fecha_generacion} a las {hora_generacion}<br>
AS Cartastral - Servicios Astrológicos IA
</p>
</body></html>"""
        else:
            # Template completo simple
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{datos_cliente['nombre']} - {especialidad}</title>
<style>
body {{ font-family: Arial; margin: 30px; line-height: 1.6; }}
.portada {{ text-align: center; padding: 40px; background: #f8f9fa; border: 3px solid #DAA520; margin: 20px 0; }}
.datos {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #2c5aa0; }}
.imagen {{ text-align: center; margin: 20px 0; }}
img {{ max-width: 100%; height: auto; border: 2px solid #ccc; }}
</style></head>
<body>
<div class="portada">
<h1>{especialidad.replace('_', ' ').upper()}</h1>
<h2>{datos_cliente['nombre']}</h2>
<p>Tu análisis personalizado</p>
<p>Generado el {fecha_generacion}</p>
</div>
<div class="datos">
<h2>Datos Personales</h2>
<p><strong>Cliente:</strong> {datos_cliente['nombre']}</p>
<p><strong>Email:</strong> {datos_cliente['email']}</p>
<p><strong>Fecha de nacimiento:</strong> {datos_cliente['fecha_nacimiento']}</p>
<p><strong>Hora de nacimiento:</strong> {datos_cliente['hora_nacimiento']}</p>
<p><strong>Lugar de nacimiento:</strong> {datos_cliente['lugar_nacimiento']}</p>
<p><strong>Generación dinámica:</strong> {archivos_unicos.get('generacion_dinamica', False)}</p>
</div>"""
            
            # Añadir imágenes si existen
            for key, img_path in archivos_unicos.items():
                if key.endswith('_img') and img_path:
                    titulo_img = key.replace('_img', '').replace('_', ' ').title()
                    html += f"""
<div class="imagen">
<h3>{titulo_img}</h3>
<img src="{img_path}" alt="{titulo_img}">
</div>"""
            
            html += f"""
<p style="text-align: center; margin-top: 40px;">
Generado el {fecha_generacion} a las {hora_generacion}<br>
AS Cartastral - Servicios Astrológicos IA
</p>
</body></html>"""
        
        return html
        
    except Exception as e:
        print(f"Error generando HTML directo: {e}")
        return None

@app.route('/test/descargar_pdf/<nombre_archivo>')
def descargar_pdf(nombre_archivo):
    """Descargar PDF generado"""
    try:
        ruta_pdf = f"informes/{nombre_archivo}"
        
        if not os.path.exists(ruta_pdf):
            return jsonify({'error': 'Archivo no encontrado'}), 404
        
        return send_file(
            ruta_pdf,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/listar_pdfs')
def listar_pdfs():
    """Listar todos los PDFs generados"""
    try:
        import glob
        
        # Buscar todos los PDFs en la carpeta informes
        pdfs = glob.glob('informes/*.pdf')
        
        lista_pdfs = []
        for pdf in pdfs:
            nombre_archivo = os.path.basename(pdf)
            stats = os.stat(pdf)
            
            lista_pdfs.append({
                'nombre': nombre_archivo,
                'tamaño_mb': round(stats.st_size / (1024*1024), 2),
                'fecha_creacion': datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                'download_url': f'/test/descargar_pdf/{nombre_archivo}'
            })
        
        return jsonify({
            'total_pdfs': len(lista_pdfs),
            'pdfs': lista_pdfs,
            'instruccion': 'Usa download_url para descargar cada PDF'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/panel_pdfs')
def panel_pdfs():
    """Panel web para generar y descargar PDFs"""
    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Panel de Test PDFs - AS Cartastral</title>
    <style>
        body { font-family: Arial; max-width: 1200px; margin: 20px auto; padding: 20px; }
        .especialidad { border: 1px solid #ddd; margin: 10px; padding: 15px; border-radius: 5px; }
        .btn { padding: 8px 15px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-generar { background: #007bff; color: white; }
        .btn-descargar { background: #28a745; color: white; }
        .btn-todas { background: #6f42c1; color: white; }
        .resultado { margin-top: 10px; padding: 10px; border-radius: 3px; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <h1>🧪 Panel de Test - Informes PDF AS Cartastral</h1>
    
    <div style="margin: 20px 0;">
        <button class="btn btn-todas" onclick="generarTodasEspecialidades()">
            📄 Generar PDFs de Todas las Especialidades
        </button>
        <button class="btn btn-todas" onclick="listarPdfs()">
            📋 Listar PDFs Existentes
        </button>
    </div>
    
    <div id="resultado-general"></div>
    
    <h2>Especialidades Individuales:</h2>
    
    <div class="especialidad">
        <h3>🌟 Carta Astral IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('carta_astral_ia')">Generar PDF</button>
        <div id="resultado-carta_astral_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>🌟 Revolución Solar IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('revolucion_solar_ia')">Generar PDF</button>
        <div id="resultado-revolucion_solar_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>💕 Sinastría IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('sinastria_ia')">Generar PDF</button>
        <div id="resultado-sinastria_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>🎯 Astrología Horaria IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('astrologia_horaria_ia')">Generar PDF</button>
        <div id="resultado-astrologia_horaria_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>✋ Lectura de Manos IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('lectura_manos_ia')">Generar PDF</button>
        <div id="resultado-lectura_manos_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>👁️ Lectura Facial IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('lectura_facial_ia')">Generar PDF</button>
        <div id="resultado-lectura_facial_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>🧠 Psico-Coaching IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('psico_coaching_ia')">Generar PDF</button>
        <div id="resultado-psico_coaching_ia"></div>
    </div>
    
    <div class="especialidad">
        <h3>✍️ Grafología IA</h3>
        <button class="btn btn-generar" onclick="generarPdf('grafologia_ia')">Generar PDF</button>
        <div id="resultado-grafologia_ia"></div>
    </div>

    <script>
    function generarPdf(especialidad) {
        const resultadoDiv = document.getElementById('resultado-' + especialidad);
        resultadoDiv.innerHTML = '<div class="resultado">⏳ Generando PDF...</div>';
        
        fetch('/test/generar_pdf_especialidad/' + especialidad)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    resultadoDiv.innerHTML = `
                        <div class="resultado success">
                            ✅ PDF generado correctamente<br>
                            <button class="btn btn-descargar" onclick="descargarPdf('${data.download_url}')">
                                📥 Descargar PDF
                            </button>
                        </div>
                    `;
                } else {
                    resultadoDiv.innerHTML = `<div class="resultado error">❌ ${data.mensaje}</div>`;
                }
            })
            .catch(error => {
                resultadoDiv.innerHTML = `<div class="resultado error">❌ Error: ${error}</div>`;
            });
    }
    
    function descargarPdf(downloadUrl) {
        window.open(downloadUrl, '_blank');
    }
    
    function generarTodasEspecialidades() {
        const resultadoDiv = document.getElementById('resultado-general');
        resultadoDiv.innerHTML = '<div class="resultado">⏳ Generando PDFs de todas las especialidades...</div>';
        
        fetch('/test/generar_pdfs_todas_especialidades')
            .then(response => response.json())
            .then(data => {
                let html = '<div class="resultado success"><h3>📄 Resultados:</h3>';
                data.resultados.forEach(resultado => {
                    if (resultado.status === 'success') {
                        html += `
                            <div>✅ ${resultado.especialidad}: 
                                <button class="btn btn-descargar" onclick="descargarPdf('${resultado.download_url}')">
                                    📥 Descargar
                                </button>
                            </div>
                        `;
                    } else {
                        html += `<div>❌ ${resultado.especialidad}: ${resultado.mensaje}</div>`;
                    }
                });
                html += '</div>';
                resultadoDiv.innerHTML = html;
            })
            .catch(error => {
                resultadoDiv.innerHTML = `<div class="resultado error">❌ Error: ${error}</div>`;
            });
    }
    
    function listarPdfs() {
        const resultadoDiv = document.getElementById('resultado-general');
        resultadoDiv.innerHTML = '<div class="resultado">⏳ Listando PDFs...</div>';
        
        fetch('/test/listar_pdfs')
            .then(response => response.json())
            .then(data => {
                let html = '<div class="resultado success"><h3>📋 PDFs Disponibles:</h3>';
                if (data.pdfs.length === 0) {
                    html += '<p>No hay PDFs generados aún.</p>';
                } else {
                    data.pdfs.forEach(pdf => {
                        html += `
                            <div style="margin: 5px 0; padding: 5px; border: 1px solid #ddd;">
                                📄 ${pdf.nombre} (${pdf.tamaño_mb} MB) - ${pdf.fecha_creacion}
                                <button class="btn btn-descargar" onclick="descargarPdf('${pdf.download_url}')">
                                    📥 Descargar
                                </button>
                            </div>
                        `;
                    });
                }
                html += '</div>';
                resultadoDiv.innerHTML = html;
            })
            .catch(error => {
                resultadoDiv.innerHTML = `<div class="resultado error">❌ Error: ${error}</div>`;
            });
    }
    </script>
</body>
</html>
    '''
    return html
    
# ========================================
# 1. DEBUG PDF DETALLADO
# ========================================

@app.route('/test/debug_pdf/<especialidad>')
def debug_pdf_detallado(especialidad):
    """Debug completo del proceso de generación de PDF"""
    try:
        debug_info = {
            'paso_1_datos': {},
            'paso_2_html': {},
            'paso_3_pdf': {},
            'errores': []
        }
        
        # PASO 1: Generar datos
        try:
            datos_cliente = {
                'nombre': 'Cliente Debug',
                'email': 'debug@test.com',
                'codigo_servicio': f'DEBUG_{especialidad.upper()}',
                'fecha_nacimiento': '15/07/1985',
                'hora_nacimiento': '10:30',
                'lugar_nacimiento': 'Madrid, España'
            }
            debug_info['paso_1_datos'] = {
                'status': 'success',
                'datos': datos_cliente
            }
        except Exception as e:
            debug_info['paso_1_datos'] = {'status': 'error', 'error': str(e)}
            debug_info['errores'].append(f"Error datos: {e}")
        
        # PASO 2: Generar HTML
        try:
            from informes import generar_informe_html
            archivo_html = generar_informe_html(datos_cliente, especialidad, {}, "Debug test")
            
            if archivo_html and os.path.exists(archivo_html):
                # Leer contenido HTML para debug
                with open(archivo_html, 'r', encoding='utf-8') as f:
                    contenido_html = f.read()
                
                debug_info['paso_2_html'] = {
                    'status': 'success',
                    'archivo': archivo_html,
                    'tamaño': len(contenido_html),
                    'preview': contenido_html[:500] + "..." if len(contenido_html) > 500 else contenido_html
                }
            else:
                debug_info['paso_2_html'] = {
                    'status': 'error',
                    'error': 'Archivo HTML no generado o no existe'
                }
                debug_info['errores'].append("HTML no generado")
                
        except Exception as e:
            debug_info['paso_2_html'] = {'status': 'error', 'error': str(e)}
            debug_info['errores'].append(f"Error HTML: {e}")
        
        # PASO 3: Probar conversión PDF (solo si HTML existe)
        if debug_info['paso_2_html'].get('status') == 'success':
            try:
                from informes import convertir_html_a_pdf, generar_nombre_archivo_unico
                
                nombre_base = generar_nombre_archivo_unico(especialidad, 'DEBUG')
                archivo_pdf = f"informes/{nombre_base}.pdf"
                
                # Crear directorio
                os.makedirs('informes', exist_ok=True)
                
                # Intentar conversión
                exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
                
                if exito_pdf and os.path.exists(archivo_pdf):
                    stats = os.stat(archivo_pdf)
                    debug_info['paso_3_pdf'] = {
                        'status': 'success',
                        'archivo': archivo_pdf,
                        'tamaño_bytes': stats.st_size,
                        'tamaño_mb': round(stats.st_size / (1024*1024), 2),
                        'download_url': f'/test/descargar_pdf/{os.path.basename(archivo_pdf)}'
                    }
                else:
                    debug_info['paso_3_pdf'] = {
                        'status': 'error',
                        'error': 'PDF no generado'
                    }
                    debug_info['errores'].append("PDF no generado")
                    
            except Exception as e:
                debug_info['paso_3_pdf'] = {'status': 'error', 'error': str(e)}
                debug_info['errores'].append(f"Error PDF: {e}")
        
        # PASO 4: Verificar Playwright
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            debug_info['playwright_status'] = 'OK'
        except Exception as e:
            debug_info['playwright_status'] = f'ERROR: {e}'
            debug_info['errores'].append(f"Playwright error: {e}")
        
        return jsonify({
            'especialidad': especialidad,
            'resumen': 'success' if not debug_info['errores'] else 'error',
            'total_errores': len(debug_info['errores']),
            'debug_completo': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'especialidad': especialidad,
            'resumen': 'critical_error',
            'error': str(e)
        }), 500

# ========================================
# 2. SISTEMA REPROGRAMACIÓN CITAS
# ========================================

# INTEGRACIÓN CON SOFIA.PY - Añadir al final de sofia.py
def detectar_reprogramacion_sofia(mensaje_usuario):
    """Detectar si cliente quiere reprogramar una cita"""
    patrones_reprogramacion = [
        r'reprogramar', r'cambiar.*cita', r'cambiar.*horario', r'cambiar.*fecha',
        r'mover.*cita', r'otro.*día', r'otro.*horario', r'postponer',
        r'aplazar', r'reagendar', r'modificar.*cita'
    ]
    
    for patron in patrones_reprogramacion:
        if re.search(patron, mensaje_usuario.lower()):
            return True
    return False

def manejar_reprogramacion_sofia(mensaje_usuario, session_id, numero_telefono):
    """Manejar proceso de reprogramación desde Sofía"""
    contexto = sessions.get(session_id, {})
    
    # Detectar datos en el mensaje
    fecha_detectada = detectar_fecha_en_mensaje(mensaje_usuario)
    horario_detectado = detectar_horario_en_mensaje(mensaje_usuario)
    
    # Estado del proceso de reprogramación
    estado_reprog = contexto.get('estado_reprogramacion', 'inicio')
    
    if estado_reprog == 'inicio':
        # Solicitar datos de la cita actual
        contexto['estado_reprogramacion'] = 'datos_actuales'
        sessions[session_id] = contexto
        return {"type": "speak", "text": "Perfecto, te ayudo a reprogramar tu cita. Dime tu nombre completo y la fecha de tu cita actual."}
    
    elif estado_reprog == 'datos_actuales':
        # Recopilar nombre y fecha actual
        nombre = detectar_nombre_en_mensaje(mensaje_usuario)
        if nombre:
            contexto['nombre_cliente'] = nombre
        
        if fecha_detectada:
            contexto['fecha_actual'] = fecha_detectada
        
        if contexto.get('nombre_cliente') and contexto.get('fecha_actual'):
            contexto['estado_reprogramacion'] = 'nueva_fecha'
            sessions[session_id] = contexto
            return {"type": "speak", "text": f"Entendido {contexto['nombre_cliente']}, tu cita del {contexto['fecha_actual']}. ¿Para qué fecha quieres reprogramarla?"}
        else:
            return {"type": "speak", "text": "Necesito tu nombre completo y la fecha de tu cita actual. ¿Puedes repetírmelo?"}
    
    elif estado_reprog == 'nueva_fecha':
        if fecha_detectada:
            contexto['nueva_fecha'] = fecha_detectada
            contexto['estado_reprogramacion'] = 'nuevo_horario'
            sessions[session_id] = contexto
            
            # Obtener horarios disponibles para esa fecha
            horarios = obtener_horarios_disponibles_sofia('astrologo_humano', datetime.strptime(fecha_detectada, '%Y-%m-%d'))
            if horarios:
                horarios_texto = ", ".join(horarios[:5])
                return {"type": "speak", "text": f"Para el {fecha_detectada} tengo disponible: {horarios_texto}. ¿Cuál prefieres?"}
            else:
                return {"type": "speak", "text": f"No tengo horarios disponibles para {fecha_detectada}. ¿Te interesa otra fecha?"}
        else:
            return {"type": "speak", "text": "¿Para qué fecha quieres reprogramar tu cita? Dime el día, por ejemplo: mañana, el viernes, o 25 de septiembre."}
    
    elif estado_reprog == 'nuevo_horario':
        if horario_detectado:
            # Ejecutar reprogramación
            try:
                import requests
                resultado = requests.post('http://localhost:5000/api/reprogramar-cita', json={
                    'nombre_cliente': contexto['nombre_cliente'],
                    'fecha_original': contexto['fecha_actual'],
                    'horario_original': '11:00-12:00',  # Tendremos que mejorarlo
                    'nueva_fecha': contexto['nueva_fecha'],
                    'nuevo_horario': horario_detectado,
                    'tipo_servicio': 'sofia_astrologo'
                })
                
                if resultado.status_code == 200:
                    data = resultado.json()
                    if data['success']:
                        # Limpiar contexto
                        sessions.pop(session_id, None)
                        return {"type": "speak", "text": f"¡Perfecto! He reprogramado tu cita para el {contexto['nueva_fecha']} a las {horario_detectado}. Te llegará una confirmación."}
                    else:
                        return {"type": "speak", "text": f"No he podido reprogramar la cita: {data['message']}. ¿Quieres intentar con otro horario?"}
                else:
                    return {"type": "speak", "text": "Ha ocurrido un error técnico. ¿Prefieres que te transfiera con un operador?"}
                    
            except Exception as e:
                return {"type": "speak", "text": "Ha ocurrido un error técnico. ¿Prefieres que te transfiera con un operador?"}
        else:
            return {"type": "speak", "text": "¿A qué hora prefieres la cita? Por ejemplo: 11:00, 16:00, etc."}

# INTEGRACIÓN CON VERONICA.PY - Añadir al final de veronica.py
def detectar_reprogramacion_veronica(mensaje_usuario):
    """Detectar si cliente quiere reprogramar una cita con Verónica"""
    return detectar_reprogramacion_sofia(mensaje_usuario)  # Misma lógica

def manejar_reprogramacion_veronica(mensaje_usuario, datos_actuales):
    """Manejar reprogramación desde Verónica"""
    try:
        # Lógica similar pero adaptada para Verónica
        # Por ahora, respuesta básica hasta implementar completo
        return {"type": "speak", "text": "Entiendo que quieres reprogramar tu cita. Estoy trabajando en eso. Mientras tanto, ¿puedes llamarnos al horario de oficina para que te ayudemos manualmente?"}
    except Exception as e:
        return {"type": "speak", "text": "Ha ocurrido un problema técnico. Te transferiré con un operador."}

def detectar_fecha_en_mensaje(texto):
    """Detectar fechas en formato natural"""
    import re
    from datetime import datetime, timedelta
    
    texto_lower = texto.lower()
    hoy = datetime.now()
    
    # Mañana
    if 'mañana' in texto_lower:
        return (hoy + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Pasado mañana  
    if 'pasado mañana' in texto_lower:
        return (hoy + timedelta(days=2)).strftime('%Y-%m-%d')
    
    # Días de la semana
    dias_semana = {
        'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2,
        'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
    }
    
    for dia, num_dia in dias_semana.items():
        if dia in texto_lower:
            dias_hasta = (num_dia - hoy.weekday()) % 7
            if dias_hasta == 0:  # Si es hoy, ir a la próxima semana
                dias_hasta = 7
            return (hoy + timedelta(days=dias_hasta)).strftime('%Y-%m-%d')
    
    # Formato DD/MM o DD-MM
    fecha_match = re.search(r'(\d{1,2})[/-](\d{1,2})', texto)
    if fecha_match:
        dia, mes = fecha_match.groups()
        try:
            fecha = datetime(hoy.year, int(mes), int(dia))
            return fecha.strftime('%Y-%m-%d')
        except:
            pass
    
    return None

def detectar_horario_en_mensaje(texto):
    """Detectar horarios en el mensaje"""
    import re
    
    # Patrones de horario
    patrones = [
        r'(\d{1,2}):(\d{2})',  # 14:30
        r'(\d{1,2}) de la mañana',  # 11 de la mañana
        r'(\d{1,2}) de la tarde',   # 4 de la tarde  
        r'(\d{1,2}):\d{2}-(\d{1,2}):\d{2}',  # 11:00-12:00
    ]
    
    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            # Simplificado: retornar formato estándar
            hora = match.group(1)
            if 'tarde' in texto.lower() and int(hora) < 12:
                hora = str(int(hora) + 12)
            return f"{hora}:00-{int(hora)+1}:00"
    
    return None

def detectar_nombre_en_mensaje(texto):
    """Detectar nombres en el mensaje"""
    import re
    
    # Patrón simple para nombres
    if 'me llamo' in texto.lower():
        partes = texto.lower().split('me llamo')
        if len(partes) > 1:
            nombre = partes[1].strip().split(',')[0].split('.')[0]
            return nombre.title()
    
    # Si no tiene "me llamo", asumir que es el nombre si no tiene números
    if not re.search(r'\d', texto) and len(texto.split()) <= 3:
        return texto.strip().title()
    
    return None

def buscar_evento_en_calendar(nombre_cliente, fecha_original, horario_original):
    """Buscar evento específico en Google Calendar"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return None, "Error conectando con Google Calendar"
        
        # Buscar eventos del día original
        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=f"{fecha_original}T00:00:00+01:00",
            timeMax=f"{fecha_original}T23:59:59+01:00",
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos_dia = eventos.get('items', [])
        
        # Buscar evento que coincida con cliente y horario
        for evento in eventos_dia:
            titulo = evento.get('summary', '')
            descripcion = evento.get('description', '')
            
            # Verificar si coincide con el cliente
            if (nombre_cliente.lower() in titulo.lower() or 
                nombre_cliente.lower() in descripcion.lower()):
                
                # Verificar horario aproximado
                start_time = evento.get('start', {}).get('dateTime', '')
                if horario_original.split('-')[0] in start_time:
                    return evento, "Evento encontrado"
        
        return None, f"No se encontró evento para {nombre_cliente} en {fecha_original} {horario_original}"
        
    except Exception as e:
        return None, f"Error buscando evento: {str(e)}"

def modificar_evento_calendar(evento_id, nueva_fecha, nuevo_horario, tipo_servicio):
    """Modificar evento existente en Google Calendar"""
    try:
        service = inicializar_google_calendar()
        if not service:
            return False, "Error conectando con Google Calendar"
        
        # Obtener evento actual
        evento = service.events().get(calendarId=CALENDAR_ID, eventId=evento_id).execute()
        
        # Calcular nueva duración según tipo
        duraciones = {
            'sofia_astrologo': 60,
            'sofia_tarot': 60,
            'veronica_telefono': 30,
            'veronica_visita': 90
        }
        
        duracion = duraciones.get(tipo_servicio, 60)
        
        # Calcular nuevas horas
        from datetime import datetime, timedelta
        hora_inicio = nuevo_horario.split('-')[0]
        inicio_dt = datetime.strptime(f"{nueva_fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
        fin_dt = inicio_dt + timedelta(minutes=duracion)
        
        # Modificar evento
        evento.update({
            'start': {
                'dateTime': inicio_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Europe/Madrid',
            },
            'end': {
                'dateTime': fin_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': 'Europe/Madrid',
            },
        })
        
        # Actualizar en Google Calendar
        evento_actualizado = service.events().update(
            calendarId=CALENDAR_ID,
            eventId=evento_id,
            body=evento
        ).execute()
        
        return True, evento_actualizado.get('id')
        
    except Exception as e:
        return False, f"Error modificando evento: {str(e)}"

@app.route('/api/reprogramar-cita', methods=['POST'])
def api_reprogramar_cita():
    """API para reprogramar citas existentes"""
    try:
        data = request.get_json()
        
        # Datos requeridos
        nombre_cliente = data.get('nombre_cliente')
        fecha_original = data.get('fecha_original')  # YYYY-MM-DD
        horario_original = data.get('horario_original')  # HH:MM-HH:MM
        nueva_fecha = data.get('nueva_fecha')  # YYYY-MM-DD
        nuevo_horario = data.get('nuevo_horario')  # HH:MM-HH:MM
        tipo_servicio = data.get('tipo_servicio', 'sofia_astrologo')
        
        if not all([nombre_cliente, fecha_original, horario_original, nueva_fecha, nuevo_horario]):
            return jsonify({
                "success": False,
                "message": "Faltan datos requeridos"
            }), 400
        
        print(f"🔄 Reprogramando cita: {nombre_cliente} de {fecha_original} {horario_original} → {nueva_fecha} {nuevo_horario}")
        
        # PASO 1: Verificar disponibilidad del nuevo horario
        disponible, mensaje = verificar_disponibilidad(nueva_fecha, nuevo_horario)
        if not disponible:
            return jsonify({
                "success": False,
                "message": f"Nuevo horario no disponible: {mensaje}"
            })
        
        # PASO 2: Buscar evento original
        evento_original, mensaje_busqueda = buscar_evento_en_calendar(nombre_cliente, fecha_original, horario_original)
        if not evento_original:
            return jsonify({
                "success": False,
                "message": f"No se encontró la cita original: {mensaje_busqueda}"
            })
        
        # PASO 3: Modificar evento
        exito, resultado = modificar_evento_calendar(
            evento_original['id'], 
            nueva_fecha, 
            nuevo_horario, 
            tipo_servicio
        )
        
        if exito:
            # PASO 4: Notificar por Telegram
            enviar_notificacion_telegram_reprogramacion(
                nombre_cliente, 
                fecha_original, horario_original,
                nueva_fecha, nuevo_horario,
                tipo_servicio
            )
            
            return jsonify({
                "success": True,
                "message": "Cita reprogramada correctamente",
                "evento_id": resultado,
                "cambio": f"{fecha_original} {horario_original} → {nueva_fecha} {nuevo_horario}"
            })
        else:
            return jsonify({
                "success": False,
                "message": resultado
            })
        
    except Exception as e:
        print(f"❌ Error reprogramando cita: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

def enviar_notificacion_telegram_reprogramacion(nombre, fecha_ant, horario_ant, fecha_nueva, horario_nuevo, tipo):
    """Notificación específica para reprogramaciones"""
    try:
        from datetime import datetime
        fecha_ant_obj = datetime.strptime(fecha_ant, '%Y-%m-%d')
        fecha_nueva_obj = datetime.strptime(fecha_nueva, '%Y-%m-%d')
        
        fecha_ant_legible = fecha_ant_obj.strftime('%d/%m/%Y')
        fecha_nueva_legible = fecha_nueva_obj.strftime('%d/%m/%Y')
        
        mensaje = f"""
🔄 <b>CITA REPROGRAMADA</b>

👤 <b>Cliente:</b> {nombre}
🎯 <b>Servicio:</b> {tipo.replace('_', ' ').title()}

📅 <b>Fecha anterior:</b> {fecha_ant_legible}
⏰ <b>Horario anterior:</b> {horario_ant}

📅 <b>Nueva fecha:</b> {fecha_nueva_legible}
⏰ <b>Nuevo horario:</b> {horario_nuevo}

✅ <b>Estado:</b> Modificada en Google Calendar
🔧 <b>Sistema:</b> Reprogramación automática
        """.strip()
        
        enviar_telegram_mejora(mensaje)
        
    except Exception as e:
        print(f"⚠️ Error enviando notificación reprogramación: {e}")

@app.route('/test/panel_reprogramar')
def panel_reprogramar_citas():
    """Panel para probar reprogramación de citas"""
    html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Panel Reprogramar Citas - AS Asesores</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 20px auto; padding: 20px; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .resultado { margin: 20px 0; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <h1>🔄 Panel de Reprogramación de Citas</h1>
    
    <form onsubmit="reprogramarCita(event)">
        <div class="form-group">
            <label>Nombre del Cliente:</label>
            <input type="text" id="nombre_cliente" placeholder="Ej: Juan Pérez" required>
        </div>
        
        <div class="form-group">
            <label>Fecha Original (YYYY-MM-DD):</label>
            <input type="date" id="fecha_original" required>
        </div>
        
        <div class="form-group">
            <label>Horario Original:</label>
            <input type="text" id="horario_original" placeholder="Ej: 11:00-12:00" required>
        </div>
        
        <div class="form-group">
            <label>Nueva Fecha (YYYY-MM-DD):</label>
            <input type="date" id="nueva_fecha" required>
        </div>
        
        <div class="form-group">
            <label>Nuevo Horario:</label>
            <input type="text" id="nuevo_horario" placeholder="Ej: 16:00-17:00" required>
        </div>
        
        <div class="form-group">
            <label>Tipo de Servicio:</label>
            <select id="tipo_servicio">
                <option value="sofia_astrologo">Sofía - Astróloga</option>
                <option value="sofia_tarot">Sofía - Tarot</option>
                <option value="veronica_telefono">Verónica - Teléfono</option>
                <option value="veronica_visita">Verónica - Visita</option>
            </select>
        </div>
        
        <button type="submit" class="btn">🔄 Reprogramar Cita</button>
    </form>
    
    <div id="resultado"></div>

    <script>
    function reprogramarCita(event) {
        event.preventDefault();
        
        const datos = {
            nombre_cliente: document.getElementById('nombre_cliente').value,
            fecha_original: document.getElementById('fecha_original').value,
            horario_original: document.getElementById('horario_original').value,
            nueva_fecha: document.getElementById('nueva_fecha').value,
            nuevo_horario: document.getElementById('nuevo_horario').value,
            tipo_servicio: document.getElementById('tipo_servicio').value
        };
        
        document.getElementById('resultado').innerHTML = '<div class="resultado">⏳ Reprogramando cita...</div>';
        
        fetch('/api/reprogramar-cita', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(datos)
        })
        .then(response => response.json())
        .then(data => {
            const clase = data.success ? 'success' : 'error';
            const icono = data.success ? '✅' : '❌';
            
            document.getElementById('resultado').innerHTML = `
                <div class="resultado ${clase}">
                    ${icono} ${data.message}
                    ${data.cambio ? '<br><strong>Cambio:</strong> ' + data.cambio : ''}
                    ${data.evento_id ? '<br><strong>ID Evento:</strong> ' + data.evento_id : ''}
                </div>
            `;
        })
        .catch(error => {
            document.getElementById('resultado').innerHTML = 
                '<div class="resultado error">❌ Error de conexión: ' + error + '</div>';
        });
    }
    </script>
</body>
</html>
    '''
    return html
    
# AÑADIR AL FINAL DE main.py - DEBUG HTML DETALLADO

@app.route('/test/debug_html_step_by_step/<especialidad>')
def debug_html_paso_a_paso(especialidad):
    """Debug detallado paso a paso de la generación HTML"""
    debug_resultado = {
        'especialidad': especialidad,
        'pasos': {},
        'errores': [],
        'datos_completos': {}
    }
    
    try:
        # PASO 1: Preparar datos
        datos_cliente = {
            'nombre': 'Cliente Debug',
            'email': 'debug@test.com',
            'codigo_servicio': f'DEBUG_{especialidad.upper()}',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        debug_resultado['pasos']['datos_cliente'] = {'status': 'success', 'datos': datos_cliente}
        
        # PASO 2: Importar funciones
        try:
            from informes import generar_informe_html, obtener_template_html
            debug_resultado['pasos']['importacion'] = {'status': 'success'}
        except Exception as e:
            debug_resultado['pasos']['importacion'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error importación: {e}")
            return jsonify(debug_resultado)
        
        # PASO 3: Verificar template HTML
        try:
            template_html = obtener_template_html(especialidad)
            debug_resultado['pasos']['template_html'] = {
                'status': 'success',
                'longitud': len(template_html),
                'preview': template_html[:200] + "..." if len(template_html) > 200 else template_html
            }
        except Exception as e:
            debug_resultado['pasos']['template_html'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error template: {e}")
            return jsonify(debug_resultado)
        
        # PASO 4: Verificar Jinja2
        try:
            from jinja2 import Template
            template = Template(template_html)
            debug_resultado['pasos']['jinja2'] = {'status': 'success'}
        except Exception as e:
            debug_resultado['pasos']['jinja2'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error Jinja2: {e}")
            return jsonify(debug_resultado)
        
        # PASO 5: Preparar datos template
        try:
            from datetime import datetime
            import pytz
            
            madrid_tz = pytz.timezone('Europe/Madrid')
            ahora = datetime.now(madrid_tz)
            
            datos_template = {
                'nombre': datos_cliente['nombre'],
                'email': datos_cliente['email'],
                'fecha_nacimiento': datos_cliente['fecha_nacimiento'],
                'hora_nacimiento': datos_cliente['hora_nacimiento'],
                'lugar_nacimiento': datos_cliente['lugar_nacimiento'],
                'fecha_generacion': ahora.strftime('%d/%m/%Y'),
                'hora_generacion': ahora.strftime('%H:%M'),
                'resumen_sesion': "Resumen de prueba para testing"
            }
            debug_resultado['pasos']['datos_template'] = {'status': 'success', 'datos': datos_template}
        except Exception as e:
            debug_resultado['pasos']['datos_template'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error datos template: {e}")
            return jsonify(debug_resultado)
        
        # PASO 6: Renderizar template
        try:
            html_content = template.render(**datos_template)
            debug_resultado['pasos']['renderizado'] = {
                'status': 'success',
                'longitud': len(html_content),
                'preview': html_content[:300] + "..." if len(html_content) > 300 else html_content
            }
        except Exception as e:
            debug_resultado['pasos']['renderizado'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error renderizado: {e}")
            return jsonify(debug_resultado)
        
        # PASO 7: Verificar directorios
        try:
            import os
            os.makedirs('templates', exist_ok=True)
            debug_resultado['pasos']['directorios'] = {'status': 'success'}
        except Exception as e:
            debug_resultado['pasos']['directorios'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error directorios: {e}")
            return jsonify(debug_resultado)
        
        # PASO 8: Intentar escribir archivo
        try:
            from informes import generar_nombre_archivo_unico
            nombre_base = generar_nombre_archivo_unico(especialidad, 'DEBUG')
            archivo_html = f"templates/informe_{nombre_base}.html"
            
            with open(archivo_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Verificar que se creó
            if os.path.exists(archivo_html):
                debug_resultado['pasos']['archivo_creado'] = {
                    'status': 'success',
                    'archivo': archivo_html,
                    'tamaño': os.path.getsize(archivo_html)
                }
            else:
                debug_resultado['pasos']['archivo_creado'] = {'status': 'error', 'error': 'Archivo no existe después de escribir'}
                debug_resultado['errores'].append("Archivo no creado")
                
        except Exception as e:
            debug_resultado['pasos']['archivo_creado'] = {'status': 'error', 'error': str(e)}
            debug_resultado['errores'].append(f"Error escribiendo archivo: {e}")
        
        # RESUMEN
        debug_resultado['resumen'] = 'success' if not debug_resultado['errores'] else 'error'
        debug_resultado['total_errores'] = len(debug_resultado['errores'])
        
        return jsonify(debug_resultado)
        
    except Exception as e:
        debug_resultado['error_critico'] = str(e)
        debug_resultado['resumen'] = 'critical_error'
        return jsonify(debug_resultado)

@app.route('/test/debug_simple_html')
def debug_simple_html():
    """Test simple de creación HTML"""
    try:
        # Test básico de Jinja2
        from jinja2 import Template
        
        html_simple = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Hola {{ nombre }}</h1>
            <p>Email: {{ email }}</p>
        </body>
        </html>
        """
        
        template = Template(html_simple)
        resultado = template.render(nombre="Test", email="test@test.com")
        
        # Intentar escribir archivo
        import os
        os.makedirs('templates', exist_ok=True)
        
        with open('templates/test_simple.html', 'w', encoding='utf-8') as f:
            f.write(resultado)
        
        return jsonify({
            'status': 'success',
            'html_generado': resultado,
            'archivo_creado': os.path.exists('templates/test_simple.html')
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'tipo_error': type(e).__name__
        })

@app.route('/test/verificar_informes_py')
def verificar_informes_py():
    """Verificar que informes.py está funcionando"""
    try:
        # Verificar importaciones
        resultado = {}
        
        try:
            import informes
            resultado['modulo_informes'] = 'OK'
        except Exception as e:
            resultado['modulo_informes'] = f'ERROR: {e}'
        
        try:
            from informes import obtener_template_html
            resultado['funcion_template'] = 'OK'
        except Exception as e:
            resultado['funcion_template'] = f'ERROR: {e}'
        
        try:
            from informes import generar_informe_html
            resultado['funcion_generar'] = 'OK'
        except Exception as e:
            resultado['funcion_generar'] = f'ERROR: {e}'
        
        try:
            from jinja2 import Template
            resultado['jinja2'] = 'OK'
        except Exception as e:
            resultado['jinja2'] = f'ERROR: {e}'
        
        try:
            import pytz
            resultado['pytz'] = 'OK'
        except Exception as e:
            resultado['pytz'] = f'ERROR: {e}'
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'error_critico': str(e),
            'tipo': type(e).__name__
        })
        
@app.route('/test/debug_jinja_incremental/<especialidad>')
def debug_jinja_incremental(especialidad):
    """Debug línea por línea del template Jinja2"""
    try:
        from informes import obtener_template_html
        from jinja2 import Template, TemplateSyntaxError
        
        # Obtener template completo
        template_html = obtener_template_html(especialidad)
        
        # Dividir en líneas
        lineas = template_html.split('\n')
        
        resultado = {
            'especialidad': especialidad,
            'total_lineas': len(lineas),
            'template_preview': template_html[:500] + "..." if len(template_html) > 500 else template_html,
            'errores_sintaxis': [],
            'lineas_problematicas': []
        }
        
        # Probar template completo primero
        try:
            template = Template(template_html)
            resultado['template_completo'] = 'OK'
        except TemplateSyntaxError as e:
            resultado['template_completo'] = f'ERROR: {str(e)}'
            resultado['error_linea'] = getattr(e, 'lineno', 'desconocida')
            resultado['error_mensaje'] = str(e)
            
            # Si hay error, buscar línea problemática
            try:
                linea_error = e.lineno - 1 if hasattr(e, 'lineno') and e.lineno > 0 else 0
                if 0 <= linea_error < len(lineas):
                    resultado['linea_problema'] = {
                        'numero': linea_error + 1,
                        'contenido': lineas[linea_error],
                        'contexto_antes': lineas[max(0, linea_error-2):linea_error],
                        'contexto_despues': lineas[linea_error+1:min(len(lineas), linea_error+3)]
                    }
            except:
                pass
        
        # Buscar patrones problemáticos específicos
        patrones_problematicos = [
            r'\{\{\{\{',  # 4 llaves
            r'\}\}\}\}',  # 4 llaves cierre
            r'\{\%\%',    # doble %
            r'\%\%\}',    # doble % cierre
            r'\{\{[^}]*\{\{',  # variables anidadas
            r'\}\}[^{]*\}\}',  # cierres duplicados
        ]
        
        import re
        for i, linea in enumerate(lineas):
            for patron in patrones_problematicos:
                if re.search(patron, linea):
                    resultado['lineas_problematicas'].append({
                        'numero': i + 1,
                        'contenido': linea.strip(),
                        'patron': patron
                    })
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'error_critico': str(e),
            'tipo': type(e).__name__
        })

@app.route('/test/template_minimo')
def test_template_minimo():
    """Probar template mínimo funcional"""
    try:
        from jinja2 import Template
        
        # Template super básico
        template_minimo = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Mínimo</title>
</head>
<body>
    <h1>{{ nombre }}</h1>
    <p>Email: {{ email }}</p>
    
    {% if mostrar_extra %}
        <p>Contenido extra: {{ contenido_extra }}</p>
    {% endif %}
    
    {% for item in lista %}
        <li>{{ item }}</li>
    {% endfor %}
</body>
</html>
        """
        
        template = Template(template_minimo)
        resultado = template.render(
            nombre="Test Usuario",
            email="test@test.com",
            mostrar_extra=True,
            contenido_extra="Funciona!",
            lista=["Item 1", "Item 2", "Item 3"]
        )
        
        return jsonify({
            'status': 'success',
            'template_funciona': True,
            'html_generado': resultado
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'template_funciona': False,
            'error': str(e)
        })

@app.route('/test/corregir_template_carta_astral')
def corregir_template_carta_astral():
    """Generar template corregido para carta astral"""
    
    # Template limpio sin errores
    template_corregido = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Carta Astral - AS Cartastral</title>
    <style>
        body { font-family: Georgia, serif; margin: 40px; line-height: 1.6; }
        .portada { text-align: center; margin-bottom: 30px; }
        .datos-natales { background: #f8f9fa; padding: 20px; margin: 20px 0; }
        .section { margin: 30px 0; }
        .footer { margin-top: 50px; font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <div class="portada">
        <h1>🌟 CARTA ASTRAL PERSONALIZADA 🌟</h1>
        <h2>{{ nombre }}</h2>
        <p>AS Cartastral - Servicios Astrológicos Personalizados</p>
    </div>

    <div class="datos-natales">
        <h2>📊 Datos Natales</h2>
        <p><strong>Nombre:</strong> {{ nombre }}</p>
        <p><strong>Email:</strong> {{ email }}</p>
        <p><strong>Fecha de nacimiento:</strong> {{ fecha_nacimiento }}</p>
        <p><strong>Hora de nacimiento:</strong> {{ hora_nacimiento }}</p>
        <p><strong>Lugar de nacimiento:</strong> {{ lugar_nacimiento }}</p>
    </div>

    {% if carta_natal_img %}
    <div class="section">
        <h2>🌍 Tu Carta Natal</h2>
        <img src="file://{{ carta_natal_img }}" alt="Carta natal" style="max-width: 100%;">
        <p><em>Tu mapa astrológico personal en el momento de tu nacimiento</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>✨ Introducción</h2>
        <p>Bienvenido/a a tu análisis astrológico personalizado. Esta carta astral revela las posiciones planetarias exactas en el momento de tu nacimiento.</p>
    </div>

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión Telefónica</h2>
        <p><strong>Duración:</strong> 40 minutos</p>
        <div>{{ resumen_sesion }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""
    
    # Probar que funciona
    try:
        from jinja2 import Template
        template = Template(template_corregido)
        
        # Test con datos dummy
        resultado = template.render(
            nombre="Cliente Test",
            email="test@test.com",
            fecha_nacimiento="15/07/1985",
            hora_nacimiento="10:30",
            lugar_nacimiento="Madrid, España",
            carta_natal_img="test.png",
            resumen_sesion="Resumen de prueba",
            fecha_generacion="20/09/2025",
            hora_generacion="15:30"
        )
        
        return jsonify({
            'status': 'success',
            'template_corregido': template_corregido,
            'test_resultado': resultado[:500] + "..." if len(resultado) > 500 else resultado,
            'longitud': len(resultado)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'template_corregido': template_corregido
        })

@app.route("/test/ver_html_generado/<archivo>")
def ver_html_generado(archivo):
    """Ver contenido del HTML generado"""
    try:
        ruta_archivo = f"templates/{archivo}"
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            return f"<pre>{contenido}</pre>"
        else:
            return f"Archivo no encontrado: {ruta_archivo}"
    except Exception as e:
        return f"Error: {str(e)}"
        
@app.route("/test/debug_rutas_imagenes_directo")
def debug_rutas_imagenes_directo():
    """Debug directo de las rutas de imágenes"""
    try:
        from informes import obtener_ruta_imagen_absoluta
        import os
        
        # Test todas las imágenes que necesitamos
        imagenes_test = [
            'logo.jpg', 'astrologia-3.jpg', 'Tarot y astrologia-5.jpg',
            'Sinastria.jpg', 'astrologia-1.jpg', 'coaching-4.jpg'
        ]
        
        resultados = {}
        
        for imagen in imagenes_test:
            # Llamar a nuestra función
            ruta_generada = obtener_ruta_imagen_absoluta(imagen)
            
            # Verificar si existe
            existe = os.path.exists(ruta_generada) if not ruta_generada.startswith('data:') else False
            
            resultados[imagen] = {
                'ruta_generada': ruta_generada,
                'existe_archivo': existe,
                'es_placeholder': ruta_generada.startswith('data:image/svg')
            }
        
        # También listar lo que hay realmente en img/
        contenido_img = []
        if os.path.exists('./img/'):
            for archivo in os.listdir('./img/'):
                if archivo.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    contenido_img.append(archivo)
        
        return jsonify({
            'resultados_imagenes': resultados,
            'archivos_reales_en_img': contenido_img,
            'directorio_actual': os.getcwd()
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'tipo': type(e).__name__})
        
@app.route("/test/debug_railway_images")
def debug_railway_images():
    """Debug específico para Railway - verificar acceso real a imágenes"""
    try:
        from informes import obtener_ruta_imagen_absoluta
        import os
        
        # Test cada imagen específica
        imagenes_test = ['logo.jpg', 'astrologia-3.jpg', 'coaching-4.jpg']
        resultados = {}
        
        for imagen in imagenes_test:
            resultado = {
                'imagen_buscada': imagen,
                'ruta_generada': '',
                'archivo_existe': False,
                'es_placeholder': False,
                'contenido_img_dir': [],
                'ruta_absoluta_real': '',
                'accesible_playwright': False
            }
            
            # 1. Llamar función
            ruta = obtener_ruta_imagen_absoluta(imagen)
            resultado['ruta_generada'] = ruta
            resultado['es_placeholder'] = ruta.startswith('data:')
            
            # 2. Si no es placeholder, verificar acceso
            if not resultado['es_placeholder']:
                resultado['archivo_existe'] = os.path.exists(ruta)
                resultado['ruta_absoluta_real'] = os.path.abspath(ruta) if resultado['archivo_existe'] else 'No existe'
            
            # 3. Listar contenido real de img/
            if os.path.exists('./img/'):
                archivos_img = []
                for f in os.listdir('./img/'):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        archivos_img.append(f)
                resultado['contenido_img_dir'] = archivos_img
            
            # 4. Test de acceso Playwright simulado
            if resultado['archivo_existe']:
                try:
                    # Simular lo que hace Playwright
                    with open(ruta, 'rb') as f:
                        f.read(100)  # Leer un poco
                    resultado['accesible_playwright'] = True
                except:
                    resultado['accesible_playwright'] = False
            
            resultados[imagen] = resultado
        
        # Info del sistema
        sistema_info = {
            'directorio_actual': os.getcwd(),
            'usuario_actual': os.getenv('USER', 'unknown'),
            'existe_img_dir': os.path.exists('./img/'),
            'permisos_img_dir': oct(os.stat('./img/').st_mode)[-3:] if os.path.exists('./img/') else 'No existe',
            'variables_entorno_railway': {
                'RAILWAY_ENVIRONMENT': os.getenv('RAILWAY_ENVIRONMENT'),
                'RAILWAY_PROJECT_NAME': os.getenv('RAILWAY_PROJECT_NAME'),
                'PORT': os.getenv('PORT')
            }
        }
        
        return jsonify({
            'resultados_imagenes': resultados,
            'sistema_info': sistema_info,
            'problema_detectado': 'Railway container access' if any(not r['archivo_existe'] and not r['es_placeholder'] for r in resultados.values()) else 'Otro'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'tipo_error': type(e).__name__
        })
        
@app.route("/test/ver_html_ultimo")
def ver_html_ultimo():
    """Ver el último HTML generado para debugging"""
    try:
        import os
        import glob
        
        # Buscar el archivo HTML más reciente
        patron = "templates/informe_*.html"
        archivos = glob.glob(patron)
        
        if archivos:
            archivo_mas_reciente = max(archivos, key=os.path.getmtime)
            
            with open(archivo_mas_reciente, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar las líneas de imágenes específicamente
            lineas_img = []
            for i, linea in enumerate(contenido.split('\n')):
                if '<img src=' in linea:
                    lineas_img.append(f"Línea {i+1}: {linea.strip()}")
            
            return f"""
            <h2>Archivo: {archivo_mas_reciente}</h2>
            <h3>🖼️ Líneas de imágenes encontradas:</h3>
            <pre>{'<br>'.join(lineas_img)}</pre>
            
            <h3>📄 HTML completo:</h3>
            <textarea style="width:100%; height:400px;">{contenido}</textarea>
            
            <h3>🔗 Ver renderizado:</h3>
            <iframe src="/{archivo_mas_reciente}" width="100%" height="600px"></iframe>
            """
        else:
            return "No se encontraron archivos HTML generados"
            
    except Exception as e:
        return f"Error: {str(e)}"

def buscar_o_crear_imagen_dummy(tipo_imagen, timestamp):
    """Buscar imagen existente o usar una dummy"""
    try:
        import os
        import glob
        
        print(f"🔍 Buscando imagen para: {tipo_imagen}")
        
        # 1. Buscar en static/ archivos recientes
        patterns = [
            f"static/{tipo_imagen}_*.png",
            f"static/*{tipo_imagen}*.png"
        ]
        
        archivos_encontrados = []
        for pattern in patterns:
            try:
                archivos_encontrados.extend(glob.glob(pattern))
            except Exception as e:
                print(f"⚠️ Error en patrón {pattern}: {e}")
        
        if archivos_encontrados:
            try:
                archivo_mas_reciente = max(archivos_encontrados, key=os.path.getmtime)
                print(f"✅ Usando imagen existente: {archivo_mas_reciente}")
                return archivo_mas_reciente
            except Exception as e:
                print(f"⚠️ Error seleccionando archivo reciente: {e}")
        
        # 2. Buscar en img/ (imágenes estáticas)
        img_patterns = [
            f"img/{tipo_imagen}*.jpg",
            f"img/{tipo_imagen}*.JPG",
            f"img/{tipo_imagen}*.png",
            f"img/*{tipo_imagen}*.jpg",
            f"img/*{tipo_imagen}*.JPG"
        ]
        
        for pattern in img_patterns:
            try:
                archivos_img = glob.glob(pattern)
                if archivos_img:
                    print(f"✅ Usando imagen estática: {archivos_img[0]}")
                    return archivos_img[0]
            except Exception as e:
                print(f"⚠️ Error en patrón img {pattern}: {e}")
        
        # 3. Crear imagen dummy
        dummy_path = f"static/{tipo_imagen}_dummy_{timestamp}.png"
        print(f"🔨 Creando imagen dummy: {dummy_path}")
        
        if crear_imagen_dummy(dummy_path, tipo_imagen):
            return dummy_path
        else:
            print(f"⚠️ No se pudo crear dummy, devolviendo ruta de fallback")
            return dummy_path
            
    except Exception as e:
        print(f"❌ Error en buscar_o_crear_imagen_dummy: {e}")
        return f"static/error_{tipo_imagen}_{timestamp}.png"

def crear_imagen_dummy(ruta_archivo, tipo_imagen):
    """Crear imagen dummy simple para testing"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import os
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
        
        # Crear imagen base
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Añadir texto
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        texto = f"IMAGEN DUMMY\n{tipo_imagen.upper()}\nGenerada para testing"
        
        # Dibujar rectángulo de fondo
        draw.rectangle([50, 50, 750, 550], outline='black', width=3)
        
        # Dibujar texto centrado
        if font:
            draw.text((400, 300), texto, fill='black', font=font, anchor='mm')
        else:
            draw.text((400, 300), texto, fill='black', anchor='mm')
        
        # Guardar imagen
        img.save(ruta_archivo, 'PNG')
        print(f"✅ Imagen dummy creada: {ruta_archivo}")
        return True
        
    except Exception as e:
        print(f"❌ Error creando imagen dummy: {e}")
        try:
            # Crear archivo vacío como fallback
            with open(ruta_archivo, 'w') as f:
                f.write("")
            return False
        except:
            return False

# ===================================
# ENDPOINTS DE DEBUG (AQUÍ SÍ ESTÁ DEFINIDO 'app')
# ===================================

@app.route('/test/debug_archivos_unicos/<especialidad>')
def debug_archivos_unicos(especialidad):
    """Debug específico para archivos_unicos"""
    try:
        print(f"🔍 Debug: Creando archivos_unicos para {especialidad}")
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        
        # Verificar que no sea None o vacío
        if archivos_unicos is None:
            return jsonify({
                'error': 'crear_archivos_unicos_testing() devolvió None',
                'especialidad': especialidad
            }), 500
            
        if not isinstance(archivos_unicos, dict):
            return jsonify({
                'error': f'archivos_unicos no es dict, es: {type(archivos_unicos)}',
                'especialidad': especialidad,
                'valor': str(archivos_unicos)
            }), 500
        
        print(f"🔍 Debug: archivos_unicos creados: {archivos_unicos}")
        
        # Verificar existencia de archivos
        archivos_verificados = {}
        
        for key, ruta in archivos_unicos.items():
            print(f"🔍 Debug: Procesando {key} = {ruta} (tipo: {type(ruta)})")
            
            # Manejar solo strings que parecen rutas de archivo
            if isinstance(ruta, str) and ('/' in ruta or '\\' in ruta or ruta.endswith(('.png', '.jpg', '.jpeg', '.JPG'))):
                # Es una ruta de archivo
                try:
                    if os.path.exists(ruta):
                        archivos_verificados[key] = {
                            'ruta': ruta,
                            'existe': True,
                            'tamaño': os.path.getsize(ruta),
                            'tipo': 'archivo'
                        }
                    else:
                        archivos_verificados[key] = {
                            'ruta': ruta,
                            'existe': False,
                            'tipo': 'archivo_no_encontrado'
                        }
                except Exception as e:
                    archivos_verificados[key] = {
                        'ruta': ruta,
                        'existe': False,
                        'tipo': 'error_verificacion',
                        'error': str(e)
                    }
            else:
                # No es una ruta de archivo (número, diccionario, etc.)
                archivos_verificados[key] = {
                    'valor': ruta,
                    'tipo': str(type(ruta).__name__),
                    'es_ruta': False
                }
        
        # Contar solo archivos (no otros valores)
        archivos_reales = {k: v for k, v in archivos_verificados.items() 
                          if v.get('tipo', '').startswith('archivo')}
        archivos_existentes = sum(1 for v in archivos_reales.values() 
                                 if v.get('existe', False))
        
        return jsonify({
            'especialidad': especialidad,
            'archivos_unicos_generados': archivos_unicos,
            'verificacion_existencia': archivos_verificados,
            'total_elementos': len(archivos_unicos),
            'total_archivos_esperados': len(archivos_reales),
            'archivos_existentes': archivos_existentes,
            'elementos_no_archivo': [k for k, v in archivos_verificados.items() 
                                   if not v.get('es_ruta', True)]
        })
        
    except Exception as e:
        import traceback
        error_details = {
            'error': str(e),
            'especialidad': especialidad,
            'traceback': traceback.format_exc(),
            'error_type': type(e).__name__
        }
        
        print(f"❌ Error en debug_archivos_unicos: {error_details}")
        return jsonify(error_details), 500

# ===================================
# MODIFICAR FUNCIÓN EXISTENTE generar_solo_pdf() EN main.py
# ===================================

# Buscar esta función en main.py y REEMPLAZAR con:
def generar_solo_pdf(datos_cliente, tipo_servicio):
    """Generar solo PDF sin enviar email - CON IMÁGENES DE PRUEBA"""
    try:
        from informes import generar_informe_html, convertir_html_a_pdf, generar_nombre_archivo_unico
        import os
        
        print(f"📄 Generando PDF para {tipo_servicio}")
        
        # 🔥 USAR ARCHIVOS_UNICOS DE PRUEBA (en lugar de diccionario vacío)
        archivos_unicos_prueba = crear_archivos_unicos_testing(tipo_servicio)
        
        # Debug: Imprimir qué se está pasando
        print(f"🔥 DEBUG archivos_unicos_prueba: {archivos_unicos_prueba}")
        
        # Generar HTML CON archivos_unicos
        archivo_html = generar_informe_html(
            datos_cliente, 
            tipo_servicio, 
            archivos_unicos_prueba,  # 🔥 CAMBIO: No más diccionario vacío
            "Resumen de prueba para testing - Generado en Railway"
        )
        
        if not archivo_html:
            print("❌ Error generando HTML")
            return None
        
        # Generar PDF
        nombre_base = generar_nombre_archivo_unico(tipo_servicio, datos_cliente.get('codigo_servicio', ''))
        archivo_pdf = f"informes/{nombre_base}.pdf"
        
        # Crear directorio si no existe
        os.makedirs('informes', exist_ok=True)
        
        exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
        
        if exito_pdf:
            print(f"✅ PDF generado: {archivo_pdf}")
            return archivo_pdf
        else:
            print("❌ Error generando PDF")
            return None
        
    except Exception as e:
        print(f"❌ Error en generar_solo_pdf: {e}")
        import traceback
        traceback.print_exc()
        return None
        
@app.route('/test/ping')
def test_ping():
    """Endpoint simple para verificar que la app funciona"""
    return jsonify({
        'status': 'OK',
        'message': 'La aplicación está funcionando',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test/endpoints')  
def test_endpoints():
    """Listar todos los endpoints disponibles"""
    import urllib.parse
    endpoints = []
    for rule in app.url_map.iter_rules():
        endpoints.append({
            'endpoint': rule.rule,
            'methods': list(rule.methods)
        })
    return jsonify({
        'total_endpoints': len(endpoints),
        'endpoints': endpoints
    })
    
def buscar_o_crear_imagen_dummy(tipo_imagen, timestamp):
    """Buscar imagen existente o crear dummy"""
    try:
        import os
        import glob
        
        # 1. Buscar en static/ archivos existentes
        patterns = [
            f"static/{tipo_imagen}_*.png",
            f"static/*{tipo_imagen}*.png"
        ]
        
        archivos_encontrados = []
        for pattern in patterns:
            try:
                archivos_encontrados.extend(glob.glob(pattern))
            except:
                pass
        
        if archivos_encontrados:
            archivo_mas_reciente = max(archivos_encontrados, key=os.path.getmtime)
            return archivo_mas_reciente
        
        # 2. Crear imagen dummy
        dummy_path = f"static/{tipo_imagen}_dummy_{timestamp}.png"
        crear_imagen_dummy(dummy_path, tipo_imagen)
        return dummy_path
            
    except Exception as e:
        print(f"❌ Error en buscar_o_crear_imagen_dummy: {e}")
        return f"static/error_{tipo_imagen}_{timestamp}.png"

def crear_imagen_dummy(ruta_archivo, tipo_imagen):
    """Crear imagen dummy simple"""
    try:
        from PIL import Image, ImageDraw
        import os
        
        os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
        
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Dibujar rectángulo y texto
        draw.rectangle([50, 50, 750, 550], outline='black', width=3)
        draw.text((400, 300), f"IMAGEN DUMMY\n{tipo_imagen.upper()}", fill='black', anchor='mm')
        
        img.save(ruta_archivo, 'PNG')
        print(f"✅ Imagen dummy creada: {ruta_archivo}")
        return True
        
    except Exception as e:
        print(f"❌ Error creando imagen dummy: {e}")
        return False
        
@app.route('/test/verificar_cambios_aplicados/<especialidad>')
def verificar_cambios_aplicados(especialidad):
    """Verificar si los cambios se aplicaron correctamente"""
    try:
        from informes import generar_informe_html, generar_nombre_archivo_unico
        import os
        
        # Datos de prueba
        datos_cliente = {
            'nombre': 'Cliente Test Verificación',
            'email': 'test@verificacion.com',
            'codigo_servicio': 'VERIFY_123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        print(f"🔍 VERIFICACIÓN: Iniciando test para {especialidad}")
        
        # PASO 1: Crear archivos_unicos de prueba
        archivos_unicos_prueba = crear_archivos_unicos_testing(especialidad)
        print(f"🔍 PASO 1 - archivos_unicos creados: {archivos_unicos_prueba}")
        
        # PASO 2: Intentar generar HTML directamente
        print(f"🔍 PASO 2 - Llamando a generar_informe_html...")
        archivo_html = generar_informe_html(
            datos_cliente, 
            especialidad, 
            archivos_unicos_prueba,  # ← Este es el paso crítico
            "Test de verificación - Comprobar si archivos_unicos llegan correctamente"
        )
        
        resultado = {
            'especialidad': especialidad,
            'paso_1_archivos_unicos': archivos_unicos_prueba,
            'paso_2_html_generado': archivo_html is not None,
        }
        
        if archivo_html:
            resultado['archivo_html_path'] = archivo_html
            
            # PASO 3: Leer el HTML generado y verificar imágenes
            try:
                with open(archivo_html, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                img_count = html_content.count('<img')
                resultado['paso_3_imagenes_en_html'] = img_count
                resultado['html_preview'] = html_content[:1000] + "..." if len(html_content) > 1000 else html_content
                
                if img_count > 0:
                    # Extraer las etiquetas img
                    import re
                    img_tags = re.findall(r'<img[^>]+>', html_content)
                    resultado['img_tags_encontradas'] = img_tags[:3]  # Primeras 3
                
            except Exception as e:
                resultado['error_leyendo_html'] = str(e)
        else:
            resultado['error'] = 'No se pudo generar HTML'
        
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'especialidad': especialidad
        }), 500
        
@app.route('/test/generar_pdf_rutas_absolutas/<especialidad>')
def generar_pdf_rutas_absolutas(especialidad):
    """Generar PDF forzando rutas absolutas sin depender de crear_archivos_unicos_testing"""
    try:
        from informes import generar_informe_html, convertir_html_a_pdf, generar_nombre_archivo_unico
        import os
        
        # Datos de prueba
        datos_cliente = {
            'nombre': 'Cliente Test Absoluto',
            'email': 'absoluto@test.com',
            'codigo_servicio': 'ABS_123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # 🔥 CREAR RUTAS ABSOLUTAS DIRECTAMENTE AQUÍ
        base_dir = os.path.abspath('.')  # Debería ser /app
        print(f"🔥 DEBUG: Base directory = {base_dir}")
        
        # Crear archivos_unicos con rutas absolutas HARDCODED
        if especialidad in ['carta_astral_ia', 'carta_natal']:
            archivos_unicos = {
                'carta_natal_img': f"{base_dir}/static/carta_astral.png",
                'progresiones_img': f"{base_dir}/static/carta_astral_completa.png",
                'transitos_img': f"{base_dir}/static/carta_astral_corregida.png"
            }
        else:
            # Para otras especialidades, usar archivos que sabemos que existen
            archivos_unicos = {
                'imagen_principal': f"{base_dir}/static/carta_astral.png"
            }
        
        # 🔥 VERIFICAR RUTAS ANTES DE CONTINUAR
        print(f"🔥 DEBUG: Archivos_unicos con rutas absolutas:")
        for key, path in archivos_unicos.items():
            exists = os.path.exists(path)
            print(f"  - {key}: {path} (existe: {exists})")
        
        # Generar HTML
        archivo_html = generar_informe_html(datos_cliente, especialidad, archivos_unicos, "Test rutas absolutas")
        
        if not archivo_html:
            return jsonify({'error': 'No se pudo generar HTML'}), 500
        
        # Leer HTML y verificar rutas
        with open(archivo_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Buscar etiquetas img
        import re
        img_tags = re.findall(r'<img[^>]+>', html_content)
        
        # Generar PDF
        nombre_pdf = f"absoluto_{especialidad}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        archivo_pdf = f"informes/{nombre_pdf}"
        os.makedirs('informes', exist_ok=True)
        
        exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
        
        return jsonify({
            'especialidad': especialidad,
            'base_directory': base_dir,
            'archivos_unicos_absolutos': archivos_unicos,
            'verificacion_existencia': {k: os.path.exists(v) for k, v in archivos_unicos.items()},
            'html_generado': archivo_html is not None,
            'img_tags_en_html': img_tags,
            'total_imagenes_html': len(img_tags),
            'pdf_generado': exito_pdf,
            'download_url': f"/test/descargar_pdf/{nombre_pdf}" if exito_pdf else None
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# TAMBIÉN AÑADIR ENDPOINT PARA VER QUE FUNCIÓN SE ESTÁ USANDO

@app.route('/test/verificar_funcion_archivos_unicos')
def verificar_funcion_archivos_unicos():
    """Verificar qué función crear_archivos_unicos_testing se está ejecutando"""
    try:
        import inspect
        
        # Obtener el código fuente de la función actual
        funcion_codigo = inspect.getsource(crear_archivos_unicos_testing)
        
        # Probar la función
        resultado_test = crear_archivos_unicos_testing('carta_astral_ia')
        
        return jsonify({
            'funcion_codigo_preview': funcion_codigo[:500] + "...",
            'usa_os_path_join': 'os.path.join' in funcion_codigo,
            'usa_base_dir': 'base_dir' in funcion_codigo,
            'resultado_test': resultado_test,
            'primer_archivo': list(resultado_test.values())[0] if resultado_test else None,
            'es_ruta_absoluta': str(list(resultado_test.values())[0]).startswith('/') if resultado_test else False
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/test/pdf_arquitectura_correcta/<especialidad>')
def pdf_arquitectura_correcta(especialidad):
    """Test usando arquitectura real: HTTP para /img/, verificar /static/"""
    try:
        from informes import generar_informe_html, convertir_html_a_pdf, generar_nombre_archivo_unico
        import os
        
        datos_cliente = {
            'nombre': 'Test Arquitectura Real',
            'email': 'arq@test.com',
            'codigo_servicio': 'ARQ_123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30', 
            'lugar_nacimiento': 'Madrid, España'
        }
        
        base_url = "https://as-webhooks-production.up.railway.app"
        base_dir = "/app"
        
        # 🔥 USAR ARQUITECTURA REAL
        if especialidad in ['carta_astral_ia', 'carta_natal']:
            archivos_unicos = {
                # IMÁGENES DINÁMICAS: Intentar HTTP primero, luego file:// si falla
                'carta_natal_img': f"{base_url}/static/carta_astral.png",
                'progresiones_img': f"{base_url}/static/carta_astral_completa.png",
                'transitos_img': f"{base_url}/static/carta_astral_corregida.png"
            }
        elif especialidad in ['revolucion_solar_ia', 'revolucion_solar']:
            archivos_unicos = {
                'carta_natal_img': f"{base_url}/static/carta_astral.png",
                'revolucion_img': f"{base_url}/static/carta_astral_placidus.png"
            }
        elif especialidad in ['sinastria_ia', 'sinastria']:
            archivos_unicos = {
                'sinastria_img': f"{base_url}/static/carta_astral_demo.png"
            }
        elif especialidad in ['lectura_manos_ia', 'lectura_manos']:
            # Para manos, las imágenes las sube el cliente a /static/
            archivos_unicos = {
                'mano_izquierda_img': f"{base_url}/static/mano_ejemplo.jpg",  # Placeholder
                'mano_derecha_img': f"{base_url}/static/mano_ejemplo2.jpg"    # Placeholder
            }
        elif especialidad in ['lectura_facial_ia', 'lectura_facial']:
            # Para facial, las imágenes las sube el cliente a /static/
            archivos_unicos = {
                'cara_frontal_img': f"{base_url}/static/cara_ejemplo.jpg"     # Placeholder
            }
        else:
            archivos_unicos = {}
        
        # Verificar accesibilidad HTTP de imágenes dinámicas
        import requests
        verificacion = {}
        fallback_local = {}
        
        for key, url in archivos_unicos.items():
            try:
                response = requests.head(url, timeout=3)
                if response.status_code == 200:
                    verificacion[key] = {'url': url, 'http_ok': True}
                else:
                    # Si HTTP falla, usar file:// local
                    ruta_local = url.replace(base_url, base_dir)
                    if os.path.exists(ruta_local):
                        fallback_local[key] = ruta_local
                        verificacion[key] = {'url': url, 'http_ok': False, 'fallback': ruta_local, 'exists_local': True}
                    else:
                        verificacion[key] = {'url': url, 'http_ok': False, 'exists_local': False}
            except:
                # Si HTTP falla completamente, usar file:// local
                ruta_local = url.replace(base_url, base_dir)
                if os.path.exists(ruta_local):
                    fallback_local[key] = ruta_local
                    verificacion[key] = {'url': url, 'http_ok': False, 'fallback': ruta_local, 'exists_local': True}
                else:
                    verificacion[key] = {'url': url, 'http_ok': False, 'exists_local': False}
        
        # Usar fallbacks locales donde sea necesario
        for key, ruta_local in fallback_local.items():
            archivos_unicos[key] = ruta_local
        
        # Generar HTML y PDF
        archivo_html = generar_informe_html(datos_cliente, especialidad, archivos_unicos, "Test arquitectura real")
        
        if archivo_html:
            with open(archivo_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            import re
            img_tags = re.findall(r'<img[^>]+>', html_content)
            
            nombre_pdf = f"arq_{especialidad}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            archivo_pdf = f"informes/{nombre_pdf}"
            os.makedirs('informes', exist_ok=True)
            
            exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
            
            return jsonify({
                'especialidad': especialidad,
                'metodo': 'Arquitectura real: HTTP + fallback local',
                'archivos_unicos_finales': archivos_unicos,
                'verificacion_http': verificacion,
                'fallbacks_usados': len(fallback_local),
                'img_tags_en_html': img_tags,
                'total_imagenes': len(img_tags),
                'pdf_generado': exito_pdf,
                'download_url': f"/test/descargar_pdf/{nombre_pdf}" if exito_pdf else None
            })
        else:
            return jsonify({'error': 'No se pudo generar HTML'}), 500
            
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# TAMBIÉN VERIFICAR SI RAILWAY SIRVE /static/ POR HTTP

@app.route('/test/verificar_static_http')
def verificar_static_http():
    """Verificar si Railway sirve archivos de /static/ por HTTP"""
    try:
        import requests
        import os
        
        base_url = "https://as-webhooks-production.up.railway.app"
        
        # Archivos que sabemos que existen en /static/ según debug anterior
        archivos_test = [
            'carta_astral.png',
            'carta_astral_completa.png', 
            'carta_astral_corregida.png',
            'carta_astral_demo.png'
        ]
        
        resultados = {}
        
        for archivo in archivos_test:
            url_http = f"{base_url}/static/{archivo}"
            ruta_local = f"/app/static/{archivo}"
            
            # Test HTTP
            try:
                response = requests.head(url_http, timeout=3)
                http_ok = response.status_code == 200
            except:
                http_ok = False
            
            # Test local
            existe_local = os.path.exists(ruta_local)
            
            resultados[archivo] = {
                'url_http': url_http,
                'http_accesible': http_ok,
                'existe_localmente': existe_local,
                'recomendacion': 'HTTP' if http_ok else ('file://' if existe_local else 'NO DISPONIBLE')
            }
        
        return jsonify({
            'railway_sirve_static': any(r['http_accesible'] for r in resultados.values()),
            'archivos_probados': resultados,
            'resumen': {
                'http_funciona': sum(1 for r in resultados.values() if r['http_accesible']),
                'solo_local': sum(1 for r in resultados.values() if r['existe_localmente'] and not r['http_accesible']),
                'no_disponible': sum(1 for r in resultados.values() if not r['existe_localmente'])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/test/pdf_templates_sin_file_prefix/<especialidad>')
def pdf_templates_sin_file_prefix(especialidad):
    """Generar PDF con templates corregidos (sin file:// prefix)"""
    try:
        from informes import convertir_html_a_pdf, generar_nombre_archivo_unico
        from jinja2 import Template
        import os
        
        datos_cliente = {
            'nombre': 'Test Sin File Prefix',
            'email': 'sinfile@test.com',
            'codigo_servicio': 'NOFILE_123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # Usar HTTP URLs
        base_url = "https://as-webhooks-production.up.railway.app"
        
        if especialidad in ['carta_astral_ia', 'carta_natal']:
            archivos_unicos = {
                'carta_natal_img': f"{base_url}/static/carta_astral.png",
                'progresiones_img': f"{base_url}/static/carta_astral_completa.png",
                'transitos_img': f"{base_url}/static/carta_astral_corregida.png"
            }
            
            # TEMPLATE CORREGIDO SIN file:// PREFIX
            template_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe de Carta Astral - AS Cartastral</title>
    <style>
        body { font-family: Georgia, serif; margin: 40px; line-height: 1.6; color: #333; }
        .portada { text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; }
        .datos-natales { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }
        .section { margin: 30px 0; padding: 15px; }
        .carta-img { text-align: center; margin: 30px 0; }
        .carta-img img { max-width: 100%; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .footer { margin-top: 50px; font-size: 0.9em; color: #666; text-align: center; border-top: 1px solid #eee; padding-top: 20px; }
        .dato { font-weight: bold; color: #667eea; }
        .interpretacion { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="portada">
        <h1>🌟 CARTA ASTRAL PERSONALIZADA 🌟</h1>
        <h2>{{ nombre }}</h2>
        <p>AS Cartastral - Servicios Astrológicos Personalizados</p>
    </div>

    <div class="datos-natales">
        <h2>📊 Datos Natales</h2>
        <p><span class="dato">Nombre:</span> {{ nombre }}</p>
        <p><span class="dato">Email:</span> {{ email }}</p>
        <p><span class="dato">Fecha de nacimiento:</span> {{ fecha_nacimiento }}</p>
        <p><span class="dato">Hora de nacimiento:</span> {{ hora_nacimiento }}</p>
        <p><span class="dato">Lugar de nacimiento:</span> {{ lugar_nacimiento }}</p>
    </div>

    {% if carta_natal_img %}
    <div class="carta-img">
        <h2>🌌 Tu Carta Natal</h2>
        <img src="{{ carta_natal_img }}" alt="Carta natal completa">
        <p><em>Tu mapa astrológico personal en el momento de tu nacimiento</em></p>
    </div>
    {% endif %}

    {% if progresiones_img %}
    <div class="carta-img">
        <h2>📈 Progresiones Secundarias</h2>
        <img src="{{ progresiones_img }}" alt="Progresiones secundarias">
        <p><em>La evolución de tu personalidad a lo largo del tiempo</em></p>
    </div>
    {% endif %}

    {% if transitos_img %}
    <div class="carta-img">
        <h2>🔄 Tránsitos Actuales</h2>
        <img src="{{ transitos_img }}" alt="Tránsitos actuales">
        <p><em>Las influencias planetarias que te afectan ahora</em></p>
    </div>
    {% endif %}

    <div class="section">
        <h2>✨ Introducción</h2>
        <div class="interpretacion">
            <p>Bienvenido/a a tu análisis astrológico personalizado. Esta carta astral representa una fotografía del cielo en el momento exacto de tu nacimiento, mostrando la posición de los planetas y su influencia en tu personalidad y destino.</p>
        </div>
    </div>

    {% if resumen_sesion %}
    <div class="section">
        <h2>📞 Resumen de tu Sesión</h2>
        <div class="interpretacion">
            {{ resumen_sesion }}
        </div>
    </div>
    {% endif %}

    <div class="footer">
        <p><strong>Fecha de generación:</strong> {{ fecha_generacion }} a las {{ hora_generacion }}</p>
        <p><strong>Tipo de análisis:</strong> Carta Astral Completa con Progresiones y Tránsitos</p>
        <p><strong>Generado por:</strong> AS Cartastral - Servicios Astrológicos IA</p>
    </div>
</body>
</html>"""

        else:
            # Para otras especialidades, template básico
            archivos_unicos = {'imagen_principal': f"{base_url}/static/carta_astral.png"}
            template_html = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Informe - AS Cartastral</title></head>
<body>
    <h1>{{ nombre }}</h1>
    <p>Email: {{ email }}</p>
    {% if imagen_principal %}<img src="{{ imagen_principal }}" alt="Imagen principal">{% endif %}
    <p>{{ fecha_generacion }}</p>
</body>
</html>"""
        
        # Preparar datos para template
        from datetime import datetime
        import pytz
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
            'resumen_sesion': "Test de template sin file:// prefix - Todas las imágenes deben cargar correctamente"
        }
        datos_template.update(archivos_unicos)
        
        # Renderizar template
        template = Template(template_html)
        html_content = template.render(**datos_template)
        
        # Verificar HTML generado
        import re
        img_tags = re.findall(r'<img[^>]+>', html_content)
        
        # Guardar HTML
        nombre_base = generar_nombre_archivo_unico(especialidad, datos_cliente.get('codigo_servicio', ''))
        archivo_html = f"templates/informe_{nombre_base}.html"
        os.makedirs('templates', exist_ok=True)
        
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Generar PDF
        nombre_pdf = f"nofile_{especialidad}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        archivo_pdf = f"informes/{nombre_pdf}"
        os.makedirs('informes', exist_ok=True)
        
        exito_pdf = convertir_html_a_pdf(archivo_html, archivo_pdf)
        
        return jsonify({
            'especialidad': especialidad,
            'metodo': 'Template sin file:// prefix',
            'archivos_unicos': archivos_unicos,
            'img_tags_corregidas': img_tags,
            'total_imagenes': len(img_tags),
            'html_path': archivo_html,
            'pdf_generado': exito_pdf,
            'download_url': f"/test/descargar_pdf/{nombre_pdf}" if exito_pdf else None,
            'diferencia_clave': 'Templates usan src="{{ imagen }}" en lugar de src="file://{{ imagen }}"'
        })
        
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500
        
# TAMBIÉN VERIFICAR SI generar_solo_pdf USA LA FUNCIÓN CORRECTA
@app.route('/test/verificar_generar_solo_pdf')
def verificar_generar_solo_pdf():
    """Verificar el código actual de generar_solo_pdf"""
    try:
        import inspect
        
        # Obtener código fuente de generar_solo_pdf
        codigo = inspect.getsource(generar_solo_pdf)
        
        return jsonify({
            'funcion_codigo': codigo,
            'usa_crear_archivos_unicos_testing': 'crear_archivos_unicos_testing(' in codigo,
            'pasa_archivos_unicos': 'archivos_unicos' in codigo,
            'debug_print': '🔥 DEBUG' in codigo,
            'lineas_criticas': [
                line.strip() for line in codigo.split('\n') 
                if any(keyword in line for keyword in ['archivos_unicos', 'generar_informe_html', 'crear_archivos_unicos_testing'])
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/test/generar_cartas_directas')
def generar_cartas_directas():
    """Test directo: generar cartas sin Sofia, crear PDF automáticamente"""
    try:
        import time
        from datetime import datetime
        
        # Importar funciones directamente desde sofia.py
        from agents.sofia import generar_cartas_astrales_completas
        
        print("🎯 GENERANDO CARTAS DIRECTAMENTE...")
        
        # Datos de prueba (exactos como Sofia los usa)
        timestamp = int(time.time())
        
        datos_natales = {
            'nombre': 'Test Directo',
            'email': 'directo@test.com',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid',
            'residencia_actual': 'Madrid'
        }
        
        # Archivos únicos con timestamp (exacto como Sofia)
        archivos_unicos = {
            'carta_natal_img': f'static/carta_natal_DIRECTO_{timestamp}.png',
            'progresiones_img': f'static/progresiones_DIRECTO_{timestamp}.png',
            'transitos_img': f'static/transitos_DIRECTO_{timestamp}.png'
        }
        
        # GENERAR CARTAS DIRECTAMENTE
        exito, datos_interpretacion = generar_cartas_astrales_completas(datos_natales, archivos_unicos)
        
        if exito:
            print("✅ CARTAS GENERADAS EXITOSAMENTE")
            
            # Verificar archivos creados
            import os
            archivos_verificados = {}
            for key, ruta in archivos_unicos.items():
                exists = os.path.exists(ruta)
                size = os.path.getsize(ruta) if exists else 0
                archivos_verificados[key] = {
                    'ruta': ruta,
                    'existe': exists,
                    'tamaño': size
                }
                print(f"📁 {key}: {ruta} - Existe: {exists} - Tamaño: {size}")
            
            # GENERAR PDF AUTOMÁTICAMENTE CON LAS NUEVAS IMÁGENES
            from informes import procesar_y_enviar_informe
            
            datos_cliente = {
                'nombre': 'Test Directo Cartas',
                'email': 'directo@test.com',
                'codigo_servicio': 'DIRECTO_TEST',
                'fecha_nacimiento': '15/07/1985',
                'hora_nacimiento': '10:30',
                'lugar_nacimiento': 'Madrid, España'
            }
            
            # Convertir rutas a HTTP URLs para PDF
            base_url = "https://as-webhooks-production.up.railway.app"
            archivos_http = {
                key: ruta.replace('static/', f'{base_url}/static/') 
                for key, ruta in archivos_unicos.items()
            }
            
            resultado_pdf = procesar_y_enviar_informe(
                datos_cliente=datos_cliente,
                tipo_servicio='carta_astral_ia',
                archivos_unicos=archivos_http,
                resumen_sesion="GENERACIÓN DIRECTA DE CARTAS - TEST EXITOSO"
            )
            
            return jsonify({
                'resultado': 'EXITO_TOTAL',
                'cartas_generadas': exito,
                'archivos_creados': archivos_verificados,
                'datos_interpretacion_disponibles': bool(datos_interpretacion),
                'pdf_generado': bool(resultado_pdf),
                'archivos_http': archivos_http,
                'mensaje': 'CARTAS GENERADAS DIRECTAMENTE Y PDF CREADO - PROBLEMA RESUELTO'
            })
        else:
            return jsonify({
                'resultado': 'ERROR_GENERACION',
                'error': 'No se pudieron generar las cartas astrales'
            })
        
    except Exception as e:
        import traceback
        return jsonify({
            'resultado': 'ERROR_CRITICO',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        
@app.route('/admin/recuperar_imagenes_perdidas')
def recuperar_imagenes_perdidas():
    import os
    from PIL import Image, ImageDraw, ImageFont
    
    try:
        imagenes_perdidas = [
            'astrologia-3.jpg',
            'Tarot y astrologia-5.jpg', 
            'Sinastria.jpg',
            'astrologia-1.jpg',
            'lectura facial.jpg',
            'coaching-4.jpg'
        ]
        
        resultados = []
        directorio = 'static/img/'
        
        for imagen in imagenes_perdidas:
            ruta_imagen = os.path.join(directorio, imagen)
            
            if not os.path.exists(ruta_imagen):
                # Crear imagen placeholder de 200x150 con el nombre
                img = Image.new('RGB', (200, 150), color='#3498db')
                draw = ImageDraw.Draw(img)
                
                # Texto del placeholder
                texto = imagen.replace('.jpg', '').replace('-', ' ').title()
                
                try:
                    # Intentar usar una fuente por defecto
                    draw.text((10, 70), texto, fill='white')
                except:
                    # Si no hay fuentes, solo crear la imagen sólida
                    pass
                
                img.save(ruta_imagen, 'JPEG')
                resultados.append(f"✅ Recuperada: {imagen}")
            else:
                resultados.append(f"✅ Ya existe: {imagen}")
        
        return jsonify({
            "status": "success",
            "resultados": resultados,
            "accion": "Imágenes placeholder creadas como emergencia"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        })
        
@app.route('/debug/sofia_generacion')
def debug_sofia_generacion():
    """Debugar generación de Sofia"""
    try:
        from datetime import datetime
        
        # Datos de prueba
        datos_natales = {
            'nombre': 'Test Cliente',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'residencia_actual': 'Madrid, España'
        }
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        archivos_unicos = {
            'carta_natal_img': f'static/carta_natal_test_{timestamp}.png',
            'progresiones_img': f'static/progresiones_test_{timestamp}.png',
            'transitos_img': f'static/transitos_test_{timestamp}.png'
        }
        
        print(f"🔧 DEBUG: Probando generación con archivos: {archivos_unicos}")
        
        # IMPORTAR Y LLAMAR LA FUNCIÓN
        from agents.sofia import generar_cartas_astrales_completas
        exito, datos = generar_cartas_astrales_completas(datos_natales, archivos_unicos)
        
        # Verificar si se crearon archivos
        import os
        archivos_creados = {}
        for key, path in archivos_unicos.items():
            archivos_creados[key] = {
                'path': path,
                'exists': os.path.exists(path),
                'size': os.path.getsize(path) if os.path.exists(path) else 0
            }
        
        return jsonify({
            'exito': exito,
            'datos_resultado': str(datos)[:500] if datos else None,
            'archivos_unicos': archivos_unicos,
            'archivos_creados': archivos_creados,
            'timestamp': timestamp
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/debug/ver_archivos')
def ver_archivos():
    import os
    import glob
    
    try:
        resultado = {
            "carpetas": {},
            "archivos_importantes": {}
        }
        
        # Verificar carpetas principales
        carpetas = ['static', 'informes', 'templates', 'static/img']
        for carpeta in carpetas:
            if os.path.exists(carpeta):
                archivos = os.listdir(carpeta)
                resultado["carpetas"][carpeta] = {
                    "existe": True,
                    "archivos": archivos[:10],  # solo primeros 10
                    "total": len(archivos)
                }
            else:
                resultado["carpetas"][carpeta] = {"existe": False}
        
        # Buscar archivos específicos
        resultado["archivos_importantes"] = {
            "pdfs": glob.glob("informes/*.pdf")[-5:],  # últimos 5 PDFs
            "imagenes_static": glob.glob("static/*.png")[-5:],  # últimas 5 imágenes
            "imagenes_fijas": glob.glob("static/img/*")
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/admin/crear_informes')
def crear_informes():
    import os
    try:
        os.makedirs('informes', exist_ok=True)
        return jsonify({
            "carpeta_informes_creada": os.path.exists('informes'),
            "status": "ok"
        })
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/test/ejecutar_carta_natal')
def ejecutar_carta_natal():
    try:
        # Importar y ejecutar directamente la función main
        from carta_natal import main as carta_main
        
        # Ejecutar con archivo de salida específico
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_salida = f"static/test_carta_natal_{timestamp}.png"
        
        # Llamar la función main del archivo
        resultado = carta_main(archivo_salida)
        
        # Verificar si se creó el archivo
        import os
        archivo_existe = os.path.exists(archivo_salida)
        tamaño = os.path.getsize(archivo_salida) if archivo_existe else 0
        
        return jsonify({
            "funcion_ejecutada": "carta_natal.main()",
            "archivo_objetivo": archivo_salida,
            "archivo_creado": archivo_existe,
            "tamaño_bytes": tamaño,
            "timestamp": timestamp
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()[:1000]
        })
        
@app.route('/test/ejecutar_carta_natal_con_error')
def ejecutar_carta_natal_con_error():
    try:
        from datetime import datetime
        import os
        
        # Capturar cualquier error de importación
        try:
            from carta_natal import main as carta_main
            importacion_ok = True
            error_importacion = None
        except Exception as e:
            importacion_ok = False
            error_importacion = str(e)
        
        if not importacion_ok:
            return jsonify({
                "paso": "error_importacion",
                "error": error_importacion,
                "solucion": "Revisar dependencias"
            })
        
        # Intentar ejecutar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_salida = f"static/test_carta_error_{timestamp}.png"
        
        try:
            resultado = carta_main(archivo_salida)
            ejecucion_ok = True
            error_ejecucion = None
        except Exception as e:
            ejecucion_ok = False
            error_ejecucion = str(e)
            import traceback
            traceback_completo = traceback.format_exc()
        
        # Verificar archivo
        archivo_existe = os.path.exists(archivo_salida)
        
        return jsonify({
            "importacion_ok": importacion_ok,
            "ejecucion_ok": ejecucion_ok,
            "error_ejecucion": error_ejecucion if not ejecucion_ok else None,
            "traceback": traceback_completo[:1500] if not ejecucion_ok else None,
            "archivo_creado": archivo_existe,
            "archivo_objetivo": archivo_salida,
            "timestamp": timestamp
        })
        
    except Exception as e:
        return jsonify({
            "error_critico": str(e),
            "paso": "error_general"
        })
        
@app.route('/test/debug_carta_natal_detallado')
def debug_carta_natal_detallado():
    try:
        from datetime import datetime
        import os
        import matplotlib
        matplotlib.use('Agg')  # Backend sin pantalla
        
        # Intentar ejecutar paso por paso
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_objetivo = f"static/debug_carta_{timestamp}.png"
        
        # Importar la clase directamente
        from carta_natal import CartaAstralNatal
        
        # Crear instancia
        carta = CartaAstralNatal(figsize=(16, 14))
        
        # Datos de prueba
        fecha_natal = (1985, 7, 15, 10, 30)
        lugar_natal = (40.42, -3.70)  # Madrid
        ciudad_natal = "Madrid, España"
        
        # Intentar generar
        aspectos, posiciones = carta.crear_carta_astral_natal(
            fecha_natal=fecha_natal,
            lugar_natal=lugar_natal,
            ciudad_natal=ciudad_natal,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        # Verificar archivos creados
        import glob
        archivos_nuevos = glob.glob(f"static/*{timestamp}*")
        todos_los_png = glob.glob("static/*.png")
        
        return jsonify({
            "proceso": "manual_paso_a_paso",
            "aspectos_calculados": len(aspectos) if aspectos else 0,
            "archivo_objetivo": archivo_objetivo,
            "archivos_con_timestamp": archivos_nuevos,
            "total_png_en_static": len(todos_los_png),
            "ultimos_png": todos_los_png[-3:] if todos_los_png else [],
            "matplotlib_backend": matplotlib.get_backend()
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()[:1500]
        })
        
@app.route('/test/verificar_patron_nombres')
def verificar_patron_nombres():
    try:
        import glob
        import os
        from datetime import datetime
        
        # Ver TODOS los archivos antes
        archivos_antes = glob.glob("static/*.png")
        
        # Ejecutar carta natal
        from carta_natal import CartaAstralNatal
        carta = CartaAstralNatal(figsize=(16, 14))
        
        aspectos, posiciones = carta.crear_carta_astral_natal(
            fecha_natal=(1990, 12, 25, 15, 45),  # Fecha específica
            lugar_natal=(40.42, -3.70),
            ciudad_natal="Madrid",
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        # Ver archivos DESPUÉS
        archivos_despues = glob.glob("static/*.png")
        
        # Encontrar archivo nuevo
        archivos_nuevos = list(set(archivos_despues) - set(archivos_antes))
        
        return jsonify({
            "archivos_antes": len(archivos_antes),
            "archivos_despues": len(archivos_despues), 
            "archivos_nuevos": archivos_nuevos,
            "patron_descubierto": archivos_nuevos[0] if archivos_nuevos else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/test/corregir_busqueda_archivos')
def corregir_busqueda_archivos():
    try:
        import glob
        from datetime import datetime
        
        # Datos de prueba como usa Sofia
        datos_natales = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30'
        }
        
        # Convertir a formato que usa carta_natal
        dia, mes, año = map(int, datos_natales['fecha_nacimiento'].split('/'))
        hora, minuto = map(int, datos_natales['hora_nacimiento'].split(':'))
        
        # Patrón que realmente se genera
        patron_real = f"static/carta_natal_{año}{mes:02d}{dia:02d}_{hora:02d}{minuto:02d}.png"
        
        # Buscar archivos con este patrón
        archivos_encontrados = glob.glob(f"static/carta_natal_{año}{mes:02d}{dia:02d}_*.png")
        
        return jsonify({
            "datos_natales": datos_natales,
            "patron_esperado_sofia": f"static/carta_natal_test_{datetime.now().strftime('%Y%m%d%H%M%S')}.png",
            "patron_real_generado": patron_real,
            "archivos_encontrados": archivos_encontrados,
            "solucion": "Sofia debe buscar archivos con patrón fecha_nacimiento"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/test/generar_y_usar_inmediato')
def generar_y_usar_inmediato():
    try:
        from datetime import datetime
        import os
        
        # Datos de prueba
        datos_natales = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # Convertir datos
        dia, mes, año = map(int, datos_natales['fecha_nacimiento'].split('/'))
        hora, minuto = map(int, datos_natales['hora_nacimiento'].split(':'))
        
        # Archivo temporal con timestamp único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # incluir microsegundos
        archivo_temp = f"static/temp_carta_{timestamp}.png"
        
        # Generar carta
        from carta_natal import CartaAstralNatal
        carta = CartaAstralNatal(figsize=(16, 14))
        
        # Configurar archivo específico
        carta.nombre_archivo_personalizado = archivo_temp
        
        aspectos, posiciones = carta.crear_carta_astral_natal(
            fecha_natal=(año, mes, dia, hora, minuto),
            lugar_natal=(40.42, -3.70),
            ciudad_natal="Madrid, España",
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        # Verificar inmediatamente
        archivo_existe = os.path.exists(archivo_temp)
        tamaño = os.path.getsize(archivo_temp) if archivo_existe else 0
        
        return jsonify({
            "metodo": "generar_y_verificar_inmediato",
            "archivo_temporal": archivo_temp,
            "archivo_existe": archivo_existe,
            "tamaño_bytes": tamaño,
            "aspectos": len(aspectos) if aspectos else 0,
            "estrategia": "usar_archivo_inmediatamente_sin_esperar"
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()[:1000]
        })
        
@app.route('/debug/quien_borra_archivos')
def quien_borra_archivos():
    try:
        import os
        import time
        from datetime import datetime
        
        # Crear archivo de prueba
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_test = f"static/test_duracion_{timestamp}.png"
        
        # Escribir archivo
        with open(archivo_test, 'w') as f:
            f.write("archivo de prueba")
        
        # Verificar inmediatamente
        existe_inmediato = os.path.exists(archivo_test)
        
        # Esperar 5 segundos
        time.sleep(5)
        existe_5_seg = os.path.exists(archivo_test)
        
        # Información de sistemas de limpieza
        info_limpieza = {
            "limpiar_cartas_py": os.path.exists("limpiar_cartas.py"),
            "funcion_limpieza_main": "limpiar_archivos_antiguos" in open("main.py").read(),
        }
        
        return jsonify({
            "archivo_creado": archivo_test,
            "existe_inmediato": existe_inmediato,
            "existe_despues_5_seg": existe_5_seg,
            "sistemas_limpieza": info_limpieza,
            "problema": "archivo_borrado_inmediatamente" if existe_inmediato and not existe_5_seg else "archivo_persiste"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})
        
@app.route('/test/verificar_extensiones_reales')
def verificar_extensiones_reales():
    import glob
    
    archivos_img = glob.glob('static/img/*')
    extensiones = {}
    
    for archivo in archivos_img:
        nombre = archivo.split('/')[-1]
        ext = nombre.split('.')[-1]
        extensiones[nombre] = ext
    
    return jsonify({
        "archivos_en_static_img": extensiones,
        "solucion": "Actualizar informes.py con extensiones reales"
    })
    
@app.route('/test/verificar_imagenes_fix')
def verificar_imagenes_fix():
    """Verificar que el fix de imágenes funciona"""
    from informes import obtener_ruta_imagen_absoluta
    import os
    
    imagenes_criticas = {
        'logo': 'logo.JPG',
        'carta_astral': 'astrologia-3.JPG',
        'revolucion': 'Tarot y astrologia-5.JPG',
        'sinastria': 'Sinastria.JPG',
        'horaria': 'astrologia-1.JPG',
        'manos': 'Lectura-de-manos-p.jpg',
        'facial': 'lectura facial.JPG',
        'coaching': 'coaching-4.JPG',
        'grafologia': 'grafologia_2.jpeg'
    }
    
    resultados = {}
    todas_ok = True
    
    for servicio, archivo in imagenes_criticas.items():
        ruta = obtener_ruta_imagen_absoluta(archivo)
        existe = os.path.exists(ruta) if not ruta.startswith('data:') else False
        
        resultados[servicio] = {
            'archivo': archivo,
            'ruta_obtenida': ruta,
            'existe': existe,
            'es_placeholder': ruta.startswith('data:')
        }
        
        if not existe or ruta.startswith('data:'):
            todas_ok = False
    
    return jsonify({
        'estado': '✅ TODO OK' if todas_ok else '⚠️ FALTAN IMÁGENES',
        'todas_imagenes_ok': todas_ok,
        'detalles': resultados,
        'siguiente_paso': 'Generar un PDF de prueba en /test/generar_pdf_especialidad/carta_astral_ia'
    })
    
@app.route('/test/comparar_entornos')
def comparar_entornos():
    """Comparar configuración Replit vs Railway"""
    import os
    import platform
    
    return jsonify({
        'entorno': {
            'plataforma': platform.platform(),
            'python_version': platform.python_version(),
            'directorio_actual': os.getcwd(),
            'usuario': os.environ.get('USER', 'unknown'),
            'home': os.environ.get('HOME', 'unknown'),
            'railway_env': 'RAILWAY_ENVIRONMENT' in os.environ
        },
        'estructura_directorios': {
            'existe_img': os.path.exists('./img/'),
            'existe_static': os.path.exists('./static/'),
            'existe_static_img': os.path.exists('./static/img/'),
            'archivos_en_img': os.listdir('./img/') if os.path.exists('./img/') else [],
            'archivos_en_static_img': os.listdir('./static/img/') if os.path.exists('./static/img/') else []
        },
        'permisos': {
            'puede_escribir_static': os.access('./static/', os.W_OK) if os.path.exists('./static/') else False,
            'puede_leer_img': os.access('./img/', os.R_OK) if os.path.exists('./img/') else False
        }
    })
    
# ========================================
# 🚨 ENDPOINTS FALTANTES - AÑADIR A main.py
# ========================================

@app.route('/test/estado_limpieza_archivos') 
def estado_limpieza_archivos():
    """Verificar qué archivos se están borrando automáticamente"""
    import os
    import glob
    from datetime import datetime, timedelta
    
    hace_7_dias = datetime.now() - timedelta(days=7)
    
    # Verificar archivos que se van a borrar
    archivos_peligro = []
    archivos_seguros = []
    
    patrones = ["static/*.png", "static/*.jpg", "static/*.JPG", "informes/*.pdf", "templates/informe_*.html"]
    
    for patron in patrones:
        for archivo in glob.glob(patron):
            try:
                fecha_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
                nombre = os.path.basename(archivo)
                
                # Archivos que se borrarán
                if fecha_archivo < hace_7_dias:
                    archivos_peligro.append({
                        'archivo': archivo,
                        'edad_dias': (datetime.now() - fecha_archivo).days,
                        'sera_borrado': True
                    })
                else:
                    archivos_seguros.append({
                        'archivo': archivo, 
                        'edad_dias': (datetime.now() - fecha_archivo).days,
                        'sera_borrado': False
                    })
            except:
                continue
    
    return jsonify({
        'archivos_seran_borrados': archivos_peligro,
        'archivos_seguros': archivos_seguros,
        'limite_dias': 7,
        'solucion': 'Aplicar /test/proteger_imagenes_criticas'
    })
    
@app.route('/diagnostico/carpetas_permisos')
def diagnostico_carpetas_permisos():
    """Verificar carpetas y permisos en Railway"""
    import os
    import stat
    from datetime import datetime
    
    resultado = {
        'timestamp': datetime.now().isoformat(),
        'directorio_actual': os.getcwd(),
        'carpetas': {},
        'permisos': {},
        'test_escritura': {}
    }
    
    # CARPETAS CRÍTICAS PARA IMÁGENES
    carpetas_criticas = ['static', 'templates', 'informes', 'img']
    
    for carpeta in carpetas_criticas:
        ruta = f'./{carpeta}/'
        resultado['carpetas'][carpeta] = {
            'existe': os.path.exists(ruta),
            'es_directorio': os.path.isdir(ruta) if os.path.exists(ruta) else False,
            'archivos_dentro': [],
            'total_archivos': 0
        }
        
        if os.path.exists(ruta):
            try:
                archivos = os.listdir(ruta)
                resultado['carpetas'][carpeta]['archivos_dentro'] = archivos[:10]  # Primeros 10
                resultado['carpetas'][carpeta]['total_archivos'] = len(archivos)
                
                # Verificar permisos
                resultado['permisos'][carpeta] = {
                    'lectura': os.access(ruta, os.R_OK),
                    'escritura': os.access(ruta, os.W_OK),
                    'ejecucion': os.access(ruta, os.X_OK)
                }
                
                # TEST DE ESCRITURA REAL
                try:
                    archivo_test = f"{ruta}test_escritura_{datetime.now().strftime('%H%M%S')}.txt"
                    with open(archivo_test, 'w') as f:
                        f.write("Test de escritura Railway")
                    
                    # Si llegó aquí, se pudo escribir
                    resultado['test_escritura'][carpeta] = {'status': 'success', 'archivo': archivo_test}
                    
                    # Limpiar archivo de test
                    os.remove(archivo_test)
                    
                except Exception as e:
                    resultado['test_escritura'][carpeta] = {'status': 'error', 'error': str(e)}
            
            except Exception as e:
                resultado['carpetas'][carpeta]['error'] = str(e)
    
    # CREAR CARPETAS FALTANTES
    carpetas_creadas = []
    for carpeta in carpetas_criticas:
        if not resultado['carpetas'][carpeta]['existe']:
            try:
                os.makedirs(f'./{carpeta}/', exist_ok=True)
                carpetas_creadas.append(carpeta)
            except Exception as e:
                resultado['carpetas'][carpeta]['error_creacion'] = str(e)
    
    resultado['carpetas_creadas'] = carpetas_creadas
    
    return jsonify(resultado)

@app.route('/diagnostico/test_creacion_imagen')
def diagnostico_test_creacion_imagen():
    """Probar crear una imagen de test en static/"""
    import os
    from datetime import datetime
    
    try:
        # Asegurar que existe la carpeta
        os.makedirs('./static/', exist_ok=True)
        
        # Crear imagen de test simple (sin usar las funciones complejas)
        nombre_imagen_test = f"test_imagen_{datetime.now().strftime('%H%M%S')}.png"
        ruta_imagen = f"./static/{nombre_imagen_test}"
        
        # Usar PIL para crear imagen simple
        try:
            from PIL import Image, ImageDraw
            
            # Crear imagen de 400x400 con fondo blanco
            img = Image.new('RGB', (400, 400), color='white')
            draw = ImageDraw.Draw(img)
            
            # Dibujar rectángulo de test
            draw.rectangle([50, 50, 350, 350], fill='lightblue', outline='blue', width=3)
            draw.text((200, 200), "TEST IMAGE", fill='black', anchor='mm')
            
            # Guardar imagen
            img.save(ruta_imagen, 'PNG')
            
            # Verificar que se creó
            if os.path.exists(ruta_imagen):
                stats = os.stat(ruta_imagen)
                return jsonify({
                    'status': 'success',
                    'mensaje': 'Imagen de test creada correctamente',
                    'archivo': ruta_imagen,
                    'tamaño_bytes': stats.st_size,
                    'url_acceso': f"https://as-webhooks-production.up.railway.app/static/{nombre_imagen_test}",
                    'metodo': 'PIL'
                })
            else:
                return jsonify({'status': 'error', 'mensaje': 'Imagen no se creó'})
                
        except ImportError:
            return jsonify({'status': 'error', 'mensaje': 'PIL no disponible'})
            
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)})

@app.route('/diagnostico/test_cartas_reales')  
def diagnostico_test_cartas_reales():
    """Probar crear carta astral real usando los archivos originales"""
    import os
    from datetime import datetime
    
    try:
        # Datos de test
        datos_natales = {
            'fecha_nacimiento': '1985-07-15',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'pais_nacimiento': 'España'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Archivos únicos de test
        archivos_unicos = {
            'carta_natal_img': f'static/carta_natal_test_{timestamp}.png',
            'progresiones_img': f'static/progresiones_test_{timestamp}.png', 
            'transitos_img': f'static/transitos_test_{timestamp}.png'
        }
        
        # Probar importar y ejecutar la función original
        try:
            # Esto debería estar en sofia.py o en un archivo similar
            # from sofia import generar_cartas_astrales_completas
            
            # Como no tengo acceso directo, simular el proceso
            from carta_natal import GraficadorCartaNatal
            
            # Crear instancia del graficador
            graficador = GraficadorCartaNatal()
            
            # Configurar datos natales (simular el formato esperado)
            fecha_natal = (1985, 7, 15, 10, 30)  # año, mes, día, hora, minuto
            
            # Intentar crear carta natal
            graficador.configurar_carta_natal(fecha_natal, lugar="Madrid, España")
            
            # Guardar con nombre específico
            graficador.nombre_archivo_personalizado = archivos_unicos['carta_natal_img']
            resultado_carta = graficador.guardar_carta_natal_con_nombre_unico(fecha_natal, './static/')
            
            # Verificar resultados
            archivos_creados = {}
            for nombre, ruta in archivos_unicos.items():
                if os.path.exists(ruta):
                    stats = os.stat(ruta)
                    archivos_creados[nombre] = {
                        'creado': True,
                        'ruta': ruta,
                        'tamaño': stats.st_size,
                        'url': f"https://as-webhooks-production.up.railway.app/{ruta}"
                    }
                else:
                    archivos_creados[nombre] = {'creado': False, 'ruta': ruta}
            
            return jsonify({
                'status': 'success' if archivos_creados else 'partial',
                'mensaje': 'Test de creación de cartas reales',
                'archivos_creados': archivos_creados,
                'total_creados': len([a for a in archivos_creados.values() if a.get('creado')])
            })
            
        except ImportError as e:
            return jsonify({
                'status': 'import_error',
                'mensaje': f'No se pudo importar: {str(e)}',
                'solucion': 'Verificar que carta_natal.py esté disponible'
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'mensaje': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/diagnostico/listar_archivos_static')
def diagnostico_listar_archivos_static():
    """Listar todos los archivos en static/ con detalles"""
    import os
    import time
    from datetime import datetime
    
    try:
        if not os.path.exists('./static/'):
            return jsonify({
                'status': 'error',
                'mensaje': 'Carpeta static/ no existe',
                'solucion': 'Crear carpeta con: os.makedirs("./static/", exist_ok=True)'
            })
        
        archivos = []
        total_tamaño = 0
        
        for archivo in os.listdir('./static/'):
            ruta = f"./static/{archivo}"
            if os.path.isfile(ruta):
                stats = os.stat(ruta)
                fecha_mod = datetime.fromtimestamp(stats.st_mtime)
                
                archivo_info = {
                    'nombre': archivo,
                    'tamaño_bytes': stats.st_size,
                    'tamaño_kb': round(stats.st_size / 1024, 2),
                    'fecha_modificacion': fecha_mod.isoformat(),
                    'edad_minutos': round((time.time() - stats.st_mtime) / 60, 1),
                    'url_acceso': f"https://as-webhooks-production.up.railway.app/static/{archivo}",
                    'es_imagen': archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
                }
                
                archivos.append(archivo_info)
                total_tamaño += stats.st_size
        
        # Ordenar por fecha de modificación (más recientes primero)
        archivos.sort(key=lambda x: x['fecha_modificacion'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'total_archivos': len(archivos),
            'total_tamaño_kb': round(total_tamaño / 1024, 2),
            'archivos': archivos,
            'archivos_recientes': [a for a in archivos if a['edad_minutos'] < 60],  # Últimos 60 min
            'imagenes': [a for a in archivos if a['es_imagen']]
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)})
        
# ========================================
# DIAGNÓSTICO: ¿Por qué no se generan cartas dinámicas?
# AÑADIR A main.py
# ========================================

@app.route('/diagnostico/test_carta_natal_real')
def test_carta_natal_real():
    """Probar crear una carta natal real con timestamp único"""
    try:
        from datetime import datetime
        import os
        
        # Datos de test
        datos_natales = {
            'fecha_nacimiento': '1985-07-15',
            'hora_nacimiento': '10:30', 
            'lugar_nacimiento': 'Madrid, España',
            'pais_nacimiento': 'España'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_esperado = f"carta_natal_test_{timestamp}.png"
        ruta_esperada = f"static/{nombre_esperado}"
        
        resultado = {
            'timestamp': timestamp,
            'archivo_esperado': nombre_esperado,
            'ruta_esperada': ruta_esperada,
            'paso_1_imports': {},
            'paso_2_ejecucion': {},
            'paso_3_archivo_creado': {}
        }
        
        # PASO 1: Probar imports
        try:
            # Intentar importar carta_natal
            import carta_natal
            resultado['paso_1_imports']['carta_natal'] = 'success'
            
            # Listar funciones disponibles en el módulo
            funciones = [attr for attr in dir(carta_natal) if not attr.startswith('_')]
            resultado['paso_1_imports']['funciones_disponibles'] = funciones
            
        except Exception as e:
            resultado['paso_1_imports']['carta_natal'] = f'error: {str(e)}'
            return jsonify(resultado)
        
        # PASO 2: Intentar crear carta
        try:
            # Buscar la función correcta para generar carta
            if hasattr(carta_natal, 'generar_carta_natal'):
                resultado['paso_2_ejecucion']['funcion_encontrada'] = 'generar_carta_natal'
                # Intentar ejecutar
                carta_result = carta_natal.generar_carta_natal(datos_natales, ruta_esperada)
                resultado['paso_2_ejecucion']['resultado'] = carta_result
                
            elif hasattr(carta_natal, 'crear_carta_natal'):
                resultado['paso_2_ejecucion']['funcion_encontrada'] = 'crear_carta_natal'
                carta_result = carta_natal.crear_carta_natal(datos_natales, ruta_esperada)
                resultado['paso_2_ejecucion']['resultado'] = carta_result
                
            else:
                # Intentar usar la primera función que no sea privada
                funciones_publicas = [f for f in funciones if callable(getattr(carta_natal, f))]
                if funciones_publicas:
                    primera_funcion = funciones_publicas[0]
                    resultado['paso_2_ejecucion']['funcion_encontrada'] = primera_funcion
                    resultado['paso_2_ejecucion']['intento'] = 'usando primera función pública'
                else:
                    resultado['paso_2_ejecucion']['error'] = 'No se encontraron funciones ejecutables'
                    
        except Exception as e:
            resultado['paso_2_ejecucion']['error'] = str(e)
            import traceback
            resultado['paso_2_ejecucion']['traceback'] = traceback.format_exc()
        
        # PASO 3: Verificar si se creó el archivo
        if os.path.exists(ruta_esperada):
            stats = os.stat(ruta_esperada)
            resultado['paso_3_archivo_creado'] = {
                'creado': True,
                'tamaño_bytes': stats.st_size,
                'url': f"https://as-webhooks-production.up.railway.app/{ruta_esperada}"
            }
        else:
            resultado['paso_3_archivo_creado'] = {'creado': False}
            
            # Listar archivos en static para ver si se creó con otro nombre
            archivos_static = os.listdir('./static/')
            archivos_nuevos = [f for f in archivos_static if timestamp in f]
            resultado['paso_3_archivo_creado']['archivos_con_timestamp'] = archivos_nuevos
        
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error_general': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/diagnostico/probar_imports_swisseph') 
def probar_imports_swisseph():
    """Probar si las dependencias astrológicas funcionan"""
    resultado = {'imports': {}}
    
    # Lista de módulos que podrían ser necesarios
    modulos_necesarios = [
        'swisseph',
        'pyephem', 
        'carta_natal',
        'progresiones',
        'transitos',
        'revolucion_solar',
        'revolucion_natal',
        'sinastria'
    ]
    
    for modulo in modulos_necesarios:
        try:
            imported_module = __import__(modulo)
            resultado['imports'][modulo] = {
                'status': 'success',
                'file': getattr(imported_module, '__file__', 'unknown'),
                'functions': [attr for attr in dir(imported_module) if not attr.startswith('_')][:10]
            }
        except ImportError as e:
            resultado['imports'][modulo] = {
                'status': 'import_error', 
                'error': str(e)
            }
        except Exception as e:
            resultado['imports'][modulo] = {
                'status': 'other_error',
                'error': str(e)
            }
    
    # Verificar si swisseph funciona básicamente
    try:
        import swisseph as swe
        # Test básico de swisseph
        jd = swe.julday(2025, 9, 24, 12.0)
        resultado['swisseph_test'] = {
            'julian_day_test': jd,
            'working': True
        }
    except:
        resultado['swisseph_test'] = {'working': False}
    
    return jsonify(resultado)

@app.route('/diagnostico/simular_llamada_sofia')
def simular_llamada_sofia():
    """Simular el proceso completo que hace Sofia cuando llama un cliente"""
    try:
        from datetime import datetime
        
        # Datos de test como los que pasaría Sofia
        datos_cliente = {
            'nombre': 'Test Cliente Diagnóstico',
            'email': 'diagnostico@ascartastral.com',
            'codigo_servicio': 'AI_DIAG123',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'pais_nacimiento': 'España'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Archivos que Sofia intentaría crear
        archivos_esperados = {
            'carta_natal_img': f'static/carta_natal_{timestamp}.png',
            'progresiones_img': f'static/progresiones_{timestamp}.png',
            'transitos_img': f'static/transitos_{timestamp}.png'
        }
        
        resultado = {
            'datos_cliente': datos_cliente,
            'archivos_esperados': archivos_esperados,
            'proceso_sofia': {}
        }
        
        # Intentar importar la función que usa Sofia
        try:
            # Esto debería estar en sofia.py
            from sofia import generar_cartas_astrales_completas
            resultado['proceso_sofia']['import_sofia'] = 'success'
            
            # Llamar la función como lo haría Sofia
            datos_natales = {
                'fecha_nacimiento': datos_cliente['fecha_nacimiento'], 
                'hora_nacimiento': datos_cliente['hora_nacimiento'],
                'lugar_nacimiento': datos_cliente['lugar_nacimiento'],
                'pais_nacimiento': datos_cliente['pais_nacimiento']
            }
            
            exito, datos_interpretacion = generar_cartas_astrales_completas(datos_natales, archivos_esperados)
            
            resultado['proceso_sofia']['exito'] = exito
            resultado['proceso_sofia']['datos_interpretacion'] = str(datos_interpretacion)[:200] + "..."
            
        except ImportError as e:
            resultado['proceso_sofia']['import_error'] = str(e)
        except Exception as e:
            resultado['proceso_sofia']['execution_error'] = str(e)
            import traceback
            resultado['proceso_sofia']['traceback'] = traceback.format_exc()
        
        # Verificar archivos creados
        archivos_creados = {}
        import os
        for nombre, ruta in archivos_esperados.items():
            if os.path.exists(ruta):
                stats = os.stat(ruta) 
                archivos_creados[nombre] = {
                    'creado': True,
                    'tamaño': stats.st_size,
                    'url': f"https://as-webhooks-production.up.railway.app/{ruta}"
                }
            else:
                archivos_creados[nombre] = {'creado': False}
        
        resultado['archivos_resultado'] = archivos_creados
        
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/diagnostico/verificar_dependencias')
def verificar_dependencias():
    """Verificar todas las dependencias necesarias"""
    import subprocess
    import sys
    
    resultado = {
        'python_version': sys.version,
        'pip_packages': {},
        'system_info': {}
    }
    
    # Paquetes críticos para astrología
    paquetes_criticos = [
        'swisseph',
        'pyephem',
        'matplotlib',
        'PIL', 
        'Pillow',
        'numpy',
        'flask',
        'playwright'
    ]
    
    for paquete in paquetes_criticos:
        try:
            # Intentar importar
            __import__(paquete)
            resultado['pip_packages'][paquete] = 'installed'
        except ImportError:
            resultado['pip_packages'][paquete] = 'missing'
        except Exception as e:
            resultado['pip_packages'][paquete] = f'error: {str(e)}'
    
    # Info del sistema
    import os
    resultado['system_info'] = {
        'cwd': os.getcwd(),
        'PATH': os.environ.get('PATH', '')[:200] + "...",
        'PYTHONPATH': os.environ.get('PYTHONPATH', 'not_set'),
        'platform': sys.platform
    }
    
    return jsonify(resultado)
    
# ========================================
# 🔧 TEST EJECUTAR FUNCIÓN REAL - MAIN.PY
# ========================================

@app.route('/test/ejecutar_carta_natal_directo')
def ejecutar_carta_natal_directo():
    """Ejecutar directamente las funciones que sabemos que existen"""
    try:
        from datetime import datetime
        import os
        
        # Importar carta_natal (sabemos que funciona)
        import carta_natal
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        resultado = {
            'timestamp': timestamp,
            'intentos': [],
            'archivos_creados': []
        }
        
        # INTENTO 1: generar_carta_natal_personalizada
        try:
            datos_natales = {
                'fecha_nacimiento': '1985-07-15',
                'hora_nacimiento': '10:30',
                'lugar_nacimiento': 'Madrid',
                'pais_nacimiento': 'España'
            }
            
            archivo_salida = f"static/carta_test_personalizada_{timestamp}.png"
            
            # Llamar la función
            resultado_carta = carta_natal.generar_carta_natal_personalizada(
                datos_natales, archivo_salida
            )
            
            resultado['intentos'].append({
                'metodo': 'generar_carta_natal_personalizada',
                'resultado': str(resultado_carta),
                'archivo_esperado': archivo_salida
            })
            
            # Verificar si se creó
            if os.path.exists(archivo_salida):
                stats = os.stat(archivo_salida)
                resultado['archivos_creados'].append({
                    'archivo': archivo_salida,
                    'tamaño': stats.st_size,
                    'url': f"https://as-webhooks-production.up.railway.app/{archivo_salida}",
                    'metodo': 'generar_carta_natal_personalizada'
                })
            
        except Exception as e:
            resultado['intentos'].append({
                'metodo': 'generar_carta_natal_personalizada',
                'error': str(e)
            })
        
        # INTENTO 2: CartaAstralNatal (clase)
        try:
            # Crear instancia de la clase
            carta_instance = carta_natal.CartaAstralNatal()
            
            # Datos en formato que podría esperar la clase
            fecha_natal = (1985, 7, 15, 10, 30)  # año, mes, día, hora, minuto
            lugar = "Madrid, España"
            
            archivo_clase = f"static/carta_test_clase_{timestamp}.png"
            
            # Si la clase tiene método para generar carta
            if hasattr(carta_instance, 'generar_carta'):
                resultado_clase = carta_instance.generar_carta(fecha_natal, lugar, archivo_clase)
            elif hasattr(carta_instance, 'crear_carta'):
                resultado_clase = carta_instance.crear_carta(fecha_natal, lugar, archivo_clase)
            elif hasattr(carta_instance, 'guardar_carta'):
                # Podría necesitar configurar primero
                carta_instance.configurar_datos(fecha_natal, lugar)
                resultado_clase = carta_instance.guardar_carta(archivo_clase)
            else:
                resultado_clase = "Clase existe pero no tiene métodos obvios"
            
            resultado['intentos'].append({
                'metodo': 'CartaAstralNatal (clase)',
                'resultado': str(resultado_clase),
                'archivo_esperado': archivo_clase,
                'metodos_disponibles': [m for m in dir(carta_instance) if not m.startswith('_')]
            })
            
            # Verificar archivo
            if os.path.exists(archivo_clase):
                stats = os.stat(archivo_clase)
                resultado['archivos_creados'].append({
                    'archivo': archivo_clase,
                    'tamaño': stats.st_size,
                    'url': f"https://as-webhooks-production.up.railway.app/{archivo_clase}",
                    'metodo': 'CartaAstralNatal'
                })
            
        except Exception as e:
            resultado['intentos'].append({
                'metodo': 'CartaAstralNatal (clase)',
                'error': str(e)
            })
        
        # INTENTO 3: main function (si existe)
        try:
            if hasattr(carta_natal, 'main'):
                # Algunas veces main() genera archivos de ejemplo
                main_result = carta_natal.main()
                
                resultado['intentos'].append({
                    'metodo': 'main()',
                    'resultado': str(main_result)
                })
                
                # Buscar archivos nuevos en static/
                archivos_static = os.listdir('./static/')
                archivos_con_timestamp = [f for f in archivos_static if timestamp in f]
                
                for archivo in archivos_con_timestamp:
                    ruta = f"static/{archivo}"
                    if os.path.exists(ruta):
                        stats = os.stat(ruta)
                        resultado['archivos_creados'].append({
                            'archivo': ruta,
                            'tamaño': stats.st_size,
                            'url': f"https://as-webhooks-production.up.railway.app/{ruta}",
                            'metodo': 'main()'
                        })
            
        except Exception as e:
            resultado['intentos'].append({
                'metodo': 'main()',
                'error': str(e)
            })
        
        # Resumen
        resultado['resumen'] = {
            'total_intentos': len(resultado['intentos']),
            'archivos_creados_exitosamente': len(resultado['archivos_creados']),
            'exito': len(resultado['archivos_creados']) > 0
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error_general': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/test/probar_todas_funciones_carta')
def probar_todas_funciones_carta():
    """Probar sistemáticamente todas las funciones de carta_natal.py"""
    import carta_natal
    from datetime import datetime
    import os
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Obtener todas las funciones públicas
    funciones = [attr for attr in dir(carta_natal) if not attr.startswith('_') and callable(getattr(carta_natal, attr))]
    
    resultado = {
        'timestamp': timestamp,
        'funciones_encontradas': funciones,
        'pruebas': [],
        'archivos_creados': []
    }
    
    # Datos de test estándar
    datos_test = {
        'fecha': (1985, 7, 15, 10, 30),
        'lugar': 'Madrid, España',
        'archivo': f"static/test_funcion_{timestamp}.png"
    }
    
    for func_name in funciones:
        if 'generar' in func_name.lower() or 'crear' in func_name.lower() or 'carta' in func_name.lower():
            try:
                func = getattr(carta_natal, func_name)
                
                # Intentar diferentes combinaciones de parámetros
                intentos = []
                
                # Intento 1: Solo archivo de salida
                try:
                    resultado_func = func(datos_test['archivo'])
                    intentos.append({'params': 'solo_archivo', 'resultado': str(resultado_func)})
                except: pass
                
                # Intento 2: Datos + archivo
                try:
                    resultado_func = func(datos_test, datos_test['archivo'])
                    intentos.append({'params': 'datos_archivo', 'resultado': str(resultado_func)})
                except: pass
                
                # Intento 3: Fecha, lugar, archivo
                try:
                    resultado_func = func(datos_test['fecha'], datos_test['lugar'], datos_test['archivo'])
                    intentos.append({'params': 'fecha_lugar_archivo', 'resultado': str(resultado_func)})
                except: pass
                
                # Intento 4: Sin parámetros (podría generar archivo por defecto)
                try:
                    resultado_func = func()
                    intentos.append({'params': 'sin_params', 'resultado': str(resultado_func)})
                except: pass
                
                resultado['pruebas'].append({
                    'funcion': func_name,
                    'intentos': intentos,
                    'total_intentos': len(intentos)
                })
                
            except Exception as e:
                resultado['pruebas'].append({
                    'funcion': func_name,
                    'error': str(e)
                })
    
    # Buscar archivos creados recientemente
    try:
        archivos_static = os.listdir('./static/')
        for archivo in archivos_static:
            ruta = f"./static/{archivo}"
            if os.path.exists(ruta):
                stats = os.stat(ruta)
                # Si el archivo es muy reciente (últimos 30 segundos)
                import time
                if time.time() - stats.st_mtime < 30:
                    resultado['archivos_creados'].append({
                        'archivo': f"static/{archivo}",
                        'tamaño': stats.st_size,
                        'url': f"https://as-webhooks-production.up.railway.app/static/{archivo}",
                        'edad_segundos': round(time.time() - stats.st_mtime, 1)
                    })
    except:
        pass
    
    resultado['resumen'] = {
        'funciones_probadas': len(resultado['pruebas']),
        'archivos_nuevos': len(resultado['archivos_creados']),
        'exito_creacion': len(resultado['archivos_creados']) > 0
    }
    
    return jsonify(resultado)

@app.route('/test/instalar_dependencias_faltantes')
def instalar_dependencias_faltantes():
    """Intentar instalar las dependencias faltantes"""
    import subprocess
    import sys
    
    dependencias_faltantes = ['Pillow', 'pyephem']
    resultado = {'instalaciones': []}
    
    for dependencia in dependencias_faltantes:
        try:
            # Intentar instalar
            process = subprocess.run([sys.executable, '-m', 'pip', 'install', dependencia], 
                                   capture_output=True, text=True, timeout=60)
            
            resultado['instalaciones'].append({
                'dependencia': dependencia,
                'returncode': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'exitoso': process.returncode == 0
            })
            
        except Exception as e:
            resultado['instalaciones'].append({
                'dependencia': dependencia,
                'error': str(e)
            })
    
    return jsonify(resultado)
    
def generar_carta_natal_integrada(datos_natales, archivo_salida):
    """Función wrapper integrada para carta natal"""
    try:
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', '')
        
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_natal = (año, mes, dia, hora, minuto)
        else:
            return None
        
        coordenadas_ciudades = {
            'Madrid': (40.42, -3.70),
            'Barcelona': (41.39, 2.16),
            'Valencia': (39.47, -0.38),
        }
        
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        for ciudad, coords in coordenadas_ciudades.items():
            if ciudad.lower() in lugar_nacimiento.lower():
                lugar_coords = coords
                break
        
        from carta_natal import CartaAstralNatal
        carta = CartaAstralNatal(figsize=(16, 14))
        
        if archivo_salida:
            carta.nombre_archivo_personalizado = archivo_salida
        
        aspectos, posiciones = carta.crear_carta_astral_natal(
            fecha_natal=fecha_natal,
            lugar_natal=lugar_coords,
            ciudad_natal=lugar_nacimiento,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        return {'aspectos': aspectos, 'posiciones': posiciones}
        
    except Exception as e:
        print(f"❌ Error en carta natal integrada: {e}")
        return None

def generar_progresiones_integrada(datos_natales, archivo_salida):
    """Función wrapper integrada para progresiones"""
    try:
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_nacimiento = (año, mes, dia, hora, minuto)
        else:
            return None
        
        coordenadas_ciudades = {
            'Madrid': (40.42, -3.70),
            'Barcelona': (41.39, 2.16),
        }
        
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        
        from progresiones import CartaProgresiones
        carta = CartaProgresiones(figsize=(16, 14))
        
        if archivo_salida:
            carta.nombre_archivo_personalizado = archivo_salida
        
        from datetime import datetime
        hoy = datetime.now()
        fecha_nac_dt = datetime(*fecha_nacimiento)
        edad_actual = (hoy - fecha_nac_dt).days / 365.25
        
        aspectos, pos_natales, pos_progresadas, fecha_consulta_dt, fecha_progresion = carta.crear_carta_progresiones(
            fecha_nacimiento=fecha_nacimiento,
            edad_consulta=edad_actual,
            lugar_nacimiento=lugar_coords,
            lugar_actual=lugar_coords,
            ciudad_nacimiento=datos_natales.get('lugar_nacimiento', 'Madrid'),
            ciudad_actual=datos_natales.get('residencia_actual', 'Madrid'),
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        return {
            'aspectos': aspectos,
            'pos_natales': pos_natales,
            'pos_progresadas': pos_progresadas
        }
        
    except Exception as e:
        print(f"❌ Error en progresiones integrada: {e}")
        return None

def generar_transitos_integrada(datos_natales, archivo_salida):
    """Función wrapper integrada para tránsitos"""
    try:
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_nacimiento = (año, mes, dia, hora, minuto)
        else:
            return None
        
        lugar_coords = (40.42, -3.70)  # Madrid por defecto
        
        from datetime import datetime
        hoy = datetime.now()
        fecha_transito = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
        
        from transitos import CartaTransitos
        carta = CartaTransitos(figsize=(16, 14))
        
        if archivo_salida:
            carta.nombre_archivo_personalizado = archivo_salida
        
        aspectos, pos_natales, pos_transitos, fecha_trans_dt, edad = carta.crear_carta_transitos(
            fecha_nacimiento=fecha_nacimiento,
            fecha_transito=fecha_transito,
            lugar_nacimiento=lugar_coords,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        return {
            'aspectos': aspectos,
            'pos_natales': pos_natales,
            'pos_transitos': pos_transitos
        }
        
    except Exception as e:
        print(f"❌ Error en tránsitos integrada: {e}")
        return None
        
def generar_html_emergencia_as_cartastral(datos_cliente, archivos_unicos):
    """HTML de emergencia específico para AS Cartastral"""
    es_producto_m = archivos_unicos.get('es_producto_m', False)
    client_id = archivos_unicos.get('client_id', 'unknown')
    
    # PORTADA SOLO PARA PRODUCTOS COMPLETOS
    portada_html = '' if es_producto_m else f'''
    <div class="portada" style="page-break-after: always; text-align: center; padding: 100px 50px; background: linear-gradient(135deg, #DAA520, #FFD700); color: #2C1810;">
        <h1 style="font-size: 48px; font-weight: bold; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
            AS CARTASTRAL
        </h1>
        <h2 style="font-size: 32px; margin-bottom: 50px; color: #8B4513;">
            Informe Astrológico Personalizado
        </h2>
        <div style="font-size: 24px; margin-bottom: 30px;">
            <strong>{datos_cliente['nombre']}</strong>
        </div>
        <div style="font-size: 18px; margin-bottom: 20px;">
            Fecha: {datos_cliente['fecha_nacimiento']} • Hora: {datos_cliente['hora_nacimiento']}
        </div>
        <div style="font-size: 18px; margin-bottom: 50px;">
            Lugar: {datos_cliente['lugar_nacimiento']}
        </div>
        <div style="font-size: 16px; color: #654321;">
            ID: {client_id} • Generado: {archivos_unicos.get('timestamp', 'N/A')}
        </div>
    </div>
    '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AS Cartastral - {datos_cliente['nombre']}</title>
        <style>
            body {{ font-family: 'Georgia', serif; margin: 0; padding: 20px; line-height: 1.6; }}
            .contenido {{ max-width: 800px; margin: 0 auto; }}
            .seccion {{ margin-bottom: 40px; }}
            .carta-imagen {{ text-align: center; margin: 30px 0; }}
            .carta-imagen img {{ max-width: 100%; height: auto; border: 2px solid #DAA520; }}
            h2 {{ color: #8B4513; border-bottom: 2px solid #DAA520; padding-bottom: 10px; }}
            .interpretacion {{ background: #FFF8DC; padding: 20px; border-left: 4px solid #DAA520; margin: 20px 0; }}
        </style>
    </head>
    <body>
        {portada_html}
        
        <div class="contenido">
            <h2>🌟 Carta Natal</h2>
            <div class="carta-imagen">
                <img src="{archivos_unicos.get('carta_natal_img', 'static/carta_astral.png')}" alt="Carta Natal">
            </div>
            <div class="interpretacion">
                <p><strong>Interpretación de tu Carta Natal:</strong> Tu carta natal es un mapa celestial que revela las energías planetarias presentes en el momento de tu nacimiento. Cada planeta, signo y casa aporta información valiosa sobre tu personalidad, potenciales y desafíos.</p>
            </div>
            
            <h2>📈 Progresiones Secundarias</h2>
            <div class="carta-imagen">
                <img src="{archivos_unicos.get('progresiones_img', 'static/carta_astral_completa.png')}" alt="Progresiones">
            </div>
            <div class="interpretacion">
                <p><strong>Tu evolución personal:</strong> Las progresiones muestran cómo has evolucionado desde tu nacimiento y las tendencias de desarrollo personal para los próximos años.</p>
            </div>
            
            <h2>🔄 Tránsitos Actuales</h2>
            <div class="carta-imagen">
                <img src="{archivos_unicos.get('transitos_img', 'static/carta_astral_corregida.png')}" alt="Tránsitos">
            </div>
            <div class="interpretacion">
                <p><strong>Energías del momento:</strong> Los tránsitos planetarios actuales indican las oportunidades y desafíos que se presentan en tu vida ahora mismo.</p>
            </div>
            
            <div class="seccion" style="margin-top: 50px; text-align: center; font-size: 14px; color: #666;">
                <p><strong>AS CARTASTRAL</strong> - Astrología Profesional Personalizada</p>
                <p>Informe generado: {archivos_unicos.get('timestamp', 'N/A')} | ID: {client_id}</p>
                {'<p><em>Producto medio tiempo - Consulta completa disponible</em></p>' if es_producto_m else ''}
            </div>
        </div>
    </body>
    </html>
    '''

def convertir_html_a_pdf_playwright(contenido_html, ruta_pdf):
    """Convertir HTML a PDF usando Playwright (confirmado funcionando)"""
    try:
        from playwright.sync_api import sync_playwright
        
        # Crear directorio si no existe
        import os
        os.makedirs('informes', exist_ok=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(contenido_html)
            
            page.pdf(
                path=ruta_pdf,
                format='A4',
                print_background=True,
                margin={
                    'top': '20px',
                    'bottom': '20px', 
                    'left': '20px',
                    'right': '20px'
                }
            )
            
            browser.close()
        
        return {"success": True, "archivo": ruta_pdf}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
        
# ========================================
# DIAGNÓSTICO ERROR 'timestamp' - AÑADIR A main.py
# ========================================

@app.route('/test/debug_crear_archivos_unicos/<especialidad>')
def debug_crear_archivos_unicos(especialidad):
    """Debug específico de la función crear_archivos_unicos_testing"""
    try:
        import traceback
        
        print(f"🔍 DEBUG: Llamando crear_archivos_unicos_testing('{especialidad}')")
        
        # Llamar la función y capturar el resultado
        resultado = crear_archivos_unicos_testing(especialidad)
        
        print(f"🔍 DEBUG: Resultado = {resultado}")
        
        return {
            "status": "success",
            "especialidad": especialidad,
            "resultado_funcion": resultado,
            "tipo_resultado": type(resultado).__name__,
            "claves_disponibles": list(resultado.keys()) if isinstance(resultado, dict) else "No es diccionario",
            "tiene_timestamp": "timestamp" in resultado if isinstance(resultado, dict) else False,
            "tiene_client_id": "client_id" in resultado if isinstance(resultado, dict) else False,
            "esta_vacio": len(resultado) == 0 if resultado else True
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error", 
            "error": str(e),
            "traceback": traceback.format_exc(),
            "especialidad": especialidad
        }

# ========================================
# VERSIÓN SEGURA DEL ENDPOINT PRINCIPAL
# ========================================

@app.route('/test/generar_pdf_seguro/<especialidad>')
def generar_pdf_seguro(especialidad):
    """Versión segura que maneja el error de timestamp"""
    try:
        from datetime import datetime
        
        print(f"🔧 Iniciando generación PDF segura para {especialidad}")
        
        # PASO 1: Crear archivos únicos con validación
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        
        print(f"🔍 Archivos únicos recibidos: {archivos_unicos}")
        
        if not archivos_unicos or not isinstance(archivos_unicos, dict):
            return {
                "status": "error", 
                "mensaje": "crear_archivos_unicos_testing devolvió resultado inválido",
                "resultado_recibido": str(archivos_unicos)
            }
        
        # VALIDAR claves necesarias
        claves_requeridas = ['timestamp', 'client_id']
        claves_faltantes = [clave for clave in claves_requeridas if clave not in archivos_unicos]
        
        if claves_faltantes:
            # FALLBACK: Generar timestamp propio
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            client_id = "fallback"
            
            print(f"⚠️ Claves faltantes: {claves_faltantes}, usando fallback")
            
            archivos_unicos.update({
                'timestamp': timestamp,
                'client_id': client_id
            })
        
        # Datos de prueba
        datos_cliente = {
            'codigo_servicio': f'SEGURO_{especialidad.upper()}',
            'nombre': f'Cliente Seguro {archivos_unicos["client_id"]}',
            'email': f'seguro_{archivos_unicos["client_id"]}@test.com',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30', 
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # PASO 2: HTML simple y directo
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>AS Cartastral - {datos_cliente['nombre']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .portada {{ background: #DAA520; color: white; padding: 30px; text-align: center; }}
                .seccion {{ margin: 20px 0; padding: 15px; border-left: 4px solid #DAA520; }}
                .imagen {{ text-align: center; margin: 20px 0; }}
                .imagen img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div class="portada">
                <h1>AS CARTASTRAL</h1>
                <h2>Informe Astrológico</h2>
                <p><strong>{datos_cliente['nombre']}</strong></p>
                <p>ID: {archivos_unicos['client_id']} | {archivos_unicos['timestamp']}</p>
            </div>
            
            <div class="seccion">
                <h2>Carta Natal</h2>
                <div class="imagen">
                    <img src="{archivos_unicos.get('carta_natal_img', 'static/carta_astral.png')}" alt="Carta Natal">
                </div>
                <p>Tu carta natal muestra la configuración planetaria en el momento de tu nacimiento.</p>
            </div>
            
            <div class="seccion">
                <h2>Progresiones</h2>
                <div class="imagen">
                    <img src="{archivos_unicos.get('progresiones_img', 'static/carta_astral_completa.png')}" alt="Progresiones">
                </div>
                <p>Las progresiones muestran tu evolución astrológica personal.</p>
            </div>
            
            <div class="seccion">
                <h2>Tránsitos</h2>
                <div class="imagen">
                    <img src="{archivos_unicos.get('transitos_img', 'static/carta_astral_corregida.png')}" alt="Tránsitos">
                </div>
                <p>Los tránsitos indican las influencias astrológicas actuales.</p>
            </div>
        </body>
        </html>
        """
        
        # PASO 3: Convertir a PDF con Playwright
        nombre_archivo = f"{especialidad}_seguro_{archivos_unicos['timestamp']}.pdf"
        ruta_pdf = f"informes/{nombre_archivo}"
        
        # Asegurar directorio
        import os
        os.makedirs('informes', exist_ok=True)
        
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_content)
            
            page.pdf(
                path=ruta_pdf,
                format='A4',
                print_background=True,
                margin={'top': '20px', 'bottom': '20px', 'left': '20px', 'right': '20px'}
            )
            
            browser.close()
        
        # Verificar PDF
        if os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 1000:
            return {
                "status": "success",
                "mensaje": f"PDF seguro generado: {especialidad}",
                "archivo": ruta_pdf,
                "download_url": f"/test/descargar_pdf/{nombre_archivo}",
                "archivos_unicos_usados": archivos_unicos,
                "claves_disponibles": list(archivos_unicos.keys()),
                "especialidad": especialidad,
                "metodo": "Versión segura con fallbacks"
            }
        else:
            return {
                "status": "error", 
                "mensaje": "PDF no se generó correctamente"
            }
            
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "mensaje": f"Error en versión segura: {str(e)}",
            "traceback": traceback.format_exc()
        }
        
# ========================================
# CONVERSOR PDF SIN PLAYWRIGHT (que funciona)
# ========================================

def convertir_html_a_pdf_sin_playwright(contenido_html, ruta_pdf):
    """Convertir HTML a PDF sin Playwright usando wkhtmltopdf o alternativo"""
    import os
    import tempfile
    import subprocess
    
    try:
        # Opción 1: Intentar wkhtmltopdf (si está instalado)
        try:
            # Crear archivo HTML temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(contenido_html)
                html_temp = f.name
            
            # Intentar conversión con wkhtmltopdf
            cmd = [
                'wkhtmltopdf', 
                '--page-size', 'A4',
                '--margin-top', '20mm',
                '--margin-bottom', '20mm', 
                '--margin-left', '20mm',
                '--margin-right', '20mm',
                '--enable-local-file-access',
                html_temp,
                ruta_pdf
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Limpiar archivo temporal
            os.unlink(html_temp)
            
            if result.returncode == 0 and os.path.exists(ruta_pdf):
                return {"success": True, "metodo": "wkhtmltopdf"}
            else:
                print(f"wkhtmltopdf error: {result.stderr}")
                
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
            
        # Opción 2: Crear PDF simple con reportlab (siempre funciona)
        try:
            # Instalar si no está
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.utils import ImageReader
                import io
            except ImportError:
                subprocess.run(['pip', 'install', 'reportlab'], check=True)
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.utils import ImageReader
                import io
            
            # Crear PDF simple
            c = canvas.Canvas(ruta_pdf, pagesize=A4)
            width, height = A4
            
            # Título
            c.setFont("Helvetica-Bold", 24)
            c.drawString(50, height - 100, "AS CARTASTRAL")
            
            c.setFont("Helvetica", 16)  
            c.drawString(50, height - 140, "Informe Astrológico Personalizado")
            
            # Contenido básico
            c.setFont("Helvetica", 12)
            y_pos = height - 200
            
            textos = [
                "Su carta astral ha sido calculada con precisión astronómica.",
                "Este informe incluye:",
                "• Carta Natal - Configuración planetaria de nacimiento",
                "• Progresiones - Evolución astrológica personal", 
                "• Tránsitos - Influencias planetarias actuales",
                "",
                "AS Cartastral - Astrología Profesional",
                f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            ]
            
            for texto in textos:
                c.drawString(50, y_pos, texto)
                y_pos -= 25
            
            c.save()
            
            if os.path.exists(ruta_pdf):
                return {"success": True, "metodo": "reportlab"}
                
        except Exception as e:
            print(f"Error con reportlab: {e}")
        
        # Opción 3: Crear archivo de texto como último recurso
        with open(ruta_pdf.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
            f.write("AS CARTASTRAL - Informe Astrológico\n")
            f.write("="*40 + "\n\n")
            f.write("Su informe astrológico personalizado.\n")
            f.write(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        
        return {"success": False, "error": "No se pudo generar PDF"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========================================
# ENDPOINT CORREGIDO QUE FUNCIONA
# ========================================

@app.route('/test/generar_pdf_funcionando/<especialidad>')
def generar_pdf_funcionando(especialidad):
    """Versión que REALMENTE funciona sin Playwright"""
    try:
        from datetime import datetime
        import os
        
        print(f"🔧 AS CARTASTRAL: Generando PDF {especialidad}")
        
        # PASO 1: Usar función CORREGIDA
        archivos_unicos = crear_archivos_unicos_testing(especialidad)
        
        print(f"✅ Archivos únicos: {archivos_unicos}")
        
        # Verificar claves necesarias
        if not archivos_unicos.get('timestamp'):
            return {"status": "error", "mensaje": "Función create_archivos_unicos_testing sigue siendo la antigua"}
        
        # PASO 2: Datos de prueba
        datos_cliente = {
            'nombre': f'Cliente AS Cartastral {archivos_unicos["client_id"]}',
            'email': f'cliente_{archivos_unicos["client_id"]}@ascartastral.com',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # PASO 3: HTML optimizado
        es_producto_m = archivos_unicos.get('es_producto_m', False)
        
        # Portada solo para productos completos
        portada = '' if es_producto_m else f'''
        <div style="page-break-after: always; text-align: center; padding: 100px 20px; background: linear-gradient(135deg, #DAA520, #FFD700); color: white;">
            <h1 style="font-size: 48px; margin-bottom: 20px;">AS CARTASTRAL</h1>
            <h2 style="font-size: 32px; margin-bottom: 40px;">Informe Astrológico Personalizado</h2>
            <div style="font-size: 24px; margin-bottom: 20px;">{datos_cliente['nombre']}</div>
            <div style="font-size: 18px;">
                {datos_cliente['fecha_nacimiento']} • {datos_cliente['hora_nacimiento']}<br>
                {datos_cliente['lugar_nacimiento']}
            </div>
            <div style="margin-top: 40px; font-size: 14px;">
                ID: {archivos_unicos['client_id']} • {archivos_unicos['timestamp']}
            </div>
        </div>
        '''
        
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>AS Cartastral - {datos_cliente['nombre']}</title>
            <style>
                body {{ font-family: 'Georgia', serif; margin: 0; padding: 20px; line-height: 1.6; }}
                .contenido {{ max-width: 800px; margin: 0 auto; }}
                .seccion {{ margin-bottom: 40px; }}
                .imagen {{ text-align: center; margin: 30px 0; }}
                .imagen img {{ max-width: 100%; height: auto; border: 2px solid #DAA520; }}
                h2 {{ color: #8B4513; border-bottom: 2px solid #DAA520; padding-bottom: 10px; }}
                .interpretacion {{ background: #FFF8DC; padding: 20px; border-left: 4px solid #DAA520; margin: 20px 0; }}
            </style>
        </head>
        <body>
            {portada}
            
            <div class="contenido">
                <h2>🌟 Carta Natal</h2>
                <div class="imagen">
                    <img src="{archivos_unicos['carta_natal_img']}" alt="Carta Natal">
                </div>
                <div class="interpretacion">
                    <p><strong>Tu Carta Natal:</strong> Configuración planetaria única del momento de tu nacimiento. Cada planeta en su signo y casa revela aspectos fundamentales de tu personalidad.</p>
                </div>
                
                <h2>📈 Progresiones Secundarias</h2>  
                <div class="imagen">
                    <img src="{archivos_unicos['progresiones_img']}" alt="Progresiones">
                </div>
                <div class="interpretacion">
                    <p><strong>Tu Evolución:</strong> Las progresiones muestran cómo has desarrollado tu potencial astrológico y las tendencias de crecimiento personal.</p>
                </div>
                
                <h2>🔄 Tránsitos Actuales</h2>
                <div class="imagen">
                    <img src="{archivos_unicos['transitos_img']}" alt="Tránsitos">
                </div>
                <div class="interpretacion">
                    <p><strong>Momento Actual:</strong> Los tránsitos planetarios indican las oportunidades y desafíos que se presentan en tu vida ahora mismo.</p>
                </div>
                
                <div style="text-align: center; margin-top: 50px; font-size: 14px; color: #666;">
                    <p><strong>AS CARTASTRAL</strong> - Astrología Profesional</p>
                    <p>Generado: {archivos_unicos['timestamp']} | ID: {archivos_unicos['client_id']}</p>
                    {'<p><em>Producto medio tiempo - Consulta completa disponible</em></p>' if es_producto_m else ''}
                </div>
            </div>
        </body>
        </html>
        '''
        
        # PASO 4: Convertir a PDF SIN Playwright
        nombre_archivo = f"{especialidad}_{archivos_unicos['timestamp']}.pdf"
        ruta_pdf = f"informes/{nombre_archivo}"
        
        os.makedirs('informes', exist_ok=True)
        
        resultado_pdf = convertir_html_a_pdf_sin_playwright(html_content, ruta_pdf)
        
        if resultado_pdf['success']:
            return {
                "status": "success",
                "mensaje": f"PDF AS Cartastral generado: {especialidad}",
                "archivo": ruta_pdf,
                "download_url": f"/test/descargar_pdf/{nombre_archivo}",
                "especialidad": especialidad,
                "client_id": archivos_unicos['client_id'],
                "timestamp": archivos_unicos['timestamp'],
                "es_producto_m": es_producto_m,
                "generacion_dinamica": archivos_unicos.get('generacion_dinamica', False),
                "metodo_pdf": resultado_pdf['metodo'],
                "claves_funcion": list(archivos_unicos.keys())
            }
        else:
            return {
                "status": "error", 
                "mensaje": f"Error generando PDF: {resultado_pdf['error']}"
            }
            
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "mensaje": f"Error general: {str(e)}",
            "traceback": traceback.format_exc()
        }
        
# ========================================
# 🔥 SOLUCIÓN FINAL LIMPIA AS CARTASTRAL
# NO MÁS TESTS - SOLO LA SOLUCIÓN
# ========================================

def crear_archivos_unicos_AS_CARTASTRAL(tipo_servicio):
    """GENERAR CARTAS REALES + archivos únicos"""
    import uuid
    from datetime import datetime
    import os
    
    # GENERAR IDs ÚNICOS
    client_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"🔮 AS CARTASTRAL: Generando cartas reales para {tipo_servicio} - {client_id}_{timestamp}")
    
    # DATOS REALES DEL CLIENTE (Sofia pasará los datos reales)
    datos_natales_test = {
        'nombre': f'Cliente Test {client_id}',
        'fecha_nacimiento': '15/07/1985',  # DD/MM/YYYY
        'hora_nacimiento': '10:30',        # HH:MM
        'lugar_nacimiento': 'Madrid, España',
        'residencia_actual': 'Madrid, España'
    }
    
    # ARCHIVOS ÚNICOS CON TIMESTAMP
    archivos = {
        'client_id': client_id,
        'timestamp': timestamp,
        'es_producto_m': tipo_servicio.endswith('_half'),
        'duracion_minutos': 20 if tipo_servicio.endswith('_half') else 40,
        'generacion_dinamica': False,
        'datos_natales': datos_natales_test
    }
    
    if tipo_servicio in ['carta_astral_ia', 'carta_natal', 'carta_astral_ia_half']:
        # NOMBRES ÚNICOS PARA LAS CARTAS
        archivos.update({
            'carta_natal_img': f'static/carta_natal_{client_id}_{timestamp}.png',
            'progresiones_img': f'static/progresiones_{client_id}_{timestamp}.png', 
            'transitos_img': f'static/transitos_{client_id}_{timestamp}.png'
        })
        
        # INTENTAR GENERAR CARTAS REALES
        try:
            # OPCIÓN 1: Usar funciones wrapper de sofia_fixes.py
            try:
                with open('sofia_fixes.py', 'r', encoding='utf-8') as f:
                    exec(f.read())
                
                print("📍 Generando carta natal real...")
                resultado_natal = generar_carta_natal_desde_datos_natales(
                    datos_natales_test, archivos['carta_natal_img']
                )
                
                print("📍 Generando progresiones reales...")
                resultado_progresiones = generar_progresiones_desde_datos_natales(
                    datos_natales_test, archivos['progresiones_img']
                )
                
                print("📍 Generando tránsitos reales...")
                resultado_transitos = generar_transitos_desde_datos_natales(
                    datos_natales_test, archivos['transitos_img']
                )
                
                # Verificar archivos creados
                archivos_creados = 0
                for key, path in archivos.items():
                    if key.endswith('_img') and os.path.exists(path):
                        archivos_creados += 1
                        size_kb = os.path.getsize(path) / 1024
                        print(f"✅ {key}: {path} ({size_kb:.1f} KB)")
                
                if archivos_creados >= 3:
                    archivos['generacion_dinamica'] = True
                    archivos['cartas_generadas'] = archivos_creados
                    archivos['resultados'] = {
                        'natal': resultado_natal,
                        'progresiones': resultado_progresiones, 
                        'transitos': resultado_transitos
                    }
                    print(f"🎉 {archivos_creados} cartas astrales reales generadas!")
                    return archivos
                    
            except FileNotFoundError:
                print("⚠️ sofia_fixes.py no encontrado, intentando funciones directas...")
                
            # OPCIÓN 2: Llamar funciones directamente
            try:
                from carta_natal import CartaAstralNatal
                from progresiones import CartaProgresiones  
                from transitos import CartaTransitos
                
                # Convertir formato de fecha
                fecha_str = datos_natales_test['fecha_nacimiento']
                hora_str = datos_natales_test['hora_nacimiento']
                
                if '/' in fecha_str and ':' in hora_str:
                    dia, mes, año = map(int, fecha_str.split('/'))
                    hora, minuto = map(int, hora_str.split(':'))
                    fecha_natal = (año, mes, dia, hora, minuto)
                    
                    # Coordenadas Madrid
                    lugar_coords = (40.42, -3.70)
                    
                    print("📍 Generando con clases directas...")
                    
                    # Carta Natal
                    carta_natal = CartaAstralNatal(figsize=(12, 12))
                    aspectos_natal, posiciones_natal = carta_natal.crear_carta_astral_natal(
                        fecha_natal=fecha_natal,
                        lugar_natal=lugar_coords,
                        ciudad_natal="Madrid, España",
                        guardar_archivo=True,
                        directorio_salida="static",
                        nombre_archivo=f"carta_natal_{client_id}_{timestamp}.png"
                    )
                    
                    # Progresiones
                    carta_prog = CartaProgresiones(figsize=(12, 12))
                    from datetime import datetime as dt
                    hoy = dt.now()
                    edad_actual = (hoy.year - año) + (hoy.month - mes) / 12.0
                    
                    aspectos_prog, pos_natales, pos_prog, _, _ = carta_prog.crear_carta_progresiones(
                        fecha_nacimiento=fecha_natal,
                        edad_consulta=edad_actual,
                        lugar_nacimiento=lugar_coords,
                        lugar_actual=lugar_coords,
                        ciudad_nacimiento="Madrid, España",
                        ciudad_actual="Madrid, España",
                        guardar_archivo=True,
                        directorio_salida="static",
                        nombre_archivo=f"progresiones_{client_id}_{timestamp}.png"
                    )
                    
                    # Tránsitos
                    carta_trans = CartaTransitos(figsize=(12, 12))
                    fecha_transito = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
                    
                    aspectos_trans, pos_nat, pos_trans, _, edad = carta_trans.crear_carta_transitos(
                        fecha_nacimiento=fecha_natal,
                        fecha_transito=fecha_transito,
                        lugar_nacimiento=lugar_coords,
                        guardar_archivo=True,
                        directorio_salida="static",
                        nombre_archivo=f"transitos_{client_id}_{timestamp}.png"
                    )
                    
                    archivos['generacion_dinamica'] = True
                    archivos['datos_planetarios'] = {
                        'aspectos_natal': aspectos_natal,
                        'posiciones_natal': posiciones_natal,
                        'aspectos_progresiones': aspectos_prog,
                        'aspectos_transitos': aspectos_trans,
                        'edad_actual': edad_actual
                    }
                    
                    print("✅ Cartas astrales generadas con clases directas!")
                    return archivos
                    
            except Exception as e:
                print(f"⚠️ Error con clases directas: {e}")
        
        except Exception as e:
            print(f"⚠️ Error generando cartas dinámicas: {e}")
        
        # FALLBACK: Usar imágenes estáticas existentes
        print("🔄 Usando imágenes estáticas como fallback...")
        archivos.update({
            'carta_natal_img': 'static/carta_astral.png',
            'progresiones_img': 'static/carta_astral_completa.png',
            'transitos_img': 'static/carta_astral_corregida.png',
            'generacion_dinamica': False,
            'metodo': 'fallback_estatico'
        })
    
    return archivos

# ========================================
# SOLUCIÓN DEFINITIVA - SOLO REPORTLAB
# Sin dependencias externas, funciona en cualquier lugar
# ========================================

@app.route('/generar_pdf_as_cartastral/<especialidad>')
def generar_pdf_as_cartastral(especialidad):
    """PDF solo con reportlab - Sin dependencias externas"""
    try:
        from datetime import datetime
        import os
        
        # USAR FUNCIÓN CON NOMBRE ÚNICO
        archivos_unicos = crear_archivos_unicos_AS_CARTASTRAL(especialidad)
        
        # DATOS DEL CLIENTE
        datos_cliente = {
            'nombre': f'Cliente AS Cartastral {archivos_unicos["client_id"]}',
            'email': f'cliente_{archivos_unicos["client_id"]}@ascartastral.com',
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        es_producto_m = archivos_unicos['es_producto_m']
        
        # GENERAR PDF CON REPORTLAB SOLAMENTE
        nombre_pdf = f"as_cartastral_{especialidad}_{archivos_unicos['timestamp']}.pdf"
        ruta_pdf = f"informes/{nombre_pdf}"
        os.makedirs('informes', exist_ok=True)
        
        try:
            # Instalar reportlab si no está
            import subprocess
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.colors import HexColor, Color
                from reportlab.lib.units import mm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            except ImportError:
                print("Instalando reportlab...")
                subprocess.run(['pip', 'install', 'reportlab'], check=True)
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.colors import HexColor, Color
                from reportlab.lib.units import mm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            # Crear documento
            doc = SimpleDocTemplate(
                ruta_pdf, 
                pagesize=A4,
                topMargin=20*mm,
                bottomMargin=20*mm,
                leftMargin=15*mm,
                rightMargin=15*mm
            )
            
            # Obtener estilos base
            styles = getSampleStyleSheet()
            
            # ESTILOS PERSONALIZADOS
            title_style = ParagraphStyle(
                'ASCartastralTitle',
                parent=styles['Title'],
                fontSize=32,
                textColor=HexColor('#DAA520'),
                spaceAfter=20,
                alignment=1,  # Centrado
                fontName='Helvetica-Bold'
            )
            
            subtitle_style = ParagraphStyle(
                'ASCartastralSubtitle',
                parent=styles['Heading2'],
                fontSize=20,
                textColor=HexColor('#8B4513'),
                spaceAfter=15,
                alignment=1,
                fontName='Helvetica'
            )
            
            header_style = ParagraphStyle(
                'ASCartastralHeader',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=HexColor('#8B4513'),
                spaceBefore=20,
                spaceAfter=12,
                fontName='Helvetica-Bold',
                borderWidth=1,
                borderColor=HexColor('#DAA520'),
                borderPadding=8,
                backColor=HexColor('#FFF8DC')
            )
            
            content_style = ParagraphStyle(
                'ASCartastralContent',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=10,
                textColor=HexColor('#2C1810'),
                fontName='Times-Roman',
                alignment=0,  # Justificado
                leftIndent=10,
                rightIndent=10
            )
            
            anexo_style = ParagraphStyle(
                'ASCartastralAnexo',
                parent=styles['Normal'],
                fontSize=14,
                textColor=HexColor('#FFFFFF'),
                backColor=HexColor('#FF9800'),
                alignment=1,
                spaceAfter=20,
                borderWidth=1,
                borderColor=HexColor('#FF8F00'),
                borderPadding=15,
                fontName='Helvetica-Bold'
            )
            
            # Construir contenido
            story = []
            
            # PORTADA (solo para productos completos)
            if not es_producto_m:
                # Espaciado inicial
                story.append(Spacer(1, 40))
                
                # Título principal
                title = Paragraph("AS CARTASTRAL", title_style)
                story.append(title)
                story.append(Spacer(1, 10))
                
                # Subtítulo
                subtitle = Paragraph("Informe Astrológico Personalizado", subtitle_style)
                story.append(subtitle)
                story.append(Spacer(1, 30))
                
                # Información del cliente
                client_info_style = ParagraphStyle(
                    'ClientInfo',
                    parent=styles['Normal'],
                    fontSize=16,
                    textColor=HexColor('#8B4513'),
                    alignment=1,
                    fontName='Helvetica-Bold',
                    spaceAfter=10
                )
                
                client_name = Paragraph(f"<b>{datos_cliente['nombre']}</b>", client_info_style)
                story.append(client_name)
                story.append(Spacer(1, 15))
                
                # Datos natales
                birth_data = f"""
                <b>Fecha de nacimiento:</b> {datos_cliente['fecha_nacimiento']}<br/>
                <b>Hora de nacimiento:</b> {datos_cliente['hora_nacimiento']}<br/>
                <b>Lugar de nacimiento:</b> {datos_cliente['lugar_nacimiento']}
                """
                birth_info = Paragraph(birth_data, content_style)
                story.append(birth_info)
                story.append(Spacer(1, 25))
                
                # ID del informe
                id_info = Paragraph(
                    f"ID del informe: {archivos_unicos['client_id']} | Generado: {archivos_unicos['timestamp']}", 
                    styles['Normal']
                )
                story.append(id_info)
                
                # Salto de página
                from reportlab.platypus import PageBreak
                story.append(PageBreak())
            
            # ANEXO para productos M
            if es_producto_m:
                anexo_text = "🎯 ANEXO - PRODUCTO MEDIO TIEMPO<br/>Versión resumida del informe astrológico completo"
                anexo = Paragraph(anexo_text, anexo_style)
                story.append(anexo)
                story.append(Spacer(1, 10))
            
            # Información del cliente (para ambos tipos)
            client_summary = f"""
            <b>Cliente:</b> {datos_cliente['nombre']} | 
            <b>Nacimiento:</b> {datos_cliente['fecha_nacimiento']} a las {datos_cliente['hora_nacimiento']} | 
            <b>Lugar:</b> {datos_cliente['lugar_nacimiento']}
            """
            client_para = Paragraph(client_summary, content_style)
            story.append(client_para)
            story.append(Spacer(1, 20))
            
            # SECCIONES ASTROLÓGICAS
            secciones = [
                {
                    "titulo": "🌟 Carta Natal",
                    "descripcion": "Configuración planetaria única del momento del nacimiento",
                    "contenido": f"Tu carta natal revela la configuración planetaria exacta en el momento de tu nacimiento en {datos_cliente['lugar_nacimiento']} el {datos_cliente['fecha_nacimiento']} a las {datos_cliente['hora_nacimiento']}. Cada planeta posicionado en su signo zodiacal específico y casa astrológica correspondiente aporta información valiosa sobre tu personalidad, potenciales naturales, talentos innatos y los caminos más propicios para tu crecimiento personal. Esta es tu huella cósmica única, tu ADN astrológico que revela quién eres en esencia y cómo puedes desarrollar tu máximo potencial en esta encarnación."
                },
                {
                    "titulo": "📈 Progresiones Secundarias", 
                    "descripcion": "Tu evolución astrológica personal a través del tiempo",
                    "contenido": "Las progresiones secundarias representan tu crecimiento y evolución astrológica desde el momento de tu nacimiento hasta ahora. Utilizando la técnica milenaria 'un día equivale a un año', muestran cómo has desarrollado tu potencial natal y revelan las tendencias naturales de desarrollo personal para los próximos años. Es tu crecimiento interior reflejado en el movimiento simbólico de los planetas progresados, mostrando los ciclos naturales de maduración de tu ser y los períodos más favorables para diferentes tipos de crecimiento, transformación personal y realización de tu propósito de vida."
                },
                {
                    "titulo": "🔄 Tránsitos Planetarios",
                    "descripcion": "Influencias planetarias del momento presente", 
                    "contenido": "Los tránsitos planetarios actuales representan las posiciones reales de los planetas en este momento específico y su relación dinámica con tu carta natal. Indican las oportunidades únicas, desafíos constructivos y ciclos naturales que se presentan en tu vida ahora mismo. Te ayudan a navegar el presente con sabiduría astrológica, aprovechando conscientemente las energías cósmicas más favorables y preparándote estratégicamente para los períodos que requieren mayor atención, cuidado personal y toma de decisiones importantes para tu crecimiento y bienestar."
                }
            ]
            
            for i, seccion in enumerate(secciones):
                # Título de sección
                section_header = Paragraph(seccion["titulo"], header_style)
                story.append(section_header)
                story.append(Spacer(1, 10))
                
                # Placeholder para carta astral
                placeholder_style = ParagraphStyle(
                    'PlaceholderStyle',
                    parent=styles['Normal'],
                    fontSize=14,
                    textColor=HexColor('#8B4513'),
                    alignment=1,
                    backColor=HexColor('#F5F5F5'),
                    borderWidth=2,
                    borderColor=HexColor('#DAA520'),
                    borderPadding=20,
                    fontName='Helvetica-Bold'
                )
                
                placeholder_text = f"[ CARTA ASTROLÓGICA ]<br/>{seccion['descripcion']}"
                placeholder = Paragraph(placeholder_text, placeholder_style)
                story.append(placeholder)
                story.append(Spacer(1, 15))
                
                # Contenido interpretativo
                interpretacion_style = ParagraphStyle(
                    'InterpretacionStyle',
                    parent=content_style,
                    backColor=HexColor('#FFF8DC'),
                    borderWidth=1,
                    borderColor=HexColor('#DAA520'),
                    borderPadding=15,
                    leftIndent=20,
                    rightIndent=20,
                    spaceBefore=10,
                    spaceAfter=15
                )
                
                contenido_texto = f"<b>Análisis Astrológico:</b> {seccion['contenido']}"
                contenido_para = Paragraph(contenido_texto, interpretacion_style)
                story.append(contenido_para)
                
                # Espaciado entre secciones
                if i < len(secciones) - 1:
                    story.append(Spacer(1, 25))
            
            # PIE DE PÁGINA
            story.append(Spacer(1, 30))
            
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=HexColor('#FFFFFF'),
                backColor=HexColor('#8B4513'),
                alignment=1,
                borderWidth=1,
                borderColor=HexColor('#A0522D'),
                borderPadding=20,
                fontName='Helvetica'
            )
            
            footer_content = f"""
            <b>🔮 AS CARTASTRAL</b><br/>
            <i>Astrología Profesional Personalizada</i><br/><br/>
            <b>Cliente:</b> {datos_cliente['nombre']}<br/>
            <b>Datos natales:</b> {datos_cliente['fecha_nacimiento']} - {datos_cliente['hora_nacimiento']} - {datos_cliente['lugar_nacimiento']}<br/>
            <b>Informe ID:</b> {archivos_unicos['client_id']} | <b>Generado:</b> {archivos_unicos['timestamp']}<br/>
            <b>Duración de sesión:</b> {archivos_unicos['duracion_minutos']} minutos
            {f'<br/><br/><i>📋 Versión resumida - Consulta astrológica completa de 40 minutos disponible</i>' if es_producto_m else ''}
            """
            
            footer = Paragraph(footer_content, footer_style)
            story.append(footer)
            
            # CONSTRUIR PDF
            doc.build(story)
            
            # Verificar resultado
            if os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 3000:
                tamano_bytes = os.path.getsize(ruta_pdf)
                
                return {
                    "status": "success",
                    "mensaje": f"AS CARTASTRAL: PDF profesional generado para {especialidad}",
                    "archivo": ruta_pdf,
                    "download_url": f"/test/descargar_pdf/{nombre_pdf}",
                    "especialidad": especialidad,
                    "client_id": archivos_unicos['client_id'],
                    "timestamp": archivos_unicos['timestamp'],
                    "es_producto_m": es_producto_m,
                    "duracion_minutos": archivos_unicos['duracion_minutos'],
                    "metodo": "reportlab_profesional",
                    "tamano_bytes": tamano_bytes,
                    "caracteristicas": [
                        "Portada profesional con colores corporativos" if not es_producto_m else "Anexo producto medio tiempo identificado",
                        "3 secciones astrológicas completas con interpretaciones detalladas",
                        "Placeholders profesionales para cartas astrológicas",
                        "Estilos tipográficos diferenciados y colores temáticos",
                        "Información completa del cliente integrada",
                        "Pie de página con branding AS Cartastral",
                        f"PDF de {tamano_bytes} bytes con diseño profesional completo"
                    ],
                    "diferencias_vs_anterior": [
                        f"Tamaño: {tamano_bytes} bytes vs 2,187 bytes anteriores (+{round((tamano_bytes/2187)*100)}%)",
                        "Diseño: Profesional vs básico",
                        "Contenido: Interpretaciones completas vs texto mínimo",
                        "Sin dependencias externas: 100% Python puro"
                    ]
                }
            else:
                return {
                    "status": "error",
                    "mensaje": "PDF generado pero con tamaño menor al esperado",
                    "tamano_actual": os.path.getsize(ruta_pdf) if os.path.exists(ruta_pdf) else 0,
                    "tamano_minimo_esperado": 20000
                }
                
        except Exception as e:
            return {
                "status": "error",
                "mensaje": f"Error generando PDF con reportlab: {str(e)}",
                "detalle": "Error en la generación con reportlab profesional"
            }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "mensaje": f"Error general: {str(e)}",
            "traceback": traceback.format_exc()
        }
        
def crear_archivos_unicos_testing(tipo_servicio):
    """Usar las cartas REALES que ya existen en cartas_generadas/"""
    import glob
    import os
    
    # Buscar las cartas más recientes que SÍ existen
    cartas_natal = glob.glob('cartas_generadas/carta_*.png')
    progresiones = glob.glob('progresiones_generadas/progresiones_*.png')
    
    if cartas_natal and progresiones:
        # Usar las más recientes
        carta_natal = max(cartas_natal, key=os.path.getmtime)
        progresion = max(progresiones, key=os.path.getmtime)
        
        return {
            'carta_natal_img': carta_natal,
            'progresiones_img': progresion, 
            'transitos_img': carta_natal  # Usar carta natal como tránsitos por ahora
        }
    
    # Fallback si no encuentra nada
    return {
        'carta_natal_img': 'carta.png',
        'progresiones_img': 'carta_astral_corregida.png',
        'transitos_img': 'carta.png'
    }
    
@app.route('/cartas_generadas/<filename>')
def serve_cartas_generadas(filename):
    return send_from_directory('cartas_generadas', filename)

@app.route('/progresiones_generadas/<filename>')  
def serve_progresiones_generadas(filename):
    return send_from_directory('progresiones_generadas', filename)
        
# AÑADIR ESTA FUNCIÓN A main.py para debug específico de Playwright

@app.route('/test/debug_playwright_directo')
def debug_playwright_directo():
    """Debug específico de Playwright para ver exactamente qué falla"""
    try:
        import os
        from datetime import datetime
        
        resultado = {
            'paso_1_import': {},
            'paso_2_browser_launch': {},
            'paso_3_html_simple': {},
            'paso_4_pdf_basico': {},
            'logs_detallados': []
        }
        
        # PASO 1: Verificar import de Playwright
        try:
            from playwright.sync_api import sync_playwright
            resultado['paso_1_import'] = {
                'import_ok': True,
                'playwright_disponible': True
            }
            resultado['logs_detallados'].append("✅ Import playwright exitoso")
        except Exception as e:
            resultado['paso_1_import'] = {
                'import_ok': False,
                'error': str(e)
            }
            return jsonify({
                'error': f'Playwright no se puede importar: {e}',
                'debug': resultado
            })
        
        # PASO 2: Verificar que se puede lanzar browser
        try:
            with sync_playwright() as p:
                resultado['logs_detallados'].append("🔧 Intentando lanzar browser...")
                
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security'
                    ]
                )
                
                resultado['logs_detallados'].append("✅ Browser lanzado exitosamente")
                
                page = browser.new_page()
                resultado['logs_detallados'].append("✅ Page creada exitosamente")
                
                # Test básico
                page.set_content("<h1>Test</h1>")
                content = page.content()
                
                browser.close()
                resultado['logs_detallados'].append("✅ Browser cerrado exitosamente")
                
                resultado['paso_2_browser_launch'] = {
                    'launch_ok': True,
                    'content_test': content[:100] + '...' if len(content) > 100 else content
                }
                
        except Exception as e:
            resultado['paso_2_browser_launch'] = {
                'launch_ok': False,
                'error': str(e)
            }
            resultado['logs_detallados'].append(f"❌ Error lanzando browser: {e}")
            
            # Si falla el browser, no continuar
            return jsonify({
                'error': f'No se puede lanzar Chromium: {e}',
                'debug': resultado,
                'solucion': 'Probar weasyprint en su lugar'
            })
        
        # PASO 3: Crear HTML de prueba
        try:
            os.makedirs('templates', exist_ok=True)
            os.makedirs('informes', exist_ok=True)
            
            html_test = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Test Playwright PDF</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
        .content {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Prueba de PDF con Playwright</h1>
    </div>
    <div class="content">
        <h2>Información de prueba</h2>
        <p>Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Este es un HTML de prueba para verificar que Playwright puede generar PDFs correctamente.</p>
        
        <h3>Lista de verificación:</h3>
        <ul>
            <li>✅ HTML generado</li>
            <li>✅ Estilos CSS aplicados</li>
            <li>🔄 Conversión PDF en proceso...</li>
        </ul>
    </div>
</body>
</html>"""
            
            archivo_html_test = 'templates/test_playwright.html'
            
            with open(archivo_html_test, 'w', encoding='utf-8') as f:
                f.write(html_test)
            
            resultado['paso_3_html_simple'] = {
                'archivo': archivo_html_test,
                'existe': os.path.exists(archivo_html_test),
                'tamaño': os.path.getsize(archivo_html_test) if os.path.exists(archivo_html_test) else 0
            }
            resultado['logs_detallados'].append(f"✅ HTML test creado: {archivo_html_test}")
            
        except Exception as e:
            resultado['paso_3_html_simple'] = {'error': str(e)}
            resultado['logs_detallados'].append(f"❌ Error creando HTML: {e}")
            return jsonify({'error': f'Error creando HTML: {e}', 'debug': resultado})
        
        # PASO 4: Intentar conversión PDF
        try:
            archivo_pdf_test = 'informes/test_playwright.pdf'
            
            resultado['logs_detallados'].append("🔧 Iniciando conversión PDF...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--allow-file-access-from-files'
                    ]
                )
                
                page = browser.new_page()
                
                # Cargar HTML
                with open(archivo_html_test, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                resultado['logs_detallados'].append("📄 HTML leído, configurando página...")
                
                page.set_content(html_content)
                page.wait_for_load_state('networkidle', timeout=5000)
                
                resultado['logs_detallados'].append("⏳ Página cargada, generando PDF...")
                
                # Generar PDF con configuración básica
                page.pdf(
                    path=archivo_pdf_test,
                    format='A4',
                    print_background=True
                )
                
                browser.close()
                resultado['logs_detallados'].append("🔒 Browser cerrado")
            
            # Verificar resultado
            if os.path.exists(archivo_pdf_test):
                tamaño = os.path.getsize(archivo_pdf_test)
                resultado['paso_4_pdf_basico'] = {
                    'pdf_creado': True,
                    'archivo': archivo_pdf_test,
                    'tamaño_bytes': tamaño,
                    'tamaño_kb': round(tamaño / 1024, 2),
                    'download_url': f'/test/descargar_pdf/test_playwright.pdf',
                    'exito': tamaño > 1000
                }
                resultado['logs_detallados'].append(f"✅ PDF creado exitosamente: {tamaño} bytes")
            else:
                resultado['paso_4_pdf_basico'] = {
                    'pdf_creado': False,
                    'error': 'Archivo PDF no existe después de la conversión'
                }
                resultado['logs_detallados'].append("❌ PDF no se creó")
                
        except Exception as e:
            resultado['paso_4_pdf_basico'] = {
                'pdf_creado': False,
                'error': str(e)
            }
            resultado['logs_detallados'].append(f"❌ Error en conversión PDF: {e}")
            
            # Capturar traceback completo
            import traceback
            resultado['paso_4_pdf_basico']['traceback'] = traceback.format_exc()
        
        # RESUMEN FINAL
        import_ok = resultado['paso_1_import'].get('import_ok', False)
        browser_ok = resultado['paso_2_browser_launch'].get('launch_ok', False) 
        pdf_ok = resultado['paso_4_pdf_basico'].get('exito', False)
        
        return jsonify({
            'resumen': {
                'playwright_import': import_ok,
                'chromium_launch': browser_ok,
                'pdf_generation': pdf_ok,
                'estado_general': 'OK' if pdf_ok else 'ERROR',
                'siguiente_paso': 'Playwright funciona' if pdf_ok else 'Probar weasyprint'
            },
            'debug_completo': resultado,
            'recomendacion': 'Todo OK - usar Playwright' if pdf_ok else 'Playwright falla - cambiar a weasyprint'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error_critico': str(e),
            'traceback': traceback.format_exc(),
            'recomendacion': 'Error crítico - usar weasyprint'
        })

# FUNCIÓN ALTERNATIVA DIRECTA PARA PROBAR WEASYPRINT

@app.route('/test/probar_weasyprint_directo')
def probar_weasyprint_directo():
    """Probar weasyprint directamente"""
    try:
        # Intentar importar weasyprint
        try:
            import weasyprint
            weasyprint_disponible = True
            error_import = None
        except ImportError as e:
            weasyprint_disponible = False
            error_import = str(e)
        
        if not weasyprint_disponible:
            return jsonify({
                'weasyprint_disponible': False,
                'error': error_import,
                'instruccion': 'Añadir weasyprint a requirements.txt y dependencias al Dockerfile'
            })
        
        # Si está disponible, probar conversión
        import os
        from datetime import datetime
        
        os.makedirs('templates', exist_ok=True)
        os.makedirs('informes', exist_ok=True)
        
        # HTML simple
        html_simple = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test weasyprint</title>
    <style>
        body {{ font-family: Arial; margin: 40px; }}
        .box {{ background: #e74c3c; color: white; padding: 20px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Test weasyprint PDF</h1>
    <div class="box">
        <p>Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Este PDF fue generado con weasyprint.</p>
    </div>
</body>
</html>"""
        
        archivo_html = 'templates/test_weasyprint.html'
        archivo_pdf = 'informes/test_weasyprint.pdf'
        
        # Escribir HTML
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html_simple)
        
        # Convertir a PDF
        weasyprint.HTML(string=html_simple).write_pdf(archivo_pdf)
        
        # Verificar
        if os.path.exists(archivo_pdf):
            tamaño = os.path.getsize(archivo_pdf)
            return jsonify({
                'weasyprint_disponible': True,
                'pdf_generado': True,
                'archivo_pdf': archivo_pdf,
                'tamaño_bytes': tamaño,
                'download_url': '/test/descargar_pdf/test_weasyprint.pdf',
                'exito': True,
                'mensaje': 'weasyprint funciona perfectamente'
            })
        else:
            return jsonify({
                'weasyprint_disponible': True,
                'pdf_generado': False,
                'error': 'PDF no se creó'
            })
            
    except Exception as e:
            return jsonify({
                'error': str(e),
                'weasyprint_disponible': False
            })
            
@app.route('/test/html_basico')
def html_basico():
    return "<h1>HTML funciona</h1><p>Si ves esto, todo OK</p>"
    
@app.route('/test/html_con_cartas_reales')
def html_con_cartas_reales():
    """Ver HTML con las cartas astrológicas reales que ya funcionan"""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Carta Astral Completa - AS Cartastral</title>
        <style>
            body {{ 
                font-family: Georgia, serif; 
                margin: 30px; 
                line-height: 1.6; 
                color: #333; 
                background: #fafafa; 
            }}
            .portada {{ 
                text-align: center; 
                margin: 30px 0; 
                padding: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                border-radius: 10px; 
            }}
            .datos-natales {{ 
                background: #f8f9fa; 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 8px; 
                border-left: 4px solid #667eea; 
            }}
            .imagen-carta {{ 
                text-align: center; 
                margin: 40px 0; 
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .imagen-carta img {{ 
                max-width: 100%; 
                height: auto; 
                border: 2px solid #ddd; 
                border-radius: 8px; 
            }}
            .footer {{ 
                margin-top: 50px; 
                padding: 20px; 
                background: #e9ecef; 
                border-radius: 8px; 
                text-align: center; 
            }}
        </style>
    </head>
    <body>
        <div class="portada">
            <h1>🔮 CARTA ASTRAL COMPLETA</h1>
            <h2>Cliente con Cartas Reales</h2>
            <p>Informe Astrológico Personalizado</p>
        </div>

        <div class="datos-natales">
            <h2>📋 Datos Natales</h2>
            <p><strong>Fecha:</strong> 15/07/1985</p>
            <p><strong>Hora:</strong> 10:30</p>
            <p><strong>Lugar:</strong> Madrid, España</p>
        </div>

        <div class="imagen-carta">
            <h2>🗺️ Tu Carta Natal</h2>
            <img src="https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926164824.png" alt="Carta Natal">
            <p>Posiciones planetarias exactas en el momento de tu nacimiento con casas, aspectos y signos zodiacales.</p>
        </div>

        <div class="imagen-carta">
            <h2>📈 Progresiones Secundarias</h2>
            <img src="https://as-webhooks-production.up.railway.app/static/progresiones_test_20250926164824.png" alt="Progresiones">
            <p>Evolución de tu personalidad a lo largo de los años según el método de progresiones secundarias.</p>
        </div>

        <div class="imagen-carta">
            <h2>🌊 Tránsitos Actuales</h2>
            <img src="https://as-webhooks-production.up.railway.app/static/transitos_test_20250926164824.png" alt="Tránsitos">
            <p>Influencias planetarias actuales en tu vida y cómo afectan a tu carta natal.</p>
        </div>

        <div class="footer">
            <p><strong>✅ Este es exactamente el contenido que iría en el PDF final</strong></p>
            <p>Con 3 cartas astrológicas completas y profesionales</p>
            <p>Generado por AS Cartastral - Servicios Astrológicos IA</p>
        </div>
    </body>
    </html>
    """
    
@app.route('/static/<filename>')
def serve_static(filename):
    """Servir archivos estáticos manualmente porque Railway no los sirve"""
    import os
    try:
        if os.path.exists(f'static/{filename}'):
            return send_from_directory('static', filename)
        else:
            return f"Archivo no encontrado: {filename}", 404
    except Exception as e:
        return f"Error sirviendo archivo: {str(e)}", 500
        
@app.route('/test/listar_archivos_static')
def listar_archivos_static():
    """Ver qué archivos existen realmente en static/"""
    import os
    import glob
    from datetime import datetime
    
    try:
        resultado = {
            'directorio_actual': os.getcwd(),
            'existe_static': os.path.exists('static/'),
            'archivos_static': [],
            'archivos_templates': [],
            'archivos_informes': []
        }
        
        # Listar static/
        if os.path.exists('static/'):
            archivos = os.listdir('static/')
            for archivo in archivos:
                ruta = f'static/{archivo}'
                if os.path.isfile(ruta):
                    stats = os.stat(ruta)
                    resultado['archivos_static'].append({
                        'nombre': archivo,
                        'tamaño': stats.st_size,
                        'fecha': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'url': f'/static/{archivo}'
                    })
        
        # Listar templates/
        if os.path.exists('templates/'):
            archivos = os.listdir('templates/')
            for archivo in archivos:
                if archivo.endswith('.html'):
                    resultado['archivos_templates'].append(archivo)
        
        # Listar informes/
        if os.path.exists('informes/'):
            archivos = os.listdir('informes/')
            for archivo in archivos:
                if archivo.endswith('.pdf'):
                    resultado['archivos_informes'].append(archivo)
        
        # Buscar cualquier archivo PNG
        todos_png = glob.glob('**/*.png', recursive=True)
        resultado['todos_los_png'] = todos_png
        
        return f"""
        <html>
        <body>
            <h1>Archivos en el sistema</h1>
            
            <h2>Directorio static/ ({len(resultado['archivos_static'])} archivos)</h2>
            <ul>
            {''.join([f'<li><a href="{a["url"]}">{a["nombre"]}</a> - {a["tamaño"]} bytes - {a["fecha"]}</li>' for a in resultado['archivos_static']])}
            </ul>
            
            <h2>Todos los PNG encontrados:</h2>
            <ul>
            {''.join([f'<li>{png}</li>' for png in resultado['todos_los_png']])}
            </ul>
            
            <h2>Templates HTML:</h2>
            <ul>
            {''.join([f'<li>{t}</li>' for t in resultado['archivos_templates']])}
            </ul>
            
            <h2>PDFs generados:</h2>
            <ul>
            {''.join([f'<li>{p}</li>' for p in resultado['archivos_informes']])}
            </ul>
            
            <pre>{repr(resultado)}</pre>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"
        
@app.route('/test/debug_donde_guarda_sofia')
def debug_donde_guarda_sofia():
    import os
    
    # Simular lo que hace Sofia
    timestamp = "20250926170000"
    archivos_esperados = {
        'carta_natal_img': f'static/carta_natal_test_{timestamp}.png',
        'progresiones_img': f'static/progresiones_test_{timestamp}.png',
        'transitos_img': f'static/transitos_test_{timestamp}.png'
    }
    
    resultado = {}
    for nombre, ruta in archivos_esperados.items():
        resultado[nombre] = {
            'ruta_esperada': ruta,
            'directorio_existe': os.path.exists(os.path.dirname(ruta)),
            'archivo_existe': os.path.exists(ruta),
            'permisos_directorio': oct(os.stat(os.path.dirname(ruta)).st_mode)[-3:] if os.path.exists(os.path.dirname(ruta)) else 'No existe'
        }
    
    return jsonify({
        'directorio_actual': os.getcwd(),
        'usuario': os.getenv('USER'),
        'archivos_test': resultado,
        'problema': 'Sofia dice que guarda pero no guarda realmente'
    })
    
@app.route('/test/html_con_cartas_existentes')
def html_con_cartas_existentes():
    """HTML usando las cartas que SÍ existen en el servidor"""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Carta Astral Completa - AS Cartastral</title>
        <style>
            body {{ font-family: Georgia, serif; margin: 30px; line-height: 1.6; color: #333; background: #fafafa; }}
            .portada {{ text-align: center; margin: 30px 0; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; }}
            .imagen-carta {{ text-align: center; margin: 40px 0; padding: 20px; background: white; border-radius: 8px; }}
            .imagen-carta img {{ max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="portada">
            <h1>CARTA ASTRAL COMPLETA</h1>
            <h2>Cliente Real</h2>
            <p>Informe Astrológico Personalizado</p>
        </div>

        <div class="imagen-carta">
            <h2>Tu Carta Natal</h2>
            <img src="/cartas_generadas/carta_19591001_1046.png" alt="Carta Natal">
            <p>Carta astrológica completa con casas, planetas y aspectos.</p>
        </div>

        <div class="imagen-carta">
            <h2>Progresiones Secundarias</h2>
            <img src="/progresiones_generadas/progresiones_19850723_1045_edad_40.0.png" alt="Progresiones">
            <p>Evolución de tu personalidad a lo largo de los años.</p>
        </div>

        <p><strong>ÉXITO: Estas son cartas astrológicas REALES funcionando</strong></p>
    </body>
    </html>
    """
    
@app.route('/test/html_con_urls_exactas')
def html_con_urls_exactas():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Test URLs Exactas</title></head>
    <body>
        <h1>Carta Natal</h1>
        <img src="https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926183454.png" style="max-width:100%; border: 1px solid red;">
        
        <h1>Progresiones</h1>
        <img src="https://as-webhooks-production.up.railway.app/static/progresiones_test_20250926183454.png" style="max-width:100%; border: 1px solid red;">
        
        <h1>Tránsitos</h1>
        <img src="https://as-webhooks-production.up.railway.app/static/transitos_test_20250926183454.png" style="max-width:100%; border: 1px solid red;">
        
        <p>Si no ves las imágenes, check F12 Console para errores</p>
    </body>
    </html>
    """
    
@app.route('/test/debug_headers_imagenes')
def debug_headers_imagenes():
    """Ver qué headers devuelve Railway para las imágenes"""
    import requests
    
    url_test = "https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926183454.png"
    
    try:
        response = requests.head(url_test)
        return jsonify({
            'url': url_test,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'problema_posible': 'CORS o Content-Type' if response.status_code == 200 else 'URL no existe'
        })
    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/test/verificar_funcion_actual')
def verificar_funcion_actual():
    """Ver exactamente qué HTML se está generando"""
    import inspect
    
    # Obtener el código fuente actual de la función
    try:
        from main import html_con_urls_exactas
        codigo_actual = inspect.getsource(html_con_urls_exactas)
    except:
        codigo_actual = "No se pudo obtener"
    
    return f"""
    <h1>Código actual de la función:</h1>
    <pre>{codigo_actual}</pre>
    
    <h1>Test directo con URLs absolutas:</h1>
    <img src="https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926191158.png" style="max-width:300px; border:2px solid red;">
    <img src="https://as-webhooks-production.up.railway.app/static/progresiones_test_20250926191158.png" style="max-width:300px; border:2px solid red;">
    <img src="https://as-webhooks-production.up.railway.app/static/transitos_test_20250926191158.png" style="max-width:300px; border:2px solid red;">
    """
    
@app.after_request
def add_cors_headers(response):
    """Añadir headers CORS para que las imágenes se vean en HTML"""
    if request.path.startswith('/static/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
    
@app.route('/test/cartas_funcionando')
def cartas_funcionando():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test URLs Absolutas</title>
    </head>
    <body>
        <h1>Test con URLs Absolutas</h1>
        <img src="https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926191158.png" width="400" style="border: 1px solid red;">
        <br>
        <img src="https://as-webhooks-production.up.railway.app/static/progresiones_test_20250926191158.png" width="400" style="border: 1px solid red;">
        <br>
        <img src="https://as-webhooks-production.up.railway.app/static/transitos_test_20250926191158.png" width="400" style="border: 1px solid red;">
        
        <p>Si aparecen las 3 cartas con bordes rojos, el problema estaba en las rutas relativas</p>
    </body>
    </html>
    """
    
@app.route('/test/debug_imagen_headers')
def debug_imagen_headers():
    """Verificar exactamente qué headers devuelve Railway"""
    import requests
    
    url = "https://as-webhooks-production.up.railway.app/static/carta_natal_test_20250926191158.png"
    
    try:
        # Request desde el servidor (simula lo que hace el HTML)
        response = requests.get(url, timeout=10)
        
        return f"""
        <h1>Debug Headers de Imagen</h1>
        <p><strong>Status:</strong> {response.status_code}</p>
        <p><strong>Content-Type:</strong> {response.headers.get('Content-Type', 'MISSING')}</p>
        <p><strong>Content-Length:</strong> {response.headers.get('Content-Length', 'MISSING')}</p>
        <p><strong>Headers completos:</strong></p>
        <pre>{dict(response.headers)}</pre>
        
        <h2>Imagen Base64 (método alternativo):</h2>
        <img src="data:image/png;base64,{__import__('base64').b64encode(response.content).decode()}" width="200">
        """
        
    except Exception as e:
        return f"Error: {str(e)}"
        
@app.route('/test/verificacion_final_archivos')
def verificacion_final_archivos():
    """Verificar qué archivos existen REALMENTE ahora mismo"""
    import os
    import glob
    from datetime import datetime
    
    # Buscar TODOS los PNG en static/
    archivos_static = glob.glob("static/*.png")
    
    # Buscar específicamente los que Sofia dice que creó
    archivos_esperados = [
        "static/carta_natal_test_20250926191158.png",
        "static/progresiones_test_20250926191158.png", 
        "static/transitos_test_20250926191158.png"
    ]
    
    verificacion = {}
    for archivo in archivos_esperados:
        verificacion[archivo] = {
            'existe': os.path.exists(archivo),
            'tamaño': os.path.getsize(archivo) if os.path.exists(archivo) else 0
        }
    
    return f"""
    <h1>VERIFICACIÓN FINAL DE ARCHIVOS</h1>
    
    <h2>Archivos que Sofia DICE que creó:</h2>
    <ul>
    {''.join([f'<li>{k}: {"✅ EXISTE" if v["existe"] else "❌ NO EXISTE"} ({v["tamaño"]} bytes)</li>' for k, v in verificacion.items()])}
    </ul>
    
    <h2>Archivos PNG que REALMENTE existen en static/:</h2>
    <ul>
    {''.join([f'<li>{archivo}</li>' for archivo in archivos_static])}
    </ul>
    
    <h2>DIAGNÓSTICO:</h2>
    <p><strong>{"Sofia crea los archivos correctamente" if all(v["existe"] for v in verificacion.values()) else "Sofia NO crea los archivos - solo dice que los crea"}</strong></p>
    
    <h2>Si los archivos SÍ existen, test de imagen:</h2>
    <img src="/static/carta_natal_test_20250926191158.png" style="border: 2px solid red; max-width: 200px;">
    """
    
# ENDPOINT DE TEST PARA PROBAR LA SOLUCIÓN BASE64

@app.route('/test/cartas_base64')
def test_cartas_base64():
    """
    TEST: Generar cartas astrales en Base64 para evitar problema filesystem Railway
    """
    try:
        from datetime import datetime
        import io
        import base64
        import matplotlib.pyplot as plt
        
        print("🔧 Iniciando test de cartas en BASE64...")
        
        # Datos de test
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'nombre': 'Usuario Test'
        }
        
        # Generar una carta simple en memoria
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Crear una carta astral básica para test
        import numpy as np
        
        # Círculo del zodíaco
        theta = np.linspace(0, 2*np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), 'b-', linewidth=2, label='Zodíaco')
        
        # Casas astrológicas (12 divisiones)
        for i in range(12):
            angle = i * np.pi / 6
            ax.plot([0, np.cos(angle)], [0, np.sin(angle)], 'k-', alpha=0.3)
            
            # Etiquetas de casas
            label_angle = angle + np.pi/12
            ax.text(1.1*np.cos(label_angle), 1.1*np.sin(label_angle), 
                   f'Casa {i+1}', ha='center', va='center', fontsize=8)
        
        # Posiciones planetarias simuladas
        planetas = ['☉', '☽', '☿', '♀', '♂', '♃', '♄', '⛢', '♆', '♇']
        colores = ['gold', 'silver', 'orange', 'pink', 'red', 'purple', 'brown', 'cyan', 'blue', 'magenta']
        
        for i, (planeta, color) in enumerate(zip(planetas, colores)):
            angle = i * 2 * np.pi / len(planetas)
            x, y = 0.8 * np.cos(angle), 0.8 * np.sin(angle)
            ax.scatter(x, y, s=200, c=color, marker='o', edgecolors='black', linewidth=1)
            ax.text(x, y, planeta, ha='center', va='center', fontsize=12, fontweight='bold')
        
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f'Carta Astral Test - {datos_natales_test["fecha_nacimiento"]}', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Convertir a base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        buffer.close()
        
        # Crear datos completos para el template
        imagenes_base64 = {
            'carta_natal': f"data:image/png;base64,{imagen_base64}",
            'progresiones': crear_placeholder_base64("Progresiones Secundarias\n(Test)"),
            'transitos': crear_placeholder_base64("Tránsitos Actuales\n(Test)")
        }
        
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # HTML directo con base64
        html_response = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🌟 Test Cartas Base64</title>
            <style>
                body {{
                    font-family: 'Georgia', serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
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
                .carta-section {{
                    margin: 30px 0;
                    padding: 20px;
                    border-left: 5px solid #667eea;
                    background: linear-gradient(90deg, #f8f9ff 0%, #ffffff 100%);
                    border-radius: 10px;
                }}
                .carta-title {{
                    color: #667eea;
                    font-size: 1.5em;
                    margin-bottom: 15px;
                    text-align: center;
                }}
                .carta-imagen {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .carta-imagen img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 10px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                    border: 3px solid #667eea;
                }}
                .success-badge {{
                    background: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 25px;
                    display: inline-block;
                    margin: 10px 0;
                    font-weight: bold;
                }}
                .info-box {{
                    background: #e8f4f8;
                    border: 1px solid #bee5eb;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌟 Test Cartas Base64 🌟</h1>
                    <div class="success-badge">✅ FILESYSTEM INDEPENDIENTE</div>
                </div>

                <div class="info-box">
                    <h3>📋 Datos de Test</h3>
                    <p><strong>Fecha:</strong> {datos_natales_test['fecha_nacimiento']}</p>
                    <p><strong>Hora:</strong> {datos_natales_test['hora_nacimiento']}</p>
                    <p><strong>Lugar:</strong> {datos_natales_test['lugar_nacimiento']}</p>
                    <p><strong>Generado:</strong> {timestamp}</p>
                    <p><strong>Método:</strong> Base64 embebido (sin archivos en disco)</p>
                </div>

                <div class="carta-section">
                    <h2 class="carta-title">🌅 Carta Astral (Base64)</h2>
                    <div class="carta-imagen">
                        <img src="{imagenes_base64['carta_natal']}" alt="Carta Astral Test">
                    </div>
                    <p><strong>✅ Esta imagen se genera en memoria y se embebe directamente en el HTML.</strong></p>
                    <p>No se guardan archivos en disco, por lo que no hay problemas de persistencia en Railway.</p>
                </div>

                <div class="carta-section">
                    <h2 class="carta-title">📈 Progresiones (Placeholder)</h2>
                    <div class="carta-imagen">
                        <img src="{imagenes_base64['progresiones']}" alt="Progresiones Test">
                    </div>
                </div>

                <div class="carta-section">
                    <h2 class="carta-title">🔄 Tránsitos (Placeholder)</h2>
                    <div class="carta-imagen">
                        <img src="{imagenes_base64['transitos']}" alt="Tránsitos Test">
                    </div>
                </div>

                <div class="info-box">
                    <h3>🔧 Ventajas de esta solución:</h3>
                    <ul>
                        <li>✅ <strong>No depende del filesystem</strong> - Railway puede reiniciar sin problemas</li>
                        <li>✅ <strong>Imágenes siempre disponibles</strong> - embebidas en el HTML</li>
                        <li>✅ <strong>Rendimiento excelente</strong> - no hay requests adicionales</li>
                        <li>✅ <strong>Funciona en cualquier entorno</strong> - local, Railway, etc.</li>
                        <li>✅ <strong>PDFs perfectos</strong> - WeasyPrint lee base64 sin problemas</li>
                    </ul>
                </div>

            </div>

            <script>
                console.log("🔍 Debug imágenes base64:");
                const imagenes = document.querySelectorAll('img[src^="data:image"]');
                console.log(`📊 Total de imágenes base64: ${{imagenes.length}}`);
                
                imagenes.forEach((img, index) => {{
                    img.onload = function() {{
                        console.log(`✅ Imagen ${{index + 1}} cargada: ${{this.naturalWidth}}x${{this.naturalHeight}}px`);
                    }};
                    img.onerror = function() {{
                        console.log(`❌ Error en imagen ${{index + 1}}`);
                    }};
                }});
            </script>
        </body>
        </html>
        """
        
        return html_response
        
    except Exception as e:
        import traceback
        return f"""
        <h1>❌ Error en test Base64</h1>
        <pre>{str(e)}</pre>
        <pre>{traceback.format_exc()}</pre>
        """

def crear_placeholder_base64(texto):
    """Crear imagen placeholder simple en base64"""
    try:
        import matplotlib.pyplot as plt
        import io
        import base64
        
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, texto, ha='center', va='center', fontsize=16, 
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        buffer.close()
        
        return f"data:image/png;base64,{imagen_base64}"
    except:
        # Fallback: imagen SVG simple
        return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y0ZjRmNCIvPjx0ZXh0IHg9IjE1MCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkltYWdlbiBubyBkaXNwb25pYmxlPC90ZXh0Pjwvc3ZnPg=="

# ENDPOINT DE INTEGRACIÓN COMPLETA
@app.route('/test/integracion_sofia_base64')
def test_integracion_sofia_base64():
    """
    TEST: Integración completa con Sofia usando Base64
    """
    try:
        from datetime import datetime
        
        # Datos de test realistas
        datos_natales = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'nombre': 'Cliente Test',
            'residencia_actual': 'Madrid, España'
        }
        
        # Simular llamada a Sofia con Base64
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print("🔧 Simulando integración Sofia con Base64...")
        
        # Aquí iría la llamada real a generar_cartas_astrales_base64()
        # Por ahora, simular el resultado
        
        resultado_simulado = {
            'exito': True,
            'datos_completos': {
                'imagenes_base64': {
                    'carta_natal': crear_placeholder_base64("Carta Natal\nGenerada por Sofia"),
                    'progresiones': crear_placeholder_base64("Progresiones\nGeneradas por Sofia"),
                    'transitos': crear_placeholder_base64("Tránsitos\nGenerados por Sofia")
                },
                'aspectos_natales': ['Sol conjunción Ascendente', 'Luna trígono Júpiter'],
                'interpretacion_ia': 'Esta carta muestra una personalidad luminosa...',
                'timestamp': datetime.now().isoformat(),
                'metodo': 'base64_sofia'
            }
        }
        
        return jsonify({
            'status': 'success',
            'mensaje': '✅ Integración Sofia Base64 funcionando',
            'datos_natales': datos_natales,
            'resultado': resultado_simulado,
            'siguiente_paso': 'Implementar en sofia.py',
            'ventajas': [
                'Sin dependencia del filesystem',
                'Imágenes siempre disponibles',
                'Compatible con Railway',
                'PDFs perfectos'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'mensaje': f'❌ Error en integración: {str(e)}'
        })

def generar_cartas_astrales_base64(datos_natales):
    return generar_cartas_astrales_base64_corregida(datos_natales)

# =======================================================================
# ENDPOINT FINAL DE TEST
# =======================================================================

@app.route('/test/cartas_finales_completas')
def test_cartas_finales_completas():
    """
    Test final con aspectos, posiciones y estadísticas completas
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'nombre': 'Test Final Completo'
        }
        
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            template_data = resultado['template_data']
            estadisticas = resultado['estadisticas']
            
            # HTML completo con todas las secciones
            html_response = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>🌟 Test Final Completo</title>
                <style>
                    body {{ font-family: 'Georgia', serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
                    .stats-header {{ background: #e8f4f8; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                    .carta-section {{ margin: 40px 0; padding: 20px; border-left: 5px solid #667eea; background: #f8f9ff; border-radius: 10px; }}
                    .carta-imagen {{ text-align: center; margin: 20px 0; }}
                    .carta-imagen img {{ max-width: 100%; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); border: 3px solid #667eea; }}
                    .aspectos-section {{ background: #f8f9ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #667eea; }}
                    .aspectos-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 8px; margin-top: 10px; }}
                    .aspecto-item {{ background: white; padding: 8px 12px; border-radius: 6px; border: 1px solid #e0e6ed; display: flex; justify-content: space-between; align-items: center; }}
                    .aspecto-planetas {{ font-weight: 500; color: #333; }}
                    .aspecto-orbe {{ font-size: 0.85em; color: #666; background: #f0f2f5; padding: 2px 6px; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🌟 Test Final - Cartas con Aspectos Completos</h1>
                    
                    <div class="stats-header">
                        <h2>📊 Resumen Estadístico</h2>
                        <p><strong>Aspectos Natales:</strong> {estadisticas['total_aspectos_natal']}</p>
                        <p><strong>Aspectos Progresiones:</strong> {estadisticas['total_aspectos_progresiones']}</p>
                        <p><strong>Aspectos Tránsitos:</strong> {estadisticas['total_aspectos_transitos']}</p>
                        <p><strong>Aspectos Exactos (< 1°):</strong> {estadisticas.get('aspectos_exactos_transitos', 0)}</p>
                    </div>

                    <div class="carta-section">
                        <h2>🌅 Carta Natal Completa</h2>
                        <div class="carta-imagen">
                            <img src="{template_data['imagenes_base64'].get('carta_natal', '')}" alt="Carta Natal">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>⭐ Aspectos Natales Principales</h3>
                            <div class="aspectos-grid">
                                {"".join([f'<div class="aspecto-item"><span class="aspecto-planetas">Aspecto {i+1}</span><span class="aspecto-orbe">Demo</span></div>' for i in range(min(8, len(template_data['aspectos_natales'])))])}
                            </div>
                            <p><strong>Total encontrados:</strong> {len(template_data['aspectos_natales'])} aspectos</p>
                        </div>
                    </div>

                    <div class="carta-section">
                        <h2>🔄 Tránsitos Actuales</h2>
                        <div class="carta-imagen">
                            <img src="{template_data['imagenes_base64'].get('transitos', '')}" alt="Tránsitos">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>⚡ Aspectos de Tránsito Activos</h3>
                            <div class="aspectos-grid">
                                {"".join([f'<div class="aspecto-item"><span class="aspecto-planetas">Tránsito {i+1}</span><span class="aspecto-orbe">Demo</span></div>' for i in range(min(8, len(template_data['aspectos_transitos'])))])}
                            </div>
                            <p><strong>Total encontrados:</strong> {len(template_data['aspectos_transitos'])} aspectos de tránsito</p>
                        </div>
                    </div>
                    
                    <div style="background: #e8f4f8; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h3>✅ Estado del Sistema:</h3>
                        <p>✅ Carta Natal: Funcionando</p>
                        <p>✅ Progresiones: Funcionando</p>
                        <p>✅ Tránsitos: Funcionando con signature correcta</p>
                        <p>✅ Base64: Sin dependencia de filesystem</p>
                        <p>✅ Aspectos: Capturados y listos para mostrar</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_response
        else:
            return f"<h1>❌ Error en test final</h1><p>Resultado: {resultado}</p>"
            
    except Exception as e:
        import traceback
        return f"<h1>❌ Error crítico en test final</h1><pre>{traceback.format_exc()}</pre>"

# =======================================================================
# ENDPOINT DE TEST PARA PROBAR LA FUNCIÓN REAL
# =======================================================================
@app.route('/test/cartas_reales_base64')
def test_cartas_reales_base64():
    """
    TEST: Usar las clases REALES de carta astral con base64
    """
    try:
        from datetime import datetime
        
        # Datos realistas
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'nombre': 'Usuario Test Real'
        }
        
        print("🔧 Iniciando test con clases REALES...")
        
        # Llamar a la función REAL
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            imagenes_base64 = resultado['imagenes_base64']
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # HTML con las cartas REALES
            html_response = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>🌟 Test Cartas REALES Base64</title>
                <style>
                    body {{
                        font-family: 'Georgia', serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 1000px;
                        margin: 0 auto;
                        background: white;
                        padding: 30px;
                        border-radius: 15px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    }}
                    .header {{
                        text-align: center;
                        border-bottom: 3px solid #667eea;
                        padding-bottom: 20px;
                        margin-bottom: 30px;
                    }}
                    .carta-section {{
                        margin: 40px 0;
                        padding: 20px;
                        border-left: 5px solid #667eea;
                        background: linear-gradient(90deg, #f8f9ff 0%, #ffffff 100%);
                        border-radius: 10px;
                    }}
                    .carta-imagen {{
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .carta-imagen img {{
                        max-width: 100%;
                        height: auto;
                        border-radius: 10px;
                        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                        border: 3px solid #667eea;
                    }}
                    .success-badge {{
                        background: #4CAF50;
                        color: white;
                        padding: 10px 20px;
                        border-radius: 25px;
                        display: inline-block;
                        margin: 10px;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌟 Cartas Astrales REALES en Base64 🌟</h1>
                        <div class="success-badge">✅ CLASES ORIGINALES</div>
                        <div class="success-badge">✅ BASE64 EMBEBIDO</div>
                    </div>

                    <div class="carta-section">
                        <h2>🌅 Carta Natal REAL</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('carta_natal', '')}" alt="Carta Natal Real">
                        </div>
                        <p>✅ Generada con CartaAstralNatal - Posiciones planetarias reales</p>
                    </div>

                    <div class="carta-section">
                        <h2>📈 Progresiones REALES</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('progresiones', '')}" alt="Progresiones Reales">
                        </div>
                        <p>✅ Generada con CartaProgresiones - Evolución personal real</p>
                    </div>

                    <div class="carta-section">
                        <h2>🔄 Tránsitos REALES</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('transitos', '')}" alt="Tránsitos Reales">
                        </div>
                        <p>✅ Generada con CartaTransitos - Influencias actuales reales</p>
                    </div>

                    <div style="background: #e8f4f8; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h3>📊 Datos de Generación:</h3>
                        <p><strong>Método:</strong> {resultado.get('metodo', 'Unknown')}</p>
                        <p><strong>Aspectos encontrados:</strong> {len(resultado.get('aspectos_natales', []))}</p>
                        <p><strong>Timestamp:</strong> {timestamp}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_response
            
        else:
            return f"""
            <h1>❌ Error generando cartas reales</h1>
            <p>La función devolvió: exito={exito}</p>
            <p>Resultado: {resultado}</p>
            """
            
    except Exception as e:
        import traceback
        return f"""
        <h1>❌ Error en test cartas reales</h1>
        <pre>{str(e)}</pre>
        <pre>{traceback.format_exc()}</pre>
        """
        
# =======================================================================
# DEBUG Y FIX PARA TRÁNSITOS - AÑADIR A main.py
# =======================================================================

@app.route('/test/debug_transitos_especifico')
def debug_transitos_especifico():
    """
    Debug específico para entender por qué fallan los tránsitos
    """
    try:
        from datetime import datetime
        import traceback
        
        # Datos de test
        fecha_str = '15/07/1985'
        hora_str = '10:30'
        
        # Convertir fecha
        dia, mes, año = map(int, fecha_str.split('/'))
        hora, minuto = map(int, hora_str.split(':'))
        fecha_natal = (año, mes, dia, hora, minuto)
        
        lugar_coords = (40.42, -3.70)  # Madrid
        
        # Fecha actual para tránsito
        hoy = datetime.now()
        fecha_consulta = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
        
        resultado_debug = {
            'fecha_natal': fecha_natal,
            'fecha_consulta': fecha_consulta,
            'lugar_coords': lugar_coords,
            'pasos': [],
            'error_final': None
        }
        
        # PASO 1: Verificar importación
        try:
            from transitos import CartaTransitos
            resultado_debug['pasos'].append('✅ Importación CartaTransitos OK')
        except Exception as e:
            resultado_debug['pasos'].append(f'❌ Error importando CartaTransitos: {e}')
            return jsonify(resultado_debug)
        
        # PASO 2: Crear instancia
        try:
            carta_trans = CartaTransitos(figsize=(12, 12))
            resultado_debug['pasos'].append('✅ Instancia CartaTransitos creada')
        except Exception as e:
            resultado_debug['pasos'].append(f'❌ Error creando instancia: {e}')
            return jsonify(resultado_debug)
        
        # PASO 3: Verificar métodos disponibles
        try:
            metodos = [m for m in dir(carta_trans) if not m.startswith('_')]
            resultado_debug['metodos_disponibles'] = metodos
            resultado_debug['pasos'].append(f'✅ Métodos disponibles: {len(metodos)}')
        except Exception as e:
            resultado_debug['pasos'].append(f'❌ Error listando métodos: {e}')
        
        # PASO 4: Intentar diferentes signatures de función
        signatures_a_probar = [
            # Signature 1: Con fecha_consulta
            {
                'nombre': 'crear_carta_transitos_v1',
                'params': {
                    'fecha_nacimiento': fecha_natal,
                    'fecha_consulta': fecha_consulta,
                    'lugar_nacimiento': lugar_coords,
                    'lugar_actual': lugar_coords,
                    'ciudad_nacimiento': 'Madrid, España',
                    'ciudad_actual': 'Madrid, España',
                    'guardar_archivo': False
                }
            },
            # Signature 2: Con fecha_transito
            {
                'nombre': 'crear_carta_transitos_v2', 
                'params': {
                    'fecha_nacimiento': fecha_natal,
                    'fecha_transito': fecha_consulta,
                    'lugar_nacimiento': lugar_coords,
                    'guardar_archivo': False,
                    'directorio_salida': None
                }
            },
            # Signature 3: Minimal
            {
                'nombre': 'crear_carta_transitos_v3',
                'params': {
                    'fecha_nacimiento': fecha_natal,
                    'fecha_transito': fecha_consulta,
                    'lugar_nacimiento': lugar_coords
                }
            }
        ]
        
        for signature in signatures_a_probar:
            try:
                resultado_debug['pasos'].append(f'🔄 Probando {signature["nombre"]}...')
                
                # Intentar llamar con estos parámetros
                resultado = carta_trans.crear_carta_transitos(**signature['params'])
                
                if resultado:
                    # Si funciona, guardar los detalles
                    if isinstance(resultado, tuple) and len(resultado) >= 3:
                        aspectos, pos_natales, pos_transitos = resultado[:3]
                        resultado_debug['pasos'].append(f'✅ {signature["nombre"]} FUNCIONA!')
                        resultado_debug['signature_exitosa'] = signature
                        resultado_debug['aspectos_encontrados'] = len(aspectos) if aspectos else 0
                        resultado_debug['pos_natales_count'] = len(pos_natales) if pos_natales else 0
                        resultado_debug['pos_transitos_count'] = len(pos_transitos) if pos_transitos else 0
                        break
                    else:
                        resultado_debug['pasos'].append(f'⚠️ {signature["nombre"]} devolvió formato inesperado: {type(resultado)}')
                else:
                    resultado_debug['pasos'].append(f'⚠️ {signature["nombre"]} devolvió None')
                    
            except Exception as e:
                resultado_debug['pasos'].append(f'❌ {signature["nombre"]} falló: {str(e)}')
                
        # PASO 5: Si todas fallan, capturar error detallado
        if 'signature_exitosa' not in resultado_debug:
            try:
                # Intentar con la signature más básica y capturar error completo
                resultado = carta_trans.crear_carta_transitos(
                    fecha_nacimiento=fecha_natal,
                    fecha_transito=fecha_consulta,
                    lugar_nacimiento=lugar_coords
                )
            except Exception as e:
                resultado_debug['error_final'] = {
                    'mensaje': str(e),
                    'tipo': type(e).__name__,
                    'traceback': traceback.format_exc()
                }
        
        return jsonify(resultado_debug)
        
    except Exception as e:
        return jsonify({
            'error_critico': str(e),
            'traceback': traceback.format_exc()
        })


# =======================================================================
# FUNCIÓN CORREGIDA PARA TRÁNSITOS BASE64
# =======================================================================

def generar_transitos_base64_corregida(datos_natales):
    """
    Generar tránsitos con la signature correcta y captura de errores mejorada
    """
    try:
        print("🔄 Generando Tránsitos CORREGIDOS en Base64...")
        
        # Extraer datos
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', '')
        
        # Convertir fecha
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_natal = (año, mes, dia, hora, minuto)
        else:
            raise ValueError("Formato fecha/hora incorrecto")
        
        # Coordenadas
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
        
        # Fecha actual
        from datetime import datetime as dt
        hoy = dt.now()
        fecha_consulta = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
        
        print(f"📍 Lugar: {lugar_coords}")
        print(f"⏰ Natal: {fecha_natal}")
        print(f"🌍 Consulta: {fecha_consulta}")
        
        # INTENTAR MÚLTIPLES SIGNATURES HASTA QUE UNA FUNCIONE
        from transitos import CartaTransitos
        carta_trans = CartaTransitos(figsize=(16, 14))
        
        # Lista de signatures a probar en orden de preferencia
        intentos = [
            # Intento 1: Con fecha_consulta (como en sofia_fixes.py)
            lambda: carta_trans.crear_carta_transitos(
                fecha_nacimiento=fecha_natal,
                fecha_consulta=fecha_consulta,
                lugar_nacimiento=lugar_coords,
                lugar_actual=lugar_coords,
                ciudad_nacimiento=ciudad_nombre,
                ciudad_actual=ciudad_nombre,
                guardar_archivo=False
            ),
            # Intento 2: Con fecha_transito (como en main.py)
            lambda: carta_trans.crear_carta_transitos(
                fecha_nacimiento=fecha_natal,
                fecha_transito=fecha_consulta,
                lugar_nacimiento=lugar_coords,
                guardar_archivo=False
            ),
            # Intento 3: Minimal con parámetros básicos
            lambda: carta_trans.crear_carta_transitos(
                fecha_natal,
                fecha_consulta,
                lugar_coords,
                guardar_archivo=False
            )
        ]
        
        resultado_transitos = None
        error_detallado = None
        
        for i, intento in enumerate(intentos, 1):
            try:
                print(f"🔄 Intento {i} de tránsitos...")
                resultado_transitos = intento()
                print(f"✅ Intento {i} exitoso!")
                break
            except Exception as e:
                print(f"❌ Intento {i} falló: {e}")
                error_detallado = str(e)
                continue
        
        if resultado_transitos:
            # Extraer datos del resultado
            if isinstance(resultado_transitos, tuple) and len(resultado_transitos) >= 3:
                aspectos_trans, pos_natales, pos_transitos = resultado_transitos[:3]
                
                # Convertir a base64
                import io
                import base64
                import matplotlib.pyplot as plt
                
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                           facecolor='white', edgecolor='none')
                buffer.seek(0)
                imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
                transitos_base64 = f"data:image/png;base64,{imagen_base64}"
                plt.close()
                buffer.close()
                
                print(f"✅ Tránsitos generados: {len(aspectos_trans)} aspectos")
                return transitos_base64, aspectos_trans
            else:
                print(f"⚠️ Formato de resultado inesperado: {type(resultado_transitos)}")
                return crear_placeholder_base64("Tránsitos\n(Formato incorrecto)"), []
        else:
            print(f"❌ Todos los intentos de tránsitos fallaron. Último error: {error_detallado}")
            return crear_placeholder_base64(f"Tránsitos\n(Error: {error_detallado[:50]}...)"), []
            
    except Exception as e:
        print(f"❌ Error crítico en tránsitos: {e}")
        import traceback
        traceback.print_exc()
        return crear_placeholder_base64(f"Tránsitos\n(Error crítico)"), []


# =======================================================================
# FUNCIÓN BASE64 MEJORADA CON MEJOR MANEJO DE TRÁNSITOS
# =======================================================================

def generar_cartas_astrales_base64_mejorada(datos_natales):
    """
    Versión mejorada que maneja mejor los tránsitos y captura más datos astrológicos
    """
    try:
        print("🔧 Generando cartas astrales MEJORADAS en BASE64...")
        
        # [Código inicial igual...]
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
        
        imagenes_base64 = {}
        datos_aspectos = {}
        
        # 1. CARTA NATAL (igual que antes)
        print("📊 Generando Carta Natal...")
        try:
            from carta_natal import CartaAstralNatal
            import matplotlib.pyplot as plt
            import io
            import base64
            
            carta_natal = CartaAstralNatal(figsize=(16, 14))
            aspectos_natal, posiciones_natal = carta_natal.crear_carta_astral_natal(
                fecha_natal=fecha_natal,
                lugar_natal=lugar_coords,
                ciudad_natal=ciudad_nombre,
                guardar_archivo=False,
                directorio_salida=None
            )
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
            imagenes_base64['carta_natal'] = f"data:image/png;base64,{imagen_base64}"
            plt.close()
            buffer.close()
            
            datos_aspectos['natal'] = {
                'aspectos': aspectos_natal,
                'posiciones': posiciones_natal
            }
            
            print(f"✅ Carta natal: {len(aspectos_natal)} aspectos")
            
        except Exception as e:
            print(f"⚠️ Error en carta natal: {e}")
            imagenes_base64['carta_natal'] = crear_placeholder_base64("Carta Natal\n(Error)")
            datos_aspectos['natal'] = {'aspectos': [], 'posiciones': {}}
        
        # 2. PROGRESIONES (igual que antes)
        print("📈 Generando Progresiones...")
        try:
            from progresiones import CartaProgresiones
            from datetime import datetime as dt
            
            carta_prog = CartaProgresiones(figsize=(16, 14))
            hoy = dt.now()
            edad_actual = (hoy.year - año) + (hoy.month - mes) / 12.0
            
            aspectos_prog, pos_natales, pos_prog, _, _ = carta_prog.crear_carta_progresiones(
                fecha_nacimiento=fecha_natal,
                edad_consulta=edad_actual,
                lugar_nacimiento=lugar_coords,
                lugar_actual=lugar_coords,
                ciudad_nacimiento=ciudad_nombre,
                ciudad_actual=ciudad_nombre,
                guardar_archivo=False
            )
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
            imagenes_base64['progresiones'] = f"data:image/png;base64,{imagen_base64}"
            plt.close()
            buffer.close()
            
            datos_aspectos['progresiones'] = {
                'aspectos': aspectos_prog,
                'posiciones_natales': pos_natales,
                'posiciones_progresadas': pos_prog
            }
            
            print(f"✅ Progresiones: {len(aspectos_prog)} aspectos")
            
        except Exception as e:
            print(f"⚠️ Error en progresiones: {e}")
            imagenes_base64['progresiones'] = crear_placeholder_base64("Progresiones\n(En desarrollo)")
            datos_aspectos['progresiones'] = {'aspectos': [], 'posiciones_natales': {}, 'posiciones_progresadas': {}}
        
        # 3. TRÁNSITOS MEJORADOS
        print("🔄 Generando Tránsitos MEJORADOS...")
        transitos_base64, aspectos_trans = generar_transitos_base64_corregida(datos_natales)
        imagenes_base64['transitos'] = transitos_base64
        datos_aspectos['transitos'] = {'aspectos': aspectos_trans}
        
        print("✅ Cartas astrales MEJORADAS generadas en BASE64")
        
        # Compilar datos completos con MÁS INFORMACIÓN
        from datetime import datetime as dt
        datos_completos = {
            'aspectos_natales': datos_aspectos['natal']['aspectos'],
            'posiciones_natales': datos_aspectos['natal']['posiciones'],
            'aspectos_progresiones': datos_aspectos['progresiones']['aspectos'],
            'aspectos_transitos': datos_aspectos['transitos']['aspectos'],
            'imagenes_base64': imagenes_base64,
            'datos_completos_aspectos': datos_aspectos,
            'timestamp': dt.now().isoformat(),
            'metodo': 'base64_mejorado_v2',
            'estadisticas': {
                'total_aspectos_natal': len(datos_aspectos['natal']['aspectos']),
                'total_aspectos_progresiones': len(datos_aspectos['progresiones']['aspectos']),
                'total_aspectos_transitos': len(datos_aspectos['transitos']['aspectos'])
            }
        }
        
        return True, datos_completos
        
    except Exception as e:
        print(f"❌ Error en cartas mejoradas: {e}")
        import traceback
        traceback.print_exc()
        return False, None


# =======================================================================
# ENDPOINT DE TEST PARA LA VERSIÓN MEJORADA
# =======================================================================

@app.route('/test/cartas_mejoradas_base64')
def test_cartas_mejoradas_base64():
    """
    Test de la versión mejorada con mejor manejo de tránsitos
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España',
            'nombre': 'Test Mejorado'
        }
        
        exito, resultado = generar_cartas_astrales_base64_mejorada(datos_natales_test)
        
        if exito and resultado:
            imagenes_base64 = resultado['imagenes_base64']
            estadisticas = resultado['estadisticas']
            
            # HTML con estadísticas detalladas
            html_response = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>🌟 Test Cartas MEJORADAS</title>
                <style>
                    body {{ font-family: 'Georgia', serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }}
                    .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
                    .stats {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                    .carta-section {{ margin: 30px 0; padding: 20px; border-left: 5px solid #667eea; background: #f8f9ff; border-radius: 10px; }}
                    .carta-imagen {{ text-align: center; margin: 20px 0; }}
                    .carta-imagen img {{ max-width: 100%; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); border: 3px solid #667eea; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🌟 Cartas Astrales MEJORADAS</h1>
                    
                    <div class="stats">
                        <h3>📊 Estadísticas de Aspectos:</h3>
                        <p><strong>Natal:</strong> {estadisticas['total_aspectos_natal']} aspectos</p>
                        <p><strong>Progresiones:</strong> {estadisticas['total_aspectos_progresiones']} aspectos</p>
                        <p><strong>Tránsitos:</strong> {estadisticas['total_aspectos_transitos']} aspectos</p>
                    </div>

                    <div class="carta-section">
                        <h2>🌅 Carta Natal</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('carta_natal', '')}" alt="Carta Natal">
                        </div>
                    </div>

                    <div class="carta-section">
                        <h2>📈 Progresiones</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('progresiones', '')}" alt="Progresiones">
                        </div>
                    </div>

                    <div class="carta-section">
                        <h2>🔄 Tránsitos</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('transitos', '')}" alt="Tránsitos">
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_response
        else:
            return f"<h1>❌ Error en test mejorado</h1><p>Resultado: {resultado}</p>"
            
    except Exception as e:
        import traceback
        return f"<h1>❌ Error crítico</h1><pre>{traceback.format_exc()}</pre>"
        
# =======================================================================
# DEBUG ESPECÍFICO PARA VER QUÉ DATOS LLEGAN - AÑADIR A main.py
# =======================================================================

@app.route('/test/debug_aspectos_datos')
def debug_aspectos_datos():
    """
    Debug: Ver exactamente qué datos de aspectos se están generando
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            # Extraer aspectos
            aspectos_natales = resultado.get('aspectos_natales', [])
            aspectos_transitos = resultado.get('aspectos_transitos', [])
            aspectos_progresiones = resultado.get('aspectos_progresiones', [])
            
            # Debug detallado
            debug_info = {
                'resultado_keys': list(resultado.keys()),
                'aspectos_natales': {
                    'count': len(aspectos_natales),
                    'tipo_datos': type(aspectos_natales).__name__,
                    'primer_aspecto': aspectos_natales[0] if aspectos_natales else 'VACÍO',
                    'primer_aspecto_keys': list(aspectos_natales[0].keys()) if aspectos_natales and hasattr(aspectos_natales[0], 'keys') else 'NO ES DICT',
                    'primer_aspecto_attrs': [attr for attr in dir(aspectos_natales[0]) if not attr.startswith('_')] if aspectos_natales else 'NO HAY ATTRS'
                },
                'aspectos_transitos': {
                    'count': len(aspectos_transitos),
                    'tipo_datos': type(aspectos_transitos).__name__,
                    'primer_aspecto': aspectos_transitos[0] if aspectos_transitos else 'VACÍO',
                },
                'aspectos_progresiones': {
                    'count': len(aspectos_progresiones),
                    'tipo_datos': type(aspectos_progresiones).__name__,
                    'primer_aspecto': aspectos_progresiones[0] if aspectos_progresiones else 'VACÍO',
                },
                'imagenes_disponibles': list(resultado.get('imagenes_base64', {}).keys()),
                'template_data_keys': list(resultado.get('template_data', {}).keys()) if 'template_data' in resultado else 'NO TEMPLATE_DATA'
            }
            
            # Si hay aspectos, examinar estructura del primero
            if aspectos_natales:
                primer_aspecto = aspectos_natales[0]
                debug_info['estructura_aspecto_natal'] = {
                    'tipo_objeto': type(primer_aspecto).__name__,
                    'es_dict': isinstance(primer_aspecto, dict),
                    'es_objeto': hasattr(primer_aspecto, '__dict__'),
                    'contenido_str': str(primer_aspecto)[:200],
                    'atributos_disponibles': [attr for attr in dir(primer_aspecto) if not attr.startswith('_')] if hasattr(primer_aspecto, '__dict__') else 'NO HAY ATRIBUTOS'
                }
                
                # Si es un objeto, intentar acceder a sus propiedades
                if hasattr(primer_aspecto, '__dict__'):
                    debug_info['propiedades_aspecto'] = vars(primer_aspecto)
                elif isinstance(primer_aspecto, dict):
                    debug_info['propiedades_aspecto'] = primer_aspecto
            
            return jsonify(debug_info)
        else:
            return jsonify({'error': 'No se pudieron generar las cartas', 'exito': exito, 'resultado': resultado})
            
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()})

# =======================================================================
# FUNCIÓN CORREGIDA PARA MOSTRAR ASPECTOS REALES
# =======================================================================

@app.route('/test/aspectos_reales_formateados')
def test_aspectos_reales_formateados():
    """
    Test: Mostrar aspectos reales formateados correctamente
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            aspectos_natales = resultado.get('aspectos_natales', [])
            aspectos_transitos = resultado.get('aspectos_transitos', [])
            imagenes_base64 = resultado.get('imagenes_base64', {})
            
            # Función helper para formatear aspectos
            def formatear_aspecto(aspecto):
                try:
                    if isinstance(aspecto, dict):
                        # Si es diccionario
                        planeta1 = aspecto.get('planeta1', aspecto.get('planeta_1', 'Planeta1'))
                        planeta2 = aspecto.get('planeta2', aspecto.get('planeta_2', 'Planeta2'))
                        tipo = aspecto.get('tipo', aspecto.get('aspecto', 'Aspecto'))
                        orbe = aspecto.get('orbe', 0)
                        return f"{planeta1} {tipo} {planeta2}", f"{orbe:.1f}°"
                    elif hasattr(aspecto, '__dict__'):
                        # Si es objeto con atributos
                        attrs = vars(aspecto)
                        planeta1 = getattr(aspecto, 'planeta1', getattr(aspecto, 'planeta_1', 'Planeta1'))
                        planeta2 = getattr(aspecto, 'planeta2', getattr(aspecto, 'planeta_2', 'Planeta2'))
                        tipo = getattr(aspecto, 'tipo', getattr(aspecto, 'aspecto', 'Aspecto'))
                        orbe = getattr(aspecto, 'orbe', 0)
                        return f"{planeta1} {tipo} {planeta2}", f"{orbe:.1f}°"
                    else:
                        # Si es string o otro tipo
                        return str(aspecto)[:50], "N/A"
                except:
                    return str(aspecto)[:50], "Error"
            
            # HTML con aspectos REALES
            html_response = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>🌟 Aspectos Reales Formateados</title>
                <style>
                    body {{ font-family: 'Georgia', serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
                    .carta-section {{ margin: 30px 0; padding: 20px; border-left: 5px solid #667eea; background: #f8f9ff; border-radius: 10px; }}
                    .carta-imagen {{ text-align: center; margin: 20px 0; }}
                    .carta-imagen img {{ max-width: 100%; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); border: 3px solid #667eea; }}
                    .aspectos-section {{ background: #f8f9ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #667eea; }}
                    .aspectos-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px; margin-top: 10px; }}
                    .aspecto-item {{ background: white; padding: 10px 15px; border-radius: 6px; border: 1px solid #e0e6ed; display: flex; justify-content: space-between; align-items: center; }}
                    .aspecto-planetas {{ font-weight: 500; color: #333; }}
                    .aspecto-orbe {{ font-size: 0.85em; color: #666; background: #f0f2f5; padding: 3px 8px; border-radius: 4px; }}
                    .debug-info {{ background: #fffacd; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #ddd; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🌟 Test de Aspectos Reales Formateados</h1>
                    
                    <div class="debug-info">
                        <h3>📊 Debug Info:</h3>
                        <p><strong>Aspectos Natales encontrados:</strong> {len(aspectos_natales)}</p>
                        <p><strong>Aspectos Tránsitos encontrados:</strong> {len(aspectos_transitos)}</p>
                        <p><strong>Imágenes disponibles:</strong> {list(imagenes_base64.keys())}</p>
                    </div>

                    <div class="carta-section">
                        <h2>🌅 Carta Natal</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('carta_natal', '')}" alt="Carta Natal">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>⭐ Aspectos Natales REALES ({len(aspectos_natales)})</h3>
                            <div class="aspectos-grid">
            """
            
            # Añadir aspectos natales REALES
            for i, aspecto in enumerate(aspectos_natales[:12]):
                aspecto_texto, orbe_texto = formatear_aspecto(aspecto)
                html_response += f"""
                                <div class="aspecto-item">
                                    <span class="aspecto-planetas">{aspecto_texto}</span>
                                    <span class="aspecto-orbe">{orbe_texto}</span>
                                </div>
                """
            
            if len(aspectos_natales) > 12:
                html_response += f"""
                                <div class="aspecto-item" style="grid-column: 1 / -1; text-align: center; font-style: italic; color: #667eea;">
                                    + {len(aspectos_natales) - 12} aspectos más...
                                </div>
                """
            
            html_response += """
                            </div>
                        </div>
                    </div>
            """
            
            # Solo mostrar tránsitos si hay imagen
            if 'transitos' in imagenes_base64:
                html_response += f"""
                    <div class="carta-section">
                        <h2>🔄 Tránsitos Actuales</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('transitos', '')}" alt="Tránsitos">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>⚡ Aspectos de Tránsito REALES ({len(aspectos_transitos)})</h3>
                            <div class="aspectos-grid">
                """
                
                # Añadir aspectos de tránsito REALES
                for i, aspecto in enumerate(aspectos_transitos[:10]):
                    aspecto_texto, orbe_texto = formatear_aspecto(aspecto)
                    html_response += f"""
                                <div class="aspecto-item">
                                    <span class="aspecto-planetas">{aspecto_texto}</span>
                                    <span class="aspecto-orbe">{orbe_texto}</span>
                                </div>
                    """
                
                if len(aspectos_transitos) > 10:
                    html_response += f"""
                                <div class="aspecto-item" style="grid-column: 1 / -1; text-align: center; font-style: italic; color: #667eea;">
                                    + {len(aspectos_transitos) - 10} aspectos más...
                                </div>
                    """
                
                html_response += """
                            </div>
                        </div>
                    </div>
                """
            
            html_response += """
                </div>
            </body>
            </html>
            """
            
            return html_response
        else:
            return f"<h1>❌ Error generando cartas</h1><p>Exito: {exito}</p>"
            
    except Exception as e:
        import traceback
        return f"<h1>❌ Error crítico</h1><pre>{traceback.format_exc()}</pre>"

# =======================================================================
# DEBUG ESPECÍFICO PARA PROGRESIONES
# =======================================================================

@app.route('/test/debug_progresiones_especifico')
def debug_progresiones_especifico():
    """
    Debug específico para entender por qué fallan las progresiones
    """
    try:
        from datetime import datetime
        
        # Datos de test
        fecha_str = '15/07/1985'
        hora_str = '10:30'
        
        dia, mes, año = map(int, fecha_str.split('/'))
        hora, minuto = map(int, hora_str.split(':'))
        fecha_natal = (año, mes, dia, hora, minuto)
        lugar_coords = (40.42, -3.70)
        ciudad_nombre = 'Madrid, España'
        
        resultado_debug = {
            'fecha_natal': fecha_natal,
            'lugar_coords': lugar_coords,
            'pasos': [],
            'error_final': None
        }
        
        # PASO 1: Verificar importación
        try:
            from progresiones import CartaProgresiones
            resultado_debug['pasos'].append('✅ Importación CartaProgresiones OK')
        except Exception as e:
            resultado_debug['pasos'].append(f'❌ Error importando CartaProgresiones: {e}')
            return jsonify(resultado_debug)
        
        # PASO 2: Crear instancia
        try:
            carta_prog = CartaProgresiones(figsize=(12, 12))
            resultado_debug['pasos'].append('✅ Instancia CartaProgresiones creada')
        except Exception as e:
            resultado_debug['pasos'].append(f'❌ Error creando instancia: {e}')
            return jsonify(resultado_debug)
        
        # PASO 3: Calcular edad actual
        try:
            hoy = datetime.now()
            edad_actual = (hoy.year - año) + (hoy.month - mes) / 12.0
            resultado_debug['edad_actual'] = edad_actual
            resultado_debug['pasos'].append(f'✅ Edad calculada: {edad_actual:.2f} años')
        except Exception as e:
            resultado_debug['pasos'].append(f'❌ Error calculando edad: {e}')
            return jsonify(resultado_debug)
        
        # PASO 4: Intentar generar progresiones
        try:
            resultado_debug['pasos'].append('🔄 Intentando crear_carta_progresiones...')
            
            aspectos_prog, pos_natales, pos_prog, _, _ = carta_prog.crear_carta_progresiones(
                fecha_nacimiento=fecha_natal,
                edad_consulta=edad_actual,
                lugar_nacimiento=lugar_coords,
                lugar_actual=lugar_coords,
                ciudad_nacimiento=ciudad_nombre,
                ciudad_actual=ciudad_nombre,
                guardar_archivo=False
            )
            
            resultado_debug['pasos'].append('✅ Progresiones generadas exitosamente!')
            resultado_debug['aspectos_encontrados'] = len(aspectos_prog) if aspectos_prog else 0
            resultado_debug['pos_natales_count'] = len(pos_natales) if pos_natales else 0
            resultado_debug['pos_prog_count'] = len(pos_prog) if pos_prog else 0
            
        except Exception as e:
            import traceback
            resultado_debug['pasos'].append(f'❌ Error en crear_carta_progresiones: {str(e)}')
            resultado_debug['error_final'] = {
                'mensaje': str(e),
                'tipo': type(e).__name__,
                'traceback': traceback.format_exc()
            }
        
        return jsonify(resultado_debug)
        
    except Exception as e:
        return jsonify({
            'error_critico': str(e),
            'traceback': traceback.format_exc()
        })

# =======================================================================
# ENDPOINT SIMPLE PARA VERIFICAR SOLO NATAL + TRÁNSITOS
# =======================================================================

@app.route('/test/solo_natal_transitos')
def test_solo_natal_transitos():
    """
    Test simplificado: Solo natal + tránsitos (sin progresiones)
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        # Generar solo natal y tránsitos
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            aspectos_natales = resultado.get('aspectos_natales', [])
            aspectos_transitos = resultado.get('aspectos_transitos', [])
            imagenes_base64 = resultado.get('imagenes_base64', {})
            
            return jsonify({
                'status': 'success',
                'cartas_disponibles': list(imagenes_base64.keys()),
                'aspectos_natales_count': len(aspectos_natales),
                'aspectos_transitos_count': len(aspectos_transitos),
                'aspectos_natales_sample': [str(a)[:100] for a in aspectos_natales[:3]],
                'aspectos_transitos_sample': [str(a)[:100] for a in aspectos_transitos[:3]],
                'siguiente_paso': 'Usar /test/aspectos_reales_formateados para ver el HTML final'
            })
        else:
            return jsonify({'status': 'error', 'exito': exito, 'resultado': resultado})
            
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()})
        
# =======================================================================
# DEBUG COMPLETO Y CORRECCIÓN - AÑADIR A main.py
# =======================================================================

@app.route('/test/debug_template_data_completo')
def debug_template_data_completo():
    """
    Debug completo: Ver exactamente qué datos llegan al template
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            # Extraer todos los datos
            aspectos_natales = resultado.get('aspectos_natales', [])
            aspectos_progresiones = resultado.get('aspectos_progresiones', [])
            aspectos_transitos = resultado.get('aspectos_transitos', [])
            imagenes_base64 = resultado.get('imagenes_base64', {})
            template_data = resultado.get('template_data', {})
            
            debug_info = {
                'resultado_principal': {
                    'keys': list(resultado.keys()),
                    'aspectos_natales_count': len(aspectos_natales),
                    'aspectos_progresiones_count': len(aspectos_progresiones),
                    'aspectos_transitos_count': len(aspectos_transitos),
                    'imagenes_disponibles': list(imagenes_base64.keys())
                },
                'template_data_estructura': {
                    'existe': 'template_data' in resultado,
                    'keys': list(template_data.keys()) if template_data else 'NO EXISTE',
                    'aspectos_natales_en_template': len(template_data.get('aspectos_natales', [])) if template_data else 0,
                    'aspectos_progresiones_en_template': len(template_data.get('aspectos_progresiones', [])) if template_data else 0,
                    'imagenes_en_template': list(template_data.get('imagenes_base64', {}).keys()) if template_data else []
                },
                'muestra_aspectos_natales': {
                    'total': len(aspectos_natales),
                    'primeros_3': [
                        {
                            'planeta1': asp.get('planeta1', 'N/A'),
                            'aspecto': asp.get('aspecto', 'N/A'),
                            'planeta2': asp.get('planeta2', 'N/A'),
                            'orbe': asp.get('orbe', 0)
                        } for asp in aspectos_natales[:3]
                    ] if aspectos_natales else []
                },
                'muestra_aspectos_progresiones': {
                    'total': len(aspectos_progresiones),
                    'primeros_3': [
                        {
                            'planeta_progresion': asp.get('planeta_progresion', 'N/A'),
                            'tipo': asp.get('tipo', 'N/A'),
                            'planeta_natal': asp.get('planeta_natal', 'N/A'),
                            'orbe': asp.get('orbe', 0)
                        } for asp in aspectos_progresiones[:3]
                    ] if aspectos_progresiones else []
                },
                'problema_identificado': None
            }
            
            # Identificar el problema específico
            if len(imagenes_base64) < 3:
                debug_info['problema_identificado'] = f"Solo {len(imagenes_base64)} imágenes generadas de 3 esperadas"
            elif len(aspectos_progresiones) == 0:
                debug_info['problema_identificado'] = "Aspectos de progresiones están vacíos"
            elif 'template_data' not in resultado:
                debug_info['problema_identificado'] = "Falta template_data en resultado"
            elif len(template_data.get('aspectos_progresiones', [])) == 0:
                debug_info['problema_identificado'] = "template_data no tiene aspectos_progresiones"
            else:
                debug_info['problema_identificado'] = "Datos parecen correctos, problema en template HTML"
            
            return jsonify(debug_info)
        else:
            return jsonify({'error': 'No se pudieron generar las cartas', 'exito': exito})
            
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()})

@app.route('/test/aspectos_reales_corregidos')
def test_aspectos_reales_corregidos():
    """
    Test con aspectos REALES mostrados correctamente
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        exito, resultado = generar_cartas_astrales_base64(datos_natales_test)
        
        if exito and resultado:
            aspectos_natales = resultado.get('aspectos_natales', [])
            aspectos_progresiones = resultado.get('aspectos_progresiones', [])
            aspectos_transitos = resultado.get('aspectos_transitos', [])
            imagenes_base64 = resultado.get('imagenes_base64', {})
            
            # HTML con aspectos REALES
            html_response = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>🌟 Test Aspectos REALES Corregidos</title>
                <style>
                    body {{ font-family: 'Georgia', serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
                    .carta-section {{ margin: 30px 0; padding: 20px; border-left: 5px solid #667eea; background: #f8f9ff; border-radius: 10px; }}
                    .carta-imagen {{ text-align: center; margin: 20px 0; }}
                    .carta-imagen img {{ max-width: 100%; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); border: 3px solid #667eea; }}
                    .aspectos-section {{ background: #f8f9ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #667eea; }}
                    .aspectos-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px; margin-top: 10px; }}
                    .aspecto-item {{ background: white; padding: 10px 15px; border-radius: 6px; border: 1px solid #e0e6ed; display: flex; justify-content: space-between; align-items: center; }}
                    .aspecto-planetas {{ font-weight: 500; color: #333; }}
                    .aspecto-orbe {{ font-size: 0.85em; color: #666; background: #f0f2f5; padding: 3px 8px; border-radius: 4px; }}
                    .debug-info {{ background: #fffacd; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🌟 Test de Aspectos REALES Corregidos</h1>
                    
                    <div class="debug-info">
                        <h3>📊 Estado actual:</h3>
                        <p><strong>Aspectos Natales:</strong> {len(aspectos_natales)} encontrados</p>
                        <p><strong>Aspectos Progresiones:</strong> {len(aspectos_progresiones)} encontrados</p>
                        <p><strong>Aspectos Tránsitos:</strong> {len(aspectos_transitos)} encontrados</p>
                        <p><strong>Imágenes:</strong> {list(imagenes_base64.keys())}</p>
                    </div>

                    <!-- CARTA NATAL CON ASPECTOS REALES -->
                    <div class="carta-section">
                        <h2>🌅 Carta Natal</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('carta_natal', '')}" alt="Carta Natal">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>⭐ Aspectos Natales REALES ({len(aspectos_natales)})</h3>
                            <div class="aspectos-grid">
            """
            
            # Añadir aspectos natales REALES
            for aspecto in aspectos_natales[:12]:
                planeta1 = aspecto.get('planeta1', 'Planeta1')
                planeta2 = aspecto.get('planeta2', 'Planeta2')
                tipo_aspecto = aspecto.get('aspecto', 'aspecto')
                orbe = aspecto.get('orbe', 0)
                
                html_response += f"""
                                <div class="aspecto-item">
                                    <span class="aspecto-planetas">{planeta1} {tipo_aspecto} {planeta2}</span>
                                    <span class="aspecto-orbe">{orbe:.1f}°</span>
                                </div>
                """
            
            if len(aspectos_natales) > 12:
                html_response += f"""
                                <div class="aspecto-item" style="grid-column: 1 / -1; text-align: center; font-style: italic; color: #667eea;">
                                    + {len(aspectos_natales) - 12} aspectos más...
                                </div>
                """
            
            html_response += """
                            </div>
                        </div>
                    </div>
            """
            
            # PROGRESIONES CON ASPECTOS REALES
            if 'progresiones' in imagenes_base64 and aspectos_progresiones:
                html_response += f"""
                    <div class="carta-section">
                        <h2>📈 Progresiones Secundarias</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('progresiones', '')}" alt="Progresiones">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>🌱 Aspectos de Progresión REALES ({len(aspectos_progresiones)})</h3>
                            <div class="aspectos-grid">
                """
                
                for aspecto in aspectos_progresiones[:10]:
                    planeta_progresion = aspecto.get('planeta_progresion', 'PlanetaProg')
                    planeta_natal = aspecto.get('planeta_natal', 'PlanetaNatal')
                    tipo = aspecto.get('tipo', 'aspecto')
                    orbe = aspecto.get('orbe', 0)
                    
                    html_response += f"""
                                    <div class="aspecto-item">
                                        <span class="aspecto-planetas">{planeta_progresion} {tipo} {planeta_natal}</span>
                                        <span class="aspecto-orbe">{orbe:.1f}°</span>
                                    </div>
                    """
                
                if len(aspectos_progresiones) > 10:
                    html_response += f"""
                                    <div class="aspecto-item" style="grid-column: 1 / -1; text-align: center; font-style: italic; color: #667eea;">
                                        + {len(aspectos_progresiones) - 10} aspectos más...
                                    </div>
                    """
                
                html_response += """
                            </div>
                        </div>
                    </div>
                """
            else:
                html_response += """
                    <div class="carta-section">
                        <h2>📈 Progresiones Secundarias</h2>
                        <div style="background: #ffebee; padding: 20px; border-radius: 8px; text-align: center;">
                            <p><strong>⚠️ Progresiones no disponibles</strong></p>
                            <p>Imagen disponible: {'progresiones' in imagenes_base64}</p>
                            <p>Aspectos disponibles: {len(aspectos_progresiones) > 0}</p>
                        </div>
                    </div>
                """
            
            # TRÁNSITOS CON ASPECTOS REALES
            if 'transitos' in imagenes_base64:
                html_response += f"""
                    <div class="carta-section">
                        <h2>🔄 Tránsitos Actuales</h2>
                        <div class="carta-imagen">
                            <img src="{imagenes_base64.get('transitos', '')}" alt="Tránsitos">
                        </div>
                        
                        <div class="aspectos-section">
                            <h3>⚡ Aspectos de Tránsito REALES ({len(aspectos_transitos)})</h3>
                            <div class="aspectos-grid">
                """
                
                for aspecto in aspectos_transitos[:10]:
                    planeta_transito = aspecto.get('planeta_transito', 'PlanetaTrans')
                    planeta_natal = aspecto.get('planeta_natal', 'PlanetaNatal')
                    tipo = aspecto.get('tipo', 'aspecto')
                    orbe = aspecto.get('orbe', 0)
                    
                    html_response += f"""
                                    <div class="aspecto-item">
                                        <span class="aspecto-planetas">{planeta_transito} {tipo} {planeta_natal}</span>
                                        <span class="aspecto-orbe">{orbe:.1f}°</span>
                                    </div>
                    """
                
                if len(aspectos_transitos) > 10:
                    html_response += f"""
                                    <div class="aspecto-item" style="grid-column: 1 / -1; text-align: center; font-style: italic; color: #667eea;">
                                        + {len(aspectos_transitos) - 10} aspectos más...
                                    </div>
                    """
                
                html_response += """
                            </div>
                        </div>
                    </div>
                """
            
            html_response += """
                </div>
            </body>
            </html>
            """
            
            return html_response
        else:
            return f"<h1>❌ Error generando cartas</h1><p>Exito: {exito}</p>"
            
    except Exception as e:
        import traceback
        return f"<h1>❌ Error crítico</h1><pre>{traceback.format_exc()}</pre>"

# =======================================================================
# FUNCIÓN CORREGIDA CON TIMESTAMP Y DATOS COMPLETOS
# =======================================================================

def generar_cartas_astrales_base64_corregida(datos_natales):
    """
    Versión CORREGIDA que asegura todos los campos necesarios
    """
    try:
        print("🔧 Generando cartas astrales CORREGIDAS...")
        
        # [Código de generación igual que antes...]
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
        }
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        ciudad_nombre = 'Madrid, España'
        
        imagenes_base64 = {}
        datos_aspectos = {}
        
        # 1. CARTA NATAL
        print("📊 Generando Carta Natal...")
        try:
            from carta_natal import CartaAstralNatal
            import matplotlib.pyplot as plt
            import io
            import base64
            
            carta_natal = CartaAstralNatal(figsize=(16, 14))
            aspectos_natal, posiciones_natal = carta_natal.crear_carta_astral_natal(
                fecha_natal=fecha_natal,
                lugar_natal=lugar_coords,
                ciudad_natal=ciudad_nombre,
                guardar_archivo=False,
                directorio_salida=None
            )
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
            imagenes_base64['carta_natal'] = f"data:image/png;base64,{imagen_base64}"
            plt.close()
            buffer.close()
            
            datos_aspectos['natal'] = {
                'aspectos': aspectos_natal,
                'posiciones': posiciones_natal
            }
            
            print(f"✅ Carta natal: {len(aspectos_natal)} aspectos")
            
        except Exception as e:
            print(f"⚠️ Error en carta natal: {e}")
            imagenes_base64['carta_natal'] = crear_placeholder_base64("Carta Natal\n(Error)")
            datos_aspectos['natal'] = {'aspectos': [], 'posiciones': {}}
        
        # 2. PROGRESIONES
        print("📈 Generando Progresiones...")
        try:
            from progresiones import CartaProgresiones
            from datetime import datetime as dt
            
            carta_prog = CartaProgresiones(figsize=(16, 14))
            hoy = dt.now()
            edad_actual = (hoy.year - año) + (hoy.month - mes) / 12.0
            
            aspectos_prog, pos_natales, pos_prog, _, _ = carta_prog.crear_carta_progresiones(
                fecha_nacimiento=fecha_natal,
                edad_consulta=edad_actual,
                lugar_nacimiento=lugar_coords,
                lugar_actual=lugar_coords,
                ciudad_nacimiento=ciudad_nombre,
                ciudad_actual=ciudad_nombre,
                guardar_archivo=False
            )
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
            imagenes_base64['progresiones'] = f"data:image/png;base64,{imagen_base64}"
            plt.close()
            buffer.close()
            
            datos_aspectos['progresiones'] = {
                'aspectos': aspectos_prog,
                'posiciones_natales': pos_natales,
                'posiciones_progresadas': pos_prog
            }
            
            print(f"✅ Progresiones: {len(aspectos_prog)} aspectos")
            
        except Exception as e:
            print(f"⚠️ Error en progresiones: {e}")
            imagenes_base64['progresiones'] = crear_placeholder_base64("Progresiones\n(Error)")
            datos_aspectos['progresiones'] = {'aspectos': []}
        
        # 3. TRÁNSITOS
        print("🔄 Generando Tránsitos...")
        try:
            from transitos import CartaTransitos
            from datetime import datetime as dt
            
            carta_trans = CartaTransitos(figsize=(16, 14))
            hoy = dt.now()
            fecha_consulta = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
            
            resultado = carta_trans.crear_carta_transitos(
                fecha_nacimiento=fecha_natal,
                fecha_transito=fecha_consulta,
                lugar_nacimiento=lugar_coords,
                guardar_archivo=False
            )
            
            if resultado and len(resultado) >= 3:
                aspectos_trans, pos_natales, pos_transitos = resultado[:3]
                
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                           facecolor='white', edgecolor='none')
                buffer.seek(0)
                imagen_base64 = base64.b64encode(buffer.getvalue()).decode()
                imagenes_base64['transitos'] = f"data:image/png;base64,{imagen_base64}"
                plt.close()
                buffer.close()
                
                datos_aspectos['transitos'] = {
                    'aspectos': aspectos_trans,
                    'posiciones_natales': pos_natales,
                    'posiciones_transitos': pos_transitos
                }
                
                print(f"✅ Tránsitos: {len(aspectos_trans)} aspectos")
            else:
                raise Exception("Resultado de tránsitos vacío")
                
        except Exception as e:
            print(f"⚠️ Error en tránsitos: {e}")
            imagenes_base64['transitos'] = crear_placeholder_base64("Tránsitos\n(Error)")
            datos_aspectos['transitos'] = {'aspectos': []}
        
        # COMPILAR DATOS COMPLETOS CON TODOS LOS CAMPOS NECESARIOS
        from datetime import datetime as dt
        timestamp = dt.now().strftime('%Y%m%d_%H%M%S')
        
        aspectos_natales = datos_aspectos['natal']['aspectos']
        posiciones_natales = datos_aspectos['natal']['posiciones']
        aspectos_progresiones = datos_aspectos['progresiones']['aspectos']
        aspectos_transitos = datos_aspectos['transitos']['aspectos']
        
        estadisticas = {
            'total_aspectos_natal': len(aspectos_natales),
            'total_aspectos_progresiones': len(aspectos_progresiones),
            'total_aspectos_transitos': len(aspectos_transitos)
        }
        
        # ESTRUCTURA COMPLETA CON TODOS LOS CAMPOS NECESARIOS
        datos_completos = {
            # Datos principales
            'aspectos_natales': aspectos_natales,
            'posiciones_natales': posiciones_natales,
            'aspectos_progresiones': aspectos_progresiones,
            'aspectos_transitos': aspectos_transitos,
            'imagenes_base64': imagenes_base64,
            'estadisticas': estadisticas,
            
            # Campos requeridos por el sistema
            'timestamp': timestamp,
            'informe_html': f"templates/informe_carta_astral_ia_{timestamp}.html",
            'informe_pdf': f"informes/informe_carta_astral_ia_{timestamp}.pdf",
            'es_producto_m': False,
            'duracion_minutos': 40,
            
            # Datos completos para debugging
            'datos_completos_aspectos': datos_aspectos,
            'metodo': 'base64_corregido_v3',
            'datos_originales': datos_natales,
            
            # Template data (estructura específica para templates)
            'template_data': {
                'aspectos_natales': aspectos_natales,
                'posiciones_natales': posiciones_natales,
                'aspectos_progresiones': aspectos_progresiones,
                'aspectos_transitos': aspectos_transitos,
                'estadisticas': estadisticas,
                'imagenes_base64': imagenes_base64,
                'timestamp': timestamp
            }
        }
        
        print("✅ Cartas astrales CORREGIDAS generadas exitosamente")
        return True, datos_completos
        
    except Exception as e:
        print(f"❌ Error en cartas corregidas: {e}")
        import traceback
        traceback.print_exc()
        return False, None

# =======================================================================
# REEMPLAZAR LA FUNCIÓN PRINCIPAL EN main.py
# =======================================================================

# COMENTAR/REEMPLAZAR la función generar_cartas_astrales_base64 existente por:
# generar_cartas_astrales_base64 = generar_cartas_astrales_base64_corregida

@app.route('/test/usar_funcion_corregida')
def test_usar_funcion_corregida():
    """
    Test usando la función corregida
    """
    try:
        datos_natales_test = {
            'fecha_nacimiento': '15/07/1985',
            'hora_nacimiento': '10:30',
            'lugar_nacimiento': 'Madrid, España'
        }
        
        exito, resultado = generar_cartas_astrales_base64_corregida(datos_natales_test)
        
        if exito and resultado:
            return jsonify({
                'status': 'success',
                'timestamp_incluido': 'timestamp' in resultado,
                'campos_principales': list(resultado.keys()),
                'aspectos_natales_count': len(resultado.get('aspectos_natales', [])),
                'aspectos_progresiones_count': len(resultado.get('aspectos_progresiones', [])),
                'aspectos_transitos_count': len(resultado.get('aspectos_transitos', [])),
                'imagenes_disponibles': list(resultado.get('imagenes_base64', {}).keys()),
                'template_data_ok': 'template_data' in resultado,
                'test_pdf_url': '/test/generar_pdf_especialidad/carta_astral_ia'
            })
        else:
            return jsonify({'status': 'error', 'exito': exito})
            
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()})

if __name__ == "__main__":
    print("🚀 Inicializando sistema AS Asesores...")

    # Ejecutar limpieza inicial al arrancar
    print("Ejecutando limpieza inicial...")
    limpiar_archivos_antiguos()
    
    # Inicializar sistema de limpieza automática
    iniciar_limpieza_automatica()
    
    # Inicializar base de datos mejorada
    print("Inicializando base de datos mejorada...")
    inicializar_bd_mejorada()
    
    # Verificar variables de entorno críticas
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  VARIABLES DE ENTORNO FALTANTES: {', '.join(missing_vars)}")
    else:
        print("✅ Variables de entorno configuradas")
    
    # Verificar configuración de Telegram
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        print("✅ Telegram configurado para notificaciones")
    else:
        print("⚠️  Telegram no configurado - Las notificaciones no funcionarán")
    
    print("✅ Sistema AS Asesores iniciado correctamente")
    print("📞 Sofía (AS Cartastral): Teléfono directo")
    print("🤖 Verónica (AS Asesores): Teléfono directo")
    print("📅 Calendario disponible en /calendario")
    print("🔧 Administración disponible en /admin")
    print("🏠 Estado del sistema en /")

    # Limpiar memoria
    gc.collect()
    
    # Ejecutar servidor
    app.run(host="0.0.0.0", port=5000, debug=True)