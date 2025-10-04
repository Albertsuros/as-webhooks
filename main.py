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
from pathlib import Path
from app import app
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ID del calendario AS Asesores
CALENDAR_ID = 'b64595022e163fbb552d1d5202a590605d3dd66079c082dc4037513c2a5369e1@group.calendar.google.com'

# ========================================
# NUEVAS IMPORTACIONES PARA MEJORAS
# ========================================
import sqlite3
import requests
import gc
import pytz
from weasyprint import HTML
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
# Importar lógica inteligente
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
        # ARCHIVOS PROTEGIDOS (no eliminar)
        # Limpiar static (imágenes de cartas) - PROTEGER IMÁGENES FIJAS
        archivos_protegidos = {
            'logo.JPG', 'astrologia-3.JPG', 'Tarot y astrologia-5.JPG',
            'Sinastria.JPG', 'astrologia-1.JPG', 'coaching-4.JPG',
            'Lectura-de-manos-p.jpg', 'lectura facial.JPG', 'grafologia_2.jpeg'
        }

        for archivo in glob.glob("static/*"):
            nombre_archivo = os.path.basename(archivo)
            if nombre_archivo in archivos_protegidos:
                continue  # No eliminar imágenes de especialidades
            try:
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

@app.route("/webhook/vendedor1", methods=["POST"])
def webhook_vendedor1():
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
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/vendedor2", methods=["POST"])
def webhook_vendedor2():
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
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

@app.route("/webhook/vendedor3", methods=["POST"])
def webhook_vendedor3():
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
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

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

        # Preparar datos con identificadores únicos para grafología
        data = preparar_datos_con_id(data, "grafologia")
        
        response = handle_grafologia_webhook(data)
        return jsonify(response)

    except Exception as e:
        print(f"Error en webhook_grafologia: {e}")
        return jsonify({
            "type": "speak",
            "text": "Error interno del servidor"
        }), 500

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
            "/webhook/grafologia": "POST - Webhook de Grafología",
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
CALENDAR_ID = 'b64595022e163fbb552d1d5202a590605d3dd66079c082dc4037513c2a5369e1@group.calendar.google.com'

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
        
# Test de conexión
def test_google_calendar():
    """Test rápido de Google Calendar"""
    service = inicializar_google_calendar()
    if service:
        print("✅ Google Calendar conectado correctamente")
        return True
    return False
    
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
        
