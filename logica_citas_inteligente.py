# ========================================
# LÓGICA INTELIGENTE DE CITAS - VERÓNICA Y SOFÍA
# ========================================

import sqlite3
from datetime import datetime, timedelta
import pytz

# ========================================
# FUNCIONES PARA VERÓNICA (AS ASESORES)
# ========================================

def calcular_margen_veronica(ultima_cita_tipo, nueva_cita_tipo):
    """
    Calcular margen necesario entre citas de Verónica
    """
    if ultima_cita_tipo == 'telefono' and nueva_cita_tipo == 'presencial':
        return 90  # 1.5 horas
    elif ultima_cita_tipo == 'presencial':
        return 90  # Siempre 1.5 horas después de presencial
    else:
        return 30  # teléfono → teléfono

def obtener_ultima_cita_veronica(fecha):
    """
    Obtener la última cita de Verónica antes de la fecha dada
    """
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT ca.horario, cs.tipo_servicio
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE cs.tipo_servicio IN ('veronica_presencial', 'veronica_telefono')
        AND ca.fecha_cita = ?
        AND ca.estado_cita = 'confirmada'
        ORDER BY ca.horario DESC
        LIMIT 1
        """, (fecha.strftime('%Y-%m-%d'),))
        
        resultado = cur.fetchone()
        conn.close()
        
        if resultado:
            horario = resultado[0]  # "10:00-10:30"
            tipo = 'presencial' if 'presencial' in resultado[1] else 'telefono'
            
            # Convertir horario a datetime
            hora_fin = horario.split('-')[1]  # "10:30"
            hora, minuto = map(int, hora_fin.split(':'))
            
            fecha_hora = datetime.combine(fecha, datetime.min.time().replace(hour=hora, minute=minuto))
            
            return fecha_hora, tipo
        
        return None, None
        
    except Exception as e:
        print(f"❌ Error obteniendo última cita Verónica: {e}")
        return None, None

def obtener_horarios_veronica_inteligentes(fecha, tipo_nueva_cita):
    """
    Obtener horarios disponibles para Verónica con lógica inteligente
    """
    try:
        # Horarios base cada 30 minutos
        horarios_base = []
        
        # Mañana: 09:00 a 13:00 (cada 30min)
        for hora in range(9, 13):
            for minuto in [0, 30]:
                if not (hora == 13 and minuto == 30):  # No 13:30
                    inicio = f"{hora:02d}:{minuto:02d}"
                    fin_min = minuto + 30
                    fin_hora = hora
                    if fin_min >= 60:
                        fin_min -= 60
                        fin_hora += 1
                    fin = f"{fin_hora:02d}:{fin_min:02d}"
                    horarios_base.append(f"{inicio}-{fin}")
        
        # Tarde: 16:00 a 19:00 (cada 30min)
        for hora in range(16, 19):
            for minuto in [0, 30]:
                inicio = f"{hora:02d}:{minuto:02d}"
                fin_min = minuto + 30
                fin_hora = hora
                if fin_min >= 60:
                    fin_min -= 60
                    fin_hora += 1
                fin = f"{fin_hora:02d}:{fin_min:02d}"
                horarios_base.append(f"{inicio}-{fin}")
        
        # Obtener última cita del día
        ultima_cita_hora, ultima_cita_tipo = obtener_ultima_cita_veronica(fecha)
        
        # Filtrar horarios según margen necesario
        horarios_disponibles = []
        
        for horario in horarios_base:
            hora_inicio = horario.split('-')[0]
            hora, minuto = map(int, hora_inicio.split(':'))
            fecha_hora_inicio = datetime.combine(fecha, datetime.min.time().replace(hour=hora, minute=minuto))
            
            # Si hay cita previa, verificar margen
            if ultima_cita_hora and ultima_cita_tipo:
                margen_necesario = calcular_margen_veronica(ultima_cita_tipo, tipo_nueva_cita)
                diferencia = (fecha_hora_inicio - ultima_cita_hora).total_seconds() / 60
                
                if diferencia < margen_necesario:
                    continue  # Saltar este horario
            
            # Verificar si está libre (no ocupado por otra cita)
            if not esta_horario_ocupado('veronica_' + tipo_nueva_cita, fecha, horario):
                horarios_disponibles.append(horario)
        
        return horarios_disponibles
        
    except Exception as e:
        print(f"❌ Error calculando horarios Verónica: {e}")
        return []

# ========================================
# FUNCIONES PARA SOFÍA (AS CARTASTRAL)
# ========================================

def verificar_antelacion_sofia(fecha_hora_cita):
    """
    Verificar que la cita tiene al menos 5 horas de antelación
    """
    try:
        ahora = datetime.now()
        diferencia = fecha_hora_cita - ahora
        horas_diferencia = diferencia.total_seconds() / 3600
        
        return horas_diferencia >= 5.0
        
    except Exception as e:
        print(f"❌ Error verificando antelación: {e}")
        return False

def obtener_proximo_dia_laboral():
    """
    Obtener el próximo día laboral (lunes a sábado)
    """
    try:
        hoy = datetime.now()
        dia = hoy + timedelta(days=1)
        
        # Si es domingo (6), avanzar a lunes
        while dia.weekday() == 6:  # 6 = domingo
            dia += timedelta(days=1)
        
        return dia
        
    except Exception as e:
        print(f"❌ Error calculando próximo día laboral: {e}")
        return datetime.now() + timedelta(days=1)

def obtener_horarios_sofia_con_antelacion(fecha_solicitada, tipo_servicio):
    """
    Obtener horarios de Sofia con verificación de antelación de 5h
    """
    try:
        ahora = datetime.now()
        
        # Si la fecha solicitada es hoy, verificar antelación
        if fecha_solicitada.date() == ahora.date():
            # Verificar si aún se puede agendar para hoy
            hora_limite = datetime.combine(fecha_solicitada, datetime.min.time().replace(hour=14, minute=0))
            
            if ahora >= hora_limite:
                # Ya no se puede agendar para hoy - devolver próximo día laboral
                fecha_solicitada = obtener_proximo_dia_laboral()
        
        # Horarios base de Sofia (cada hora para servicios humanos)
        horarios_base = []
        
        # Determinar horarios según tipo de servicio
        if tipo_servicio in ['astrologo_humano', 'tarot_humano']:
            # Servicios humanos: horarios de 1 hora
            horas_disponibles = [11, 12, 13, 16, 17, 18, 19]  # Última a las 19:00h
            
            for hora in horas_disponibles:
                inicio = f"{hora:02d}:00"
                fin = f"{hora + 1:02d}:00"
                horario = f"{inicio}-{fin}"
                
                # Verificar antelación de 5 horas
                fecha_hora_cita = datetime.combine(fecha_solicitada, datetime.min.time().replace(hour=hora))
                
                if verificar_antelacion_sofia(fecha_hora_cita):
                    if not esta_horario_ocupado(tipo_servicio, fecha_solicitada, horario):
                        horarios_base.append(horario)
        
        return horarios_base, fecha_solicitada
        
    except Exception as e:
        print(f"❌ Error calculando horarios Sofia: {e}")
        return [], fecha_solicitada

# ========================================
# FUNCIONES AUXILIARES
# ========================================

def esta_horario_ocupado(tipo_servicio, fecha, horario):
    """
    Verificar si un horario específico está ocupado
    """
    try:
        conn = sqlite3.connect("calendario_citas.db")
        cur = conn.cursor()
        
        cur.execute("""
        SELECT COUNT(*)
        FROM citas_agendadas ca
        JOIN clientes_servicios cs ON ca.cliente_servicio_id = cs.id
        WHERE cs.tipo_servicio = ?
        AND ca.fecha_cita = ?
        AND ca.horario = ?
        AND ca.estado_cita != 'cancelada'
        """, (tipo_servicio, fecha.strftime('%Y-%m-%d'), horario))
        
        resultado = cur.fetchone()[0]
        conn.close()
        
        return resultado > 0
        
    except Exception as e:
        print(f"❌ Error verificando ocupación: {e}")
        return False

def agendar_cita_inteligente(tipo_servicio, fecha, horario, cliente_datos):
    """
    Agendar cita con todas las validaciones inteligentes
    """
    try:
        # Separar empresa y tipo
        if tipo_servicio.startswith('veronica_'):
            empresa = 'AS_ASESORES'
            tipo_cita = tipo_servicio.replace('veronica_', '')
            
            # Verificar márgenes para Verónica
            ultima_hora, ultimo_tipo = obtener_ultima_cita_veronica(fecha)
            if ultima_hora and ultimo_tipo:
                # Convertir horario solicitado a datetime
                hora_inicio = horario.split('-')[0]
                hora, minuto = map(int, hora_inicio.split(':'))
                fecha_hora_nueva = datetime.combine(fecha, datetime.min.time().replace(hour=hora, minute=minuto))
                
                margen_necesario = calcular_margen_veronica(ultimo_tipo, tipo_cita)
                diferencia = (fecha_hora_nueva - ultima_hora).total_seconds() / 60
                
                if diferencia < margen_necesario:
                    return False, f"Necesita {margen_necesario} minutos de margen. Próximo disponible: {(ultima_hora + timedelta(minutes=margen_necesario)).strftime('%H:%M')}"
        
        elif tipo_servicio in ['astrologo_humano', 'tarot_humano']:
            empresa = 'AS_CARTASTRAL'
            
            # Verificar antelación para Sofia
            hora_inicio = horario.split('-')[0]
            hora, minuto = map(int, hora_inicio.split(':'))
            fecha_hora_cita = datetime.combine(fecha, datetime.min.time().replace(hour=hora, minute=minuto))
            
            if not verificar_antelacion_sofia(fecha_hora_cita):
                proximo_dia = obtener_proximo_dia_laboral()
                return False, f"Necesita 5h de antelación. Próximo disponible: {proximo_dia.strftime('%d/%m/%Y')}"
        
        # Si pasa todas las validaciones, proceder con agendamiento normal
        from main import registrar_cliente_servicio, agendar_cita_especifica
        
        cliente_id = registrar_cliente_servicio(
            codigo_servicio=f"INT_{int(datetime.now().timestamp())}",
            tipo_servicio=tipo_servicio,
            cliente_datos=cliente_datos,
            numero_telefono=cliente_datos.get('telefono', ''),
            especialista=empresa
        )
        
        if cliente_id:
            exito, codigo_reserva = agendar_cita_especifica(cliente_id, fecha, horario, tipo_servicio)
            return exito, codigo_reserva
        
        return False, "Error creando cliente"
        
    except Exception as e:
        print(f"❌ Error en agendamiento inteligente: {e}")
        return False, str(e)

# ========================================
# FUNCIÓN PRINCIPAL DE INTEGRACIÓN
# ========================================

def obtener_horarios_disponibles_inteligentes(tipo_servicio, fecha_solicitada):
    """
    Función principal que maneja todos los tipos de servicio con lógica inteligente
    """
    try:
        if tipo_servicio.startswith('veronica_'):
            # Lógica Verónica con márgenes
            tipo_cita = tipo_servicio.replace('veronica_', '')
            horarios = obtener_horarios_veronica_inteligentes(fecha_solicitada, tipo_cita)
            return horarios, fecha_solicitada
            
        elif tipo_servicio in ['astrologo_humano', 'tarot_humano']:
            # Lógica Sofia con antelación
            horarios, fecha_final = obtener_horarios_sofia_con_antelacion(fecha_solicitada, tipo_servicio)
            return horarios, fecha_final
            
        else:
            # Otros servicios (horarios normales)
            from main import obtener_horarios_disponibles
            horarios = obtener_horarios_disponibles(tipo_servicio, fecha_solicitada)
            return horarios, fecha_solicitada
            
    except Exception as e:
        print(f"❌ Error en obtener_horarios_disponibles_inteligentes: {e}")
        return [], fecha_solicitada

# ========================================
# EJEMPLOS DE USO
# ========================================

"""
# Para Verónica:
horarios, fecha = obtener_horarios_disponibles_inteligentes('veronica_presencial', datetime(2025, 8, 10))

# Para Sofia:
horarios, fecha = obtener_horarios_disponibles_inteligentes('astrologo_humano', datetime.now())

# Agendar con validaciones:
exito, codigo = agendar_cita_inteligente(
    'veronica_telefono',
    datetime(2025, 8, 10),
    '10:00-10:30',
    {'nombre': 'Juan Pérez', 'email': 'juan@email.com', 'telefono': '600123456'}
)
"""