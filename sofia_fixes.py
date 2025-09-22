# ========================================
# SOLUCIÓN COMPLETA - Funciones Wrapper para Sofia
# ========================================

# 1. FUNCIÓN WRAPPER PARA PROGRESIONES
def generar_progresiones_desde_datos_natales(datos_natales, archivo_salida):
    """Wrapper para generar progresiones usando datos_natales reales"""
    try:
        print(f"🔧 Generando progresiones con datos: {datos_natales}")
        
        # Extraer datos del diccionario datos_natales
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', '')
        lugar_actual = datos_natales.get('residencia_actual', lugar_nacimiento)
        
        # Convertir fecha string (DD/MM/YYYY) a tuple (YYYY, MM, DD, HH, MM)
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_nacimiento = (año, mes, dia, hora, minuto)
        else:
            print("❌ Error: formato de fecha/hora incorrecto")
            return None
        
        # COORDENADAS APROXIMADAS (mejorar con geocoding real)
        coordenadas_ciudades = {
            'Madrid': (40.42, -3.70),
            'Barcelona': (41.39, 2.16),
            'Valencia': (39.47, -0.38),
            'Sevilla': (37.38, -5.98),
            'Bilbao': (43.26, -2.93),
        }
        
        # Buscar coordenadas (fallback a Madrid)
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        for ciudad, coords in coordenadas_ciudades.items():
            if ciudad.lower() in lugar_nacimiento.lower():
                lugar_coords = coords
                break
        
        actual_coords = lugar_coords  # Por simplicidad, usar mismo lugar
        
        print(f"📍 Coordenadas: {lugar_coords}")
        print(f"⏰ Fecha natal: {fecha_nacimiento}")
        
        # Crear instancia de CartaProgresiones
        from progresiones import CartaProgresiones
        carta = CartaProgresiones(figsize=(16, 14))
        
        # Configurar archivo de salida
        if archivo_salida:
            carta.nombre_archivo_personalizado = archivo_salida
        
        # Calcular edad actual
        from datetime import datetime
        hoy = datetime.now()
        fecha_nac_dt = datetime(*fecha_nacimiento)
        edad_actual = (hoy - fecha_nac_dt).days / 365.25
        
        print(f"👤 Edad actual: {edad_actual:.2f} años")
        
        # Generar la carta de progresiones
        aspectos, pos_natales, pos_progresadas, fecha_consulta_dt, fecha_progresion = carta.crear_carta_progresiones(
            fecha_nacimiento=fecha_nacimiento,
            edad_consulta=edad_actual,
            lugar_nacimiento=lugar_coords,
            lugar_actual=actual_coords,
            ciudad_nacimiento=lugar_nacimiento,
            ciudad_actual=lugar_actual,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        print("✅ Progresiones generadas correctamente")
        
        # Retornar datos compatibles con Sofia
        return {
            'aspectos': aspectos,
            'pos_natales': pos_natales,
            'pos_progresadas': pos_progresadas,
            'fecha_consulta': fecha_consulta_dt,
            'fecha_progresion': fecha_progresion
        }
        
    except Exception as e:
        print(f"❌ Error generando progresiones: {e}")
        import traceback
        traceback.print_exc()
        return None


# 2. FUNCIÓN WRAPPER PARA TRÁNSITOS  
def generar_transitos_desde_datos_natales(datos_natales, archivo_salida):
    """Wrapper para generar tránsitos usando datos_natales reales"""
    try:
        print(f"🔧 Generando tránsitos con datos: {datos_natales}")
        
        # Extraer datos del diccionario datos_natales
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', '')
        
        # Convertir fecha string (DD/MM/YYYY) a tuple (YYYY, MM, DD, HH, MM)
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_nacimiento = (año, mes, dia, hora, minuto)
        else:
            print("❌ Error: formato de fecha/hora incorrecto")
            return None
        
        # COORDENADAS APROXIMADAS
        coordenadas_ciudades = {
            'Madrid': (40.42, -3.70),
            'Barcelona': (41.39, 2.16),
            'Valencia': (39.47, -0.38),
            'Sevilla': (37.38, -5.98),
            'Bilbao': (43.26, -2.93),
        }
        
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        for ciudad, coords in coordenadas_ciudades.items():
            if ciudad.lower() in lugar_nacimiento.lower():
                lugar_coords = coords
                break
        
        # Fecha de tránsito = HOY
        from datetime import datetime
        hoy = datetime.now()
        fecha_transito = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
        
        print(f"📍 Coordenadas: {lugar_coords}")
        print(f"⏰ Fecha natal: {fecha_nacimiento}")
        print(f"🌍 Fecha tránsito: {fecha_transito}")
        
        # Crear instancia de CartaTransitos
        from transitos import CartaTransitos
        carta = CartaTransitos(figsize=(16, 14))
        
        # Configurar archivo de salida
        if archivo_salida:
            carta.nombre_archivo_personalizado = archivo_salida
        
        # Generar la carta de tránsitos
        aspectos, pos_natales, pos_transitos, fecha_trans_dt, edad = carta.crear_carta_transitos(
            fecha_nacimiento=fecha_nacimiento,
            fecha_transito=fecha_transito,
            lugar_nacimiento=lugar_coords,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        print("✅ Tránsitos generados correctamente")
        
        # Retornar datos compatibles con Sofia
        return {
            'aspectos': aspectos,
            'pos_natales': pos_natales,
            'pos_transitos': pos_transitos,
            'fecha_transito': fecha_trans_dt,
            'edad': edad
        }
        
    except Exception as e:
        print(f"❌ Error generando tránsitos: {e}")
        import traceback
        traceback.print_exc()
        return None


# 3. FUNCIÓN WRAPPER PARA CARTA NATAL
def generar_carta_natal_desde_datos_natales(datos_natales, archivo_salida):
    """Wrapper para generar carta natal usando datos_natales reales"""
    try:
        print(f"🔧 Generando carta natal con datos: {datos_natales}")
        
        # Extraer datos del diccionario datos_natales
        fecha_str = datos_natales.get('fecha_nacimiento', '')
        hora_str = datos_natales.get('hora_nacimiento', '')
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', '')
        
        # Convertir fecha string (DD/MM/YYYY) a tuple (YYYY, MM, DD, HH, MM)
        if '/' in fecha_str and ':' in hora_str:
            dia, mes, año = map(int, fecha_str.split('/'))
            hora, minuto = map(int, hora_str.split(':'))
            fecha_natal = (año, mes, dia, hora, minuto)
        else:
            print("❌ Error: formato de fecha/hora incorrecto")
            return None
        
        # COORDENADAS APROXIMADAS
        coordenadas_ciudades = {
            'Madrid': (40.42, -3.70),
            'Barcelona': (41.39, 2.16),
            'Valencia': (39.47, -0.38),
            'Sevilla': (37.38, -5.98),
            'Bilbao': (43.26, -2.93),
        }
        
        lugar_coords = coordenadas_ciudades.get('Madrid', (40.42, -3.70))
        ciudad_nombre = 'Madrid, España'
        for ciudad, coords in coordenadas_ciudades.items():
            if ciudad.lower() in lugar_nacimiento.lower():
                lugar_coords = coords
                ciudad_nombre = f"{ciudad}, España"
                break
        
        print(f"📍 Coordenadas: {lugar_coords}")
        print(f"⏰ Fecha natal: {fecha_natal}")
        
        # Crear instancia de CartaAstralNatal
        from carta_natal import CartaAstralNatal
        carta = CartaAstralNatal(figsize=(16, 14))
        
        # Configurar archivo de salida
        if archivo_salida:
            carta.nombre_archivo_personalizado = archivo_salida
        
        # Generar la carta astral natal
        aspectos, posiciones = carta.crear_carta_astral_natal(
            fecha_natal=fecha_natal,
            lugar_natal=lugar_coords,
            ciudad_natal=ciudad_nombre,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        print("✅ Carta natal generada correctamente")
        
        # Retornar datos compatibles con Sofia
        return {
            'aspectos': aspectos,
            'posiciones': posiciones
        }
        
    except Exception as e:
        print(f"❌ Error generando carta natal: {e}")
        import traceback
        traceback.print_exc()
        return None


# ========================================
# REEMPLAZOS EN SOFIA.PY
# ========================================

"""
EN sofia.py, REEMPLAZAR estas líneas:

# LÍNEA ~1200: 
from progresiones import generar_progresiones_personalizada as generar_progresiones
from transitos import generar_transitos_personalizada as generar_transitos

# POR:
# Importar funciones wrapper corregidas
exec(open('sofia_fixes.py').read())  # Cargar funciones de este archivo
generar_progresiones = generar_progresiones_desde_datos_natales
generar_transitos = generar_transitos_desde_datos_natales

# Y TAMBIÉN REEMPLAZAR en la función generar_cartas_astrales_completas():

# ANTES:
carta_natal = CartaAstralNatal(
    nombre=datos_natales['nombre'],
    fecha_nacimiento=datos_natales['fecha_nacimiento'],
    hora_nacimiento=datos_natales['hora_nacimiento'],
    lugar_nacimiento=datos_natales['lugar_nacimiento'],
    residencia_actual=datos_natales['residencia_actual']
)
carta_natal.generar_carta_completa(archivo_salida=archivos_unicos['carta_natal_img'])

# DESPUÉS:  
datos_carta_natal = generar_carta_natal_desde_datos_natales(datos_natales, archivos_unicos['carta_natal_img'])

"""