from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import render_template_string
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
from pathlib import Path
from app import app
CORS(app, origins=["https://asasesores.com"])

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
    Elimina archivos de informes y cartas que tengan más de 7 días
    """
    try:
        hace_7_dias = datetime.now() - timedelta(days=7)
        archivos_eliminados = 0
        
        # Limpiar templates
        for archivo in glob.glob("templates/informe_*_*.html"):
            try:
                # Usar fecha de modificación del archivo en lugar de parsear nombre
                fecha_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
                
                if fecha_archivo < hace_7_dias:
                    os.remove(archivo)
                    archivos_eliminados += 1
                    print(f"Eliminado archivo antiguo: {archivo}")
            except (OSError, ValueError) as e:
                print(f"Error procesando archivo {archivo}: {e}")
                continue
        
        # Limpiar static (imágenes de cartas)
        for archivo in glob.glob("static/*.png"):
            try:
                # Usar fecha de modificación del archivo
                fecha_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
                
                if fecha_archivo < hace_7_dias:
                    os.remove(archivo)
                    archivos_eliminados += 1
                    print(f"Eliminada imagen antigua: {archivo}")
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
        "to_number": telefono,              # ← Cambiar "phone_number" por "to_number"
        "from_number": ZADARMA_PHONE_NUMBER_ID,  # ← Añadir esta línea
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
            'https://api.retellai.com/call',
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
        data = request.get_json()
        print(f"🔍 DEBUG Agendar cita: {data}")
        
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
    
@app.route('/api/test_booking', methods=['POST'])
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
        
        # Detectar si es ticket técnico
        agente = data.get('agente', '').lower()
        es_tecnico = 'alex' in agente or 'técnico' in agente or 'soporte' in agente
        
        # Guardar en base de datos
        lead_guardado = guardar_lead_cliente(data)
        
        # Personalizar notificación según tipo
        if es_tecnico:
            emoji_tipo = "🔧"
            tipo_registro = "TICKET TÉCNICO"
        else:
            emoji_tipo = "🎯" 
            tipo_registro = "LEAD COMERCIAL"
        
        enviar_telegram_mejora(f"""
{emoji_tipo} <b>NUEVO {tipo_registro}</b>

👤 <b>Cliente:</b> {data.get('nombre_cliente', 'Sin nombre')}
🏢 <b>Empresa:</b> {data.get('empresa', 'Sin empresa')}
📞 <b>Teléfono:</b> {data.get('telefono', 'Sin teléfono')}
📧 <b>Email:</b> {data.get('email', 'Sin email')}
📝 <b>Notas:</b> {data.get('notas', 'Sin notas')}
👨‍💼 <b>Agente:</b> {data.get('agente', 'Sin especificar')}

✅ <b>Estado:</b> Registrado - {"Seguimiento técnico" if es_tecnico else "Seguimiento comercial"}
        """)
        
        return jsonify({
            "success": True,
            "message": "Datos guardados correctamente",
            "lead_id": lead_guardado,
            "tipo": "ticket_tecnico" if es_tecnico else "lead_comercial"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
        
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
    
@app.route('/api/llamada_vendedor', methods=['POST'])
def llamada_vendedor():
    try:
        data = request.json
        print(f"=== DEBUG: Datos recibidos: {data} ===")
        
        telefono = data.get('telefono')
        empresa = data.get('empresa')
        vendedor = data.get('vendedor')
        
        # Mapear nombres de Make a nombres reales
        mapeo_vendedores = {
            'vendedor 1': 'Albert',
            'vendedor 2': 'Juan', 
            'vendedor 3': 'Carlos'
        }
        vendedor_real = mapeo_vendedores.get(vendedor, vendedor)
        
        print(f"=== DEBUG: telefono={telefono}, empresa={empresa}, vendedor={vendedor} -> {vendedor_real} ===")
        
        # Usar Zadarma-Retell para vendedores
        if vendedor_real in ['Albert', 'Juan', 'Carlos']:
            resultado = retell_llamada_zadarma(telefono, empresa, vendedor_real)
            print(f"=== DEBUG: Resultado llamada: {resultado} ===")
            return jsonify(resultado)
        else:
            return jsonify({"error": f"Vendedor no válido: {vendedor} -> {vendedor_real}"})
            
    except Exception as e:
        print(f"=== ERROR: {str(e)} ===")
        return jsonify({"error": str(e)}), 500
        
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