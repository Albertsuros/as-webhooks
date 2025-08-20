#!/usr/bin/env python3
"""
Sistema de procesamiento de fotos por email para AS Cartastral
Procesa emails con fotos de manos/facial y las guarda en static/
"""

import imaplib
import email
import os
import time
from datetime import datetime, timedelta
import sqlite3
import json

class EmailPhotoProcessor:
    def __init__(self):
        self.email_user = os.getenv("EMAIL_SENDER")
        self.email_password = os.getenv("EMAIL_PASSWORD") 
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        
    def conectar_email(self):
        """Conectar al servidor IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_user, self.email_password)
            mail.select('INBOX')
            return mail
        except Exception as e:
            print(f"❌ Error conectando email: {e}")
            return None
    
    def buscar_emails_con_fotos(self, mail, desde_fecha=None):
        """Buscar emails no leídos con attachments desde fecha específica"""
        try:
            if desde_fecha is None:
                desde_fecha = datetime.now() - timedelta(hours=24)
            
            fecha_busqueda = desde_fecha.strftime("%d-%b-%Y")
            
            # Buscar emails no leídos con attachments desde ayer
            status, messages = mail.search(None, f'(UNSEEN SINCE "{fecha_busqueda}")')
            
            if status == 'OK':
                return messages[0].split()
            return []
            
        except Exception as e:
            print(f"❌ Error buscando emails: {e}")
            return []
    
    def procesar_email_con_fotos(self, mail, email_id):
        """Procesar un email específico y extraer fotos"""
        try:
            # Obtener email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return False
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Información del email
            sender = email_message['From']
            subject = email_message['Subject'] or ""
            date_received = email_message['Date']
            
            print(f"📧 Procesando email de: {sender}")
            print(f"📧 Asunto: {subject}")
            
            # Extraer attachments (fotos)
            fotos_guardadas = []
            
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                    
                if part.get('Content-Disposition') is None:
                    continue
                    
                filename = part.get_filename()
                if filename:
                    # Verificar si es imagen
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        foto_info = self.guardar_foto(part, filename, sender)
                        if foto_info:
                            fotos_guardadas.append(foto_info)
            
            if fotos_guardadas:
                # Marcar email como leído
                mail.store(email_id, '+FLAGS', '\\Seen')
                
                # Guardar info en base de datos
                self.registrar_fotos_recibidas(sender, fotos_guardadas, subject)
                
                print(f"✅ {len(fotos_guardadas)} fotos guardadas de {sender}")
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ Error procesando email {email_id}: {e}")
            return False
    
    def guardar_foto(self, email_part, filename_original, sender_email):
        """Guardar foto en static/ con nombre único"""
        try:
            # Crear nombre único basado en timestamp y sender
            timestamp = int(time.time())
            sender_clean = sender_email.split('@')[0][:10]  # Primeros 10 chars antes del @
            
            # Obtener extensión
            _, ext = os.path.splitext(filename_original)
            
            # Nombre único
            filename_unico = f"foto_{sender_clean}_{timestamp}{ext}"
            filepath = os.path.join("static", filename_unico)
            
            # Crear directorio si no existe
            os.makedirs("static", exist_ok=True)
            
            # Guardar archivo
            with open(filepath, 'wb') as f:
                f.write(email_part.get_payload(decode=True))
            
            foto_info = {
                'filename_original': filename_original,
                'filename_guardado': filename_unico,
                'filepath': filepath,
                'size': os.path.getsize(filepath),
                'timestamp': timestamp
            }
            
            print(f"💾 Foto guardada: {filepath}")
            return foto_info
            
        except Exception as e:
            print(f"❌ Error guardando foto: {e}")
            return None
    
    def registrar_fotos_recibidas(self, sender_email, fotos_info, subject=""):
        """Registrar fotos recibidas en base de datos"""
        try:
            conn = sqlite3.connect("calendario_citas.db")
            cur = conn.cursor()
            
            # Crear tabla si no existe
            cur.execute("""
            CREATE TABLE IF NOT EXISTS fotos_recibidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_cliente VARCHAR(255),
                fotos_info TEXT,
                subject TEXT,
                fecha_recepcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                procesado BOOLEAN DEFAULT 0
            )
            """)
            
            # Insertar registro
            fotos_json = json.dumps(fotos_info)
            cur.execute("""
            INSERT INTO fotos_recibidas (email_cliente, fotos_info, subject, procesado)
            VALUES (?, ?, ?, 0)
            """, (sender_email, fotos_json, subject))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Fotos registradas en BD para {sender_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error registrando fotos: {e}")
            return False
    
    def buscar_fotos_cliente(self, email_cliente):
        """Buscar fotos de un cliente específico"""
        try:
            conn = sqlite3.connect("calendario_citas.db")
            cur = conn.cursor()
            
            cur.execute("""
            SELECT fotos_info, fecha_recepcion FROM fotos_recibidas 
            WHERE email_cliente = ? AND procesado = 0
            ORDER BY fecha_recepcion DESC LIMIT 1
            """, (email_cliente,))
            
            resultado = cur.fetchone()
            conn.close()
            
            if resultado:
                fotos_info = json.loads(resultado[0])
                return fotos_info
            
            return None
            
        except Exception as e:
            print(f"❌ Error buscando fotos: {e}")
            return None
    
    def marcar_fotos_procesadas(self, email_cliente):
        """Marcar fotos como procesadas"""
        try:
            conn = sqlite3.connect("calendario_citas.db")
            cur = conn.cursor()
            
            cur.execute("""
            UPDATE fotos_recibidas SET procesado = 1 
            WHERE email_cliente = ? AND procesado = 0
            """, (email_cliente,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error marcando fotos procesadas: {e}")
            return False
    
    def procesar_emails_pendientes(self):
        """Función principal - procesar todos los emails pendientes"""
        print("🔄 Iniciando procesamiento de emails con fotos...")
        
        mail = self.conectar_email()
        if not mail:
            return False
        
        try:
            email_ids = self.buscar_emails_con_fotos(mail)
            
            if not email_ids:
                print("✅ No hay emails con fotos pendientes")
                return True
            
            print(f"📧 Encontrados {len(email_ids)} emails para procesar")
            
            procesados = 0
            for email_id in email_ids:
                if self.procesar_email_con_fotos(mail, email_id):
                    procesados += 1
            
            print(f"✅ Procesados {procesados}/{len(email_ids)} emails con fotos")
            return True
            
        except Exception as e:
            print(f"❌ Error en procesamiento: {e}")
            return False
        finally:
            mail.close()
            mail.logout()

# Función para usar desde sofia.py
def buscar_fotos_cliente_email(email_cliente):
    """Función helper para buscar fotos desde sofia.py"""
    processor = EmailPhotoProcessor()
    return processor.buscar_fotos_cliente(email_cliente)

def marcar_fotos_como_procesadas(email_cliente):
    """Función helper para marcar fotos como procesadas"""
    processor = EmailPhotoProcessor()
    return processor.marcar_fotos_procesadas(email_cliente)

# Script principal para ejecutar manualmente
if __name__ == "__main__":
    processor = EmailPhotoProcessor()
    processor.procesar_emails_pendientes()