# ========================================
# REPROGRAMACIÓN DE CITAS
# ========================================

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
        
        if not all([nombre_cliente, fecha_original, nueva_fecha, nuevo_horario]):
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos'
            }), 400
        
        # 1. Buscar evento original en Google Calendar
        service = inicializar_google_calendar()
        if not service:
            return jsonify({
                'success': False,
                'message': 'Error conectando con Google Calendar'
            }), 500
        
        # 2. Buscar evento por fecha y nombre
        from datetime import datetime
        import pytz
        tz = pytz.timezone('Europe/Madrid')
        
        fecha_obj = datetime.strptime(fecha_original, '%Y-%m-%d')
        inicio_dia = tz.localize(fecha_obj.replace(hour=0, minute=0))
        fin_dia = tz.localize(fecha_obj.replace(hour=23, minute=59))
        
        CALENDAR_ID = 'b64595022e163fbb552d1d5202a590605d3dd66079c082dc4037513c2a5369e1@group.calendar.google.com'
        
        eventos = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=inicio_dia.isoformat(),
            timeMax=fin_dia.isoformat(),
            q=nombre_cliente,
            singleEvents=True
        ).execute()
        
        eventos_lista = eventos.get('items', [])
        
        if not eventos_lista:
            return jsonify({
                'success': False,
                'message': 'No se encontró la cita original'
            }), 404
        
        # 3. Modificar el primer evento encontrado
        evento = eventos_lista[0]
        evento_id = evento['id']
        
        # 4. Verificar disponibilidad del nuevo horario
        disponible = verificar_disponibilidad(nueva_fecha, nuevo_horario)
        
        if not disponible:
            return jsonify({
                'success': False,
                'message': 'El nuevo horario no está disponible'
            }), 400
        
        # 5. Actualizar evento
        from datetime import timedelta
        hora_inicio = nuevo_horario.split('-')[0]
        nueva_fecha_hora = datetime.strptime(f"{nueva_fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
        
        # Duración según tipo
        duraciones = {
            'sofia_astrologo': 60,
            'sofia_tarot': 60,
            'veronica_telefono': 30,
            'veronica_visita': 90
        }
        duracion = duraciones.get(tipo_servicio, 60)
        nueva_fecha_hora_fin = nueva_fecha_hora + timedelta(minutes=duracion)
        
        evento['start'] = {
            'dateTime': tz.localize(nueva_fecha_hora).isoformat(),
            'timeZone': 'Europe/Madrid'
        }
        evento['end'] = {
            'dateTime': tz.localize(nueva_fecha_hora_fin).isoformat(),
            'timeZone': 'Europe/Madrid'
        }
        
        evento_actualizado = service.events().update(
            calendarId=CALENDAR_ID,
            eventId=evento_id,
            body=evento
        ).execute()
        
        # 6. Notificar por Telegram
        try:
            import requests
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if bot_token and chat_id:
                mensaje = (
                    f"🔄 <b>CITA REPROGRAMADA</b>\n\n"
                    f"👤 <b>Cliente:</b> {nombre_cliente}\n"
                    f"📅 <b>De:</b> {fecha_original} {horario_original}\n"
                    f"📅 <b>A:</b> {nueva_fecha} {nuevo_horario}\n"
                )
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        'chat_id': chat_id,
                        'text': mensaje,
                        'parse_mode': 'HTML'
                    }
                )
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Cita reprogramada correctamente',
            'evento_id': evento_actualizado.get('id'),
            'nueva_fecha': nueva_fecha,
            'nuevo_horario': nuevo_horario
        })
        
    except Exception as e:
        print(f"❌ Error reprogramando cita: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
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
        
@app.route('/test/llamada-saliente', methods=['GET', 'POST'])
def test_llamada_saliente():
    """Test de llamada saliente desde VAPI a través de GoTrunk"""
    try:
        import requests
        import os
        
        # Configuración VAPI
        VAPI_API_KEY = os.getenv("VAPI_API_KEY")  # Necesitas añadir esta variable
        VAPI_PHONE_ID = os.getenv("VAPI_PHONE_ID")  # ID del número +34930450985
        VAPI_ASSISTANT_ID = os.getenv("VAPI_SOFIA_ID")  # ID del asistente Sofia
        
        if not all([VAPI_API_KEY, VAPI_PHONE_ID, VAPI_ASSISTANT_ID]):
            return jsonify({
                "status": "error",
                "message": "Faltan variables de entorno VAPI",
                "required": ["VAPI_API_KEY", "VAPI_PHONE_ID", "VAPI_SOFIA_ID"]
            })
        
        # Datos de la llamada de prueba
        if request.method == 'GET':
            # Mostrar formulario de test
            return render_template_string(FORM_TEST_LLAMADA)
        
        # POST: Ejecutar llamada
        data = request.get_json() or {}
        numero_destino = data.get('numero', '+34616000211')  # Tu móvil por defecto
        
        # Payload para VAPI API
        payload = {
            "phoneNumberId": VAPI_PHONE_ID,
            "customer": {
                "number": numero_destino
            },
            "assistantId": VAPI_ASSISTANT_ID,
            "assistantOverrides": {
                "firstMessage": "Hola, esta es una llamada de prueba desde VAPI a través de GoTrunk. ¿Me escuchas bien?"
            }
        }
        
        # Headers para VAPI
        headers = {
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print(f"🧪 TEST: Llamando a {numero_destino} desde VAPI...")
        
        # Hacer llamada a VAPI API
        response = requests.post(
            "https://api.vapi.ai/call",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📡 Respuesta VAPI: {response.status_code}")
        print(f"📄 Contenido: {response.text}")
        
        if response.status_code == 201:
            # Llamada iniciada correctamente
            call_data = response.json()
            call_id = call_data.get('id', 'unknown')
            
            # Notificar por Telegram
            enviar_telegram_mejora(f"""
🧪 <b>TEST LLAMADA SALIENTE VAPI</b>

📞 <b>Destino:</b> {numero_destino}
🆔 <b>Call ID:</b> {call_id}
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}

✅ <b>Estado:</b> Llamada iniciada correctamente
🔍 <b>Test:</b> Verificar si suena y hay audio
            """)
            
            return jsonify({
                "status": "success",
                "message": f"✅ Llamada iniciada a {numero_destino}",
                "call_id": call_id,
                "debug": "Revisa tu móvil - debería sonar en 5-10 segundos"
            })
            
        else:
            # Error en la llamada
            error_detail = response.text
            
            enviar_telegram_mejora(f"""
❌ <b>ERROR TEST LLAMADA VAPI</b>

📞 <b>Destino:</b> {numero_destino}
🔴 <b>Status:</b> {response.status_code}
📄 <b>Error:</b> {error_detail[:200]}

🔍 <b>Diagnóstico:</b> Problema con GoTrunk + VAPI
            """)
            
            return jsonify({
                "status": "error",
                "message": f"❌ Error iniciando llamada: {response.status_code}",
                "detail": error_detail,
                "possible_cause": "Problema de configuración GoTrunk + VAPI"
            }), response.status_code
            
    except Exception as e:
        print(f"❌ Error en test llamada: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "status": "error",
            "message": f"❌ Excepción: {str(e)}",
            "type": type(e).__name__
        }), 500

# Formulario HTML para el test
FORM_TEST_LLAMADA = '''
<!DOCTYPE html>
<html>
<head>
    <title>🧪 Test Llamada Saliente VAPI</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .container { background: #f9f9f9; padding: 30px; border-radius: 10px; }
        h1 { color: #007bff; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .alert { padding: 15px; margin: 15px 0; border-radius: 5px; }
        .alert-info { background: #d1ecf1; color: #0c5460; }
        .alert-warning { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Test Llamada Saliente VAPI</h1>
        
        <div class="alert alert-info">
            <strong>ℹ️ Objetivo:</strong> Verificar si VAPI puede hacer llamadas salientes a través de GoTrunk (no transferencias).
        </div>
        
        <div class="alert alert-warning">
            <strong>⚠️ Importante:</strong> Ten tu móvil preparado - debería sonar en 5-10 segundos después de hacer clic.
        </div>
        
        <div id="result"></div>
        
        <form onsubmit="testLlamada(event)">
            <div class="form-group">
                <label for="numero">📞 Número de destino:</label>
                <input type="tel" id="numero" value="+34616000211" required>
                <small>Formato: +34XXXXXXXXX</small>
            </div>
            
            <button type="submit">📞 Iniciar Llamada de Prueba</button>
        </form>
        
        <h3>🔍 Qué verificar:</h3>
        <ul>
            <li>✅ <strong>Suena el teléfono:</strong> VAPI + GoTrunk funciona</li>
            <li>✅ <strong>Audio claro:</strong> Conexión OK</li>
            <li>✅ <strong>Sofia responde:</strong> Asistente funciona</li>
            <li>❌ <strong>No suena:</strong> Problema GoTrunk + VAPI</li>
            <li>❌ <strong>No hay audio:</strong> Problema de codec/RTP</li>
        </ul>
    </div>

    <script>
        function testLlamada(event) {
            event.preventDefault();
            
            const numero = document.getElementById('numero').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<div class="alert alert-info">🔄 Iniciando llamada de prueba...</div>';
            
            fetch('/test/llamada-saliente', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ numero: numero })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    resultDiv.innerHTML = `
                        <div class="alert alert-success" style="background: #d4edda; color: #155724;">
                            ✅ ${data.message}<br>
                            🆔 Call ID: ${data.call_id}<br>
                            📱 ${data.debug}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-error" style="background: #f8d7da; color: #721c24;">
                            ❌ ${data.message}<br>
                            📄 ${data.detail || ''}
                        </div>
                    `;
                }
            })
            .catch(error => {
                resultDiv.innerHTML = `
                    <div class="alert alert-error" style="background: #f8d7da; color: #721c24;">
                        ❌ Error de conexión: ${error.message}
                    </div>
                `;
            });
        }
    </script>
</body>
</html>
'''

@app.route('/test/estado-vapi')
def test_estado_vapi():
    """Verificar configuración básica de VAPI"""
    try:
        # Verificar variables de entorno
        variables_vapi = {
            "VAPI_API_KEY": os.getenv("VAPI_API_KEY", "❌ No configurada"),
            "VAPI_PHONE_ID": os.getenv("VAPI_PHONE_ID", "❌ No configurada"), 
            "VAPI_SOFIA_ID": os.getenv("VAPI_SOFIA_ID", "❌ No configurada")
        }
        
        # Test de conectividad básica con VAPI API
        if os.getenv("VAPI_API_KEY"):
            try:
                headers = {"Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}"}
                response = requests.get("https://api.vapi.ai/phone-number", headers=headers, timeout=10)
                api_status = f"✅ {response.status_code}" if response.status_code == 200 else f"❌ {response.status_code}"
            except Exception as e:
                api_status = f"❌ Error: {str(e)}"
        else:
            api_status = "❌ Sin API Key"
        
        return jsonify({
            "status": "info",
            "message": "Estado de configuración VAPI",
            "variables": variables_vapi,
            "api_connectivity": api_status,
            "next_steps": [
                "1. Configurar variables de entorno VAPI",
                "2. Probar llamada saliente",
                "3. Comparar con transferencias"
            ]
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
        
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