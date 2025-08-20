import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
import swisseph as swe
import sqlite3

# Configuración de colores por elemento - CORREGIDOS
COLORES_ELEMENTOS = {
    'fuego': '#FFB3B3',    # Rojo claro para Aries, Leo, Sagitario
    'tierra': '#B3E5B3',   # Verde claro para Tauro, Virgo, Capricornio
    'aire': '#FFFF99',     # Amarillo claro para Géminis, Libra, Acuario
    'agua': '#B3D9FF'      # Azul claro para Cáncer, Escorpio, Piscis
}

COLORES_PLANETAS = {
    'Sol': '#FFD700',      # Dorado
    'Luna': '#C0C0C0',     # Plateado
    'Mercurio': '#FFA500', # Naranja
    'Venus': '#FF69B4',    # Rosa
    'Marte': '#FF0000',    # Rojo
    'Júpiter': '#800080',  # Púrpura
    'Saturno': '#2F4F4F',  # Gris oscuro
    'Urano': '#00FFFF',    # Cian
    'Neptuno': '#0000FF',  # Azul
    'Plutón': '#800000'    # Marrón
}

# Colores de aspectos - CORREGIDOS
COLORES_ASPECTOS = {
    'conjuncion': '#000000',        # Negro
    'semisextil': '#00AA00',        # Verde
    'sextil': '#00AA00',            # Verde
    'trigono': '#00AA00',           # Verde
    'semicuadratura': '#CC0000',    # Rojo
    'cuadratura': '#CC0000',        # Rojo
    'oposicion': '#CC0000',         # Rojo
    'sesquicuadratura': '#8B4513',  # Marrón
    'quincuncio': '#B8860B',        # Amarillo oscuro
    'quintil': '#87CEEB',           # Azul claro
    'biquintil': '#87CEEB'          # Azul claro
}

# Símbolos de signos zodiacales
SIMBOLOS_SIGNOS = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓']
NOMBRES_SIGNOS = ['Aries', 'Tauro', 'Géminis', 'Cáncer', 'Leo', 'Virgo',
                  'Libra', 'Escorpio', 'Sagitario', 'Capricornio', 'Acuario', 'Piscis']

# Elementos de cada signo
ELEMENTOS_SIGNOS = ['fuego', 'tierra', 'aire', 'agua', 'fuego', 'tierra',
                    'aire', 'agua', 'fuego', 'tierra', 'aire', 'agua']

# Símbolos de planetas
SIMBOLOS_PLANETAS = {
    'Sol': '☉', 'Luna': '☽', 'Mercurio': '☿', 'Venus': '♀', 'Marte': '♂',
    'Júpiter': '♃', 'Saturno': '♄', 'Urano': '♅', 'Neptuno': '♆', 'Plutón': '♇'
}

# Planetas Swiss Ephemeris
PLANETAS_SWE = {
    'Sol': swe.SUN,
    'Luna': swe.MOON,
    'Mercurio': swe.MERCURY,
    'Venus': swe.VENUS,
    'Marte': swe.MARS,
    'Júpiter': swe.JUPITER,
    'Saturno': swe.SATURN,
    'Urano': swe.URANUS,
    'Neptuno': swe.NEPTUNE,
    'Plutón': swe.PLUTO
}

def obtener_offset_desde_db(fecha_timestamp, zone_id=1):
    """
    Devuelve el offset horario (en horas) para la fecha en formato timestamp,
    buscando en la tabla timezone. Por defecto zona_id=1 (España).
    """
    try:
        conn = sqlite3.connect("atlas2025.db")
        cur = conn.cursor()
        
        query = """
        SELECT gmt_offset, abbreviation
        FROM timezone
        WHERE zone_id = ? AND time_start <= ?
        ORDER BY time_start DESC
        LIMIT 1
        """
        cur.execute(query, (zone_id, fecha_timestamp))
        row = cur.fetchone()
        conn.close()
        
        if row:
            offset_segundos = row[0]
            abbreviation = row[1]
            offset_horas = offset_segundos / 3600
            print(f"Zona horaria encontrada: {abbreviation} (GMT{offset_horas:+.1f})")
            return offset_horas
        else:
            print(f"No se encontró información de zona horaria para zone_id={zone_id}, usando GMT+1")
            return 1.0  # Por defecto GMT+1
            
    except Exception as e:
        print(f"Error accediendo a la base de datos: {e}")
        return 1.0  # Por defecto GMT+1

def obtener_zone_id_desde_coordenadas(latitud, longitud):
    """
    Obtener zone_id desde las coordenadas geográficas - CORREGIDO
    """
    try:
        conn = sqlite3.connect("atlas2025.db")
        cur = conn.cursor()
        
        # CONVERTIR coordenadas al formato de la BD
        lat_bd = int(latitud * 3600)
        lon_bd = int(longitud * 3600)
        
        # CONSULTA CORREGIDA con nombres reales de columnas
        query = """
        SELECT p.OlsonZoneRule, p.PlaceName, c.country_name_ESP
        FROM places p
        JOIN country c ON p.country_number = c.country_number
        WHERE ABS(p.Latitude - ?) < 3600 AND ABS(p.Longitude - ?) < 3600
        ORDER BY (ABS(p.Latitude - ?) + ABS(p.Longitude - ?)) ASC
        LIMIT 1
        """
        # Convertir coordenadas a segundos de arco
        lat_segundos = latitud * 3600
        lon_segundos = longitud * 3600
        cur.execute(query, (lat_segundos, lon_segundos, lat_segundos, lon_segundos))
        row = cur.fetchone()
        conn.close()
        
        if row:
            olson_zone_rule, ciudad, pais = row
            print(f"Zona encontrada: {ciudad}, {pais} (zone_id: {olson_zone_rule})")
            return olson_zone_rule
        else:
            print(f"No se encontró zona para coordenadas {latitud}, {longitud}. Usando zone_id=1")
            return 1  # Por defecto España
            
    except Exception as e:
        print(f"Error buscando zone_id: {e}")
        return 1  # Por defecto España

def obtener_nombre_ciudad(latitud, longitud):
    """
    Obtener el nombre de la ciudad desde la base de datos atlas2025 - CORREGIDO
    """
    try:
        conn = sqlite3.connect("atlas2025.db")
        cur = conn.cursor()

        # Convertir coordenadas al formato de la BD
        lat_bd = int(latitud * 3600)
        lon_bd = int(longitud * 3600)
        
        # CONSULTA CORREGIDA
        query = """
        SELECT PlaceName, country_number
        FROM Places
        WHERE ABS(Latitude - ?) < 3600 AND ABS(Longitude - ?) < 3600
        ORDER BY (ABS(Latitude - ?) + ABS(Longitude - ?)) ASC
        LIMIT 1
        """
        cur.execute(query, (lat_bd, lon_bd, lat_bd, lon_bd))
        row = cur.fetchone()
        conn.close()
        
        if row:
            ciudad, pais_num = row
            return f"{ciudad}, País #{pais_num}"
        else:
            # Si no encuentra ciudad, usar coordenadas
            lat_hem = "N" if latitud >= 0 else "S"
            lon_hem = "E" if longitud >= 0 else "W"
            return f"Lat: {abs(latitud):.2f}°{lat_hem}, Lon: {abs(longitud):.2f}°{lon_hem}"
            
    except Exception as e:
        print(f"Error buscando ciudad: {e}")
        lat_hem = "N" if latitud >= 0 else "S"
        lon_hem = "E" if longitud >= 0 else "W"
        return f"Lat: {abs(latitud):.2f}°{lat_hem}, Lon: {abs(longitud):.2f}°{lon_hem}"

class CartaRevolucionSolarSola:
    def __init__(self, figsize=(14, 12)):
        self.fig = plt.figure(figsize=figsize, facecolor='white')
        self.ax = self.fig.add_subplot(111, polar=True)
        self.configurar_ejes()
        
    def configurar_ejes(self):
        """Configurar los ejes polares - Ascendente fijo a la izquierda"""
        self.ax.set_theta_direction(1)      # Sentido antihorario
        self.ax.set_theta_offset(np.pi)     # 0° a la izquierda (Ascendente)
        self.ax.set_ylim(0, 1.5)
        self.ax.set_yticklabels([])
        self.ax.grid(False)
        
    def calcular_julian_day(self, año, mes, dia, hora, minuto, segundo=0, latitud=None, longitud=None):
        """Calcular día juliano para Swiss Ephemeris usando base de datos automáticamente"""
        
        # Obtener zone_id desde coordenadas - CORREGIDO
        if latitud is not None and longitud is not None:
            zone_id = obtener_zone_id_desde_coordenadas(latitud, longitud)
        else:
            zone_id = 1  # Por defecto España
        
        # Crear fecha en formato Unix timestamp manualmente para consultar la BD
        fecha_dt = datetime(año, mes, dia, hora, minuto, segundo)
        
        try:
            # Intentar usar timestamp normal
            timestamp = fecha_dt.timestamp()
        except (OSError, ValueError):
            # Para fechas anteriores a 1970, calcular timestamp manual
            epoch = datetime(1970, 1, 1)
            if fecha_dt < epoch:
                # Calcular segundos desde epoch (será negativo)
                delta = fecha_dt - epoch
                timestamp = delta.total_seconds()
            else:
                timestamp = 0
        
        offset_horas = obtener_offset_desde_db(timestamp, zone_id)
        
        # Convertir hora local a UTC
        hora_utc = hora - offset_horas
        print(f"Hora local: {hora:02d}:{minuto:02d} -> Hora UTC: {hora_utc:.2f}")
        
        return swe.julday(año, mes, dia, hora_utc + minuto/60.0 + segundo/3600.0)
    
    def obtener_posicion_sol_natal(self, jd_natal):
        """Obtener la posición exacta del Sol natal"""
        try:
            resultado = swe.calc_ut(jd_natal, swe.SUN)
            longitud_sol_natal = resultado[0][0]
            return longitud_sol_natal
        except Exception as e:
            print(f"Error calculando Sol natal: {e}")
            return 0.0
    
    def calcular_fecha_revolucion_solar(self, año_revolucion, posicion_sol_natal, lugar_revolucion):
        """Calcular la fecha exacta cuando el Sol vuelve a su posición natal"""
        latitud, longitud = lugar_revolucion
        
        # Fecha aproximada del cumpleaños
        fecha_aproximada = datetime(año_revolucion, 10, 1, 12, 0)  # 1 de octubre al mediodía
        jd_aproximado = self.calcular_julian_day(año_revolucion, 10, 1, 12, 0, latitud=latitud, longitud=longitud)
        
        # Buscar el momento exacto (iteración)
        tolerancia = 0.01  # 0.01 grados de tolerancia
        max_iteraciones = 100
        
        for i in range(max_iteraciones):
            # Calcular posición actual del Sol
            resultado = swe.calc_ut(jd_aproximado, swe.SUN)
            posicion_sol_actual = resultado[0][0]
            
            # Diferencia con la posición natal
            diferencia = posicion_sol_actual - posicion_sol_natal
            
            # Normalizar diferencia (-180 a +180)
            if diferencia > 180:
                diferencia -= 360
            elif diferencia < -180:
                diferencia += 360
            
            # Si estamos dentro de la tolerancia, terminamos
            if abs(diferencia) < tolerancia:
                break
            
            # Ajustar el Julian Day (aproximadamente 1 grado = 1 día)
            jd_aproximado -= diferencia / 1.0
        
        # Convertir de vuelta a fecha
        fecha_revolucion = swe.revjul(jd_aproximado)
        año, mes, dia, hora_decimal = fecha_revolucion
        
        hora = int(hora_decimal)
        minuto = int((hora_decimal - hora) * 60)
        
        return (año, mes, dia, hora, minuto), jd_aproximado
    
    def obtener_posiciones_planetas(self, jd):
        """Obtener posiciones planetarias usando Swiss Ephemeris - CON DETECCIÓN DE RETRÓGRADOS"""
        posiciones = {}
        
        for nombre, planeta_id in PLANETAS_SWE.items():
            try:
                # Obtener posición y velocidad del planeta
                resultado = swe.calc_ut(jd, planeta_id)
                longitud = resultado[0][0]
                velocidad = resultado[0][3]  # Velocidad en longitud (grados/día)
                
                # Determinar si está retrógrado (velocidad negativa)
                es_retrogrado = velocidad < 0
                
                posiciones[nombre] = {
                    'grado': longitud,
                    'velocidad': velocidad,
                    'retrogrado': es_retrogrado
                }
                
            except Exception as e:
                print(f"Error calculando {nombre}: {e}")
                
        return posiciones
    
    def calcular_casas_placidus(self, jd, latitud, longitud):
        """Calcular casas usando sistema Placidus con Swiss Ephemeris"""
        try:
            casas_info = swe.houses(jd, latitud, longitud, b'P')
            cuspides = list(casas_info[0])
            ascendente = casas_info[1][0]
            mediocielo = casas_info[1][1]
            
            return cuspides, ascendente, mediocielo
        except Exception as e:
            print(f"Error calculando casas: {e}")
            cuspides = [i * 30 for i in range(12)]
            return cuspides, 0, 90
    
    def grado_a_coordenada_carta(self, grado_absoluto, ascendente):
        """Convertir grado zodiacal absoluto a coordenada de carta"""
        grado_relativo = (grado_absoluto - ascendente) % 360
        return np.deg2rad(grado_relativo)
    
    def dibujar_circulos_concentricos(self):
        """Dibujar los círculos concéntricos de la carta"""
        radios = [0.3, 0.6, 0.75, 0.9, 1.0]
        for radio in radios:
            circle = plt.Circle((0, 0), radio, fill=False, color='black', 
                              linewidth=1.5, transform=self.ax.transData._b)
            self.ax.add_patch(circle)
    
    def dibujar_divisiones_casas(self, cuspides_casas, ascendente):
        """Dibujar las divisiones de las 12 casas"""
        color = 'black'
        linewidth = 1.1
        linestyle = '-'
        radio_inicio = 0.3
        radio_fin = 1.0
        
        for i, cuspide in enumerate(cuspides_casas):
            angle = self.grado_a_coordenada_carta(cuspide, ascendente)
            
            # Línea de división
            self.ax.plot([angle, angle], [radio_inicio, radio_fin], 
                        color=color, lw=linewidth, linestyle=linestyle)
            
            # Centro de casa para número
            cuspide_siguiente = cuspides_casas[(i + 1) % 12]
            
            if cuspide_siguiente < cuspide:
                centro_casa = (cuspide + (cuspide_siguiente + 360 - cuspide) / 2) % 360
            else:
                centro_casa = (cuspide + cuspide_siguiente) / 2
            
            casa_angle = self.grado_a_coordenada_carta(centro_casa, ascendente)
            
            # Número de casa
            self.ax.text(casa_angle, 0.45, str(i + 1), 
                        ha='center', va='center', fontsize=9, 
                        weight='normal', color='black')
    
    def dibujar_ascendente_mediocielo(self, ascendente, mediocielo):
        """Dibujar Ascendente y Mediocielo"""
        color_asc = 'red'
        color_mc = 'blue'
        linewidth = 3
        y_pos = 1.35
        fontsize = 8
        
        # ASC fijo a la izquierda
        asc_angle = np.deg2rad(0)
        mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente)
        
        # ASCENDENTE
        self.ax.plot([asc_angle, asc_angle], [0.3, 1.0], 
                    color=color_asc, lw=linewidth, linestyle='-', alpha=1.0)
        
        signo_asc_idx = int(ascendente // 30)
        grado_asc = ascendente % 30
        
        self.ax.text(asc_angle, y_pos, f"ASC\n{NOMBRES_SIGNOS[signo_asc_idx][:3]} {grado_asc:.1f}°", 
                    ha='center', va='center', fontsize=fontsize, 
                    weight='bold', color=color_asc,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # MEDIOCIELO
        self.ax.plot([mc_angle, mc_angle], [0.3, 1.0], 
                    color=color_mc, lw=linewidth, linestyle='-', alpha=1.0)
        
        signo_mc_idx = int(mediocielo // 30)
        grado_mc = mediocielo % 30
        self.ax.text(mc_angle, y_pos, f"MC\n{NOMBRES_SIGNOS[signo_mc_idx][:3]} {grado_mc:.1f}°", 
                    ha='center', va='center', fontsize=fontsize, 
                    weight='bold', color=color_mc,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
    
    def dibujar_signos_zodiacales(self, ascendente):
        """Dibujar signos zodiacales con colores"""
        for i in range(12):
            grado_inicio_signo = i * 30
            grado_fin_signo = (i + 1) * 30
            grado_centro_signo = grado_inicio_signo + 15
            
            angle_inicio = self.grado_a_coordenada_carta(grado_inicio_signo, ascendente)
            angle_fin = self.grado_a_coordenada_carta(grado_fin_signo, ascendente)
            angle_centro = self.grado_a_coordenada_carta(grado_centro_signo, ascendente)
            
            elemento = ELEMENTOS_SIGNOS[i]
            color = COLORES_ELEMENTOS[elemento]
            
            if angle_fin < angle_inicio:
                angles1 = np.linspace(angle_inicio, 2*np.pi, 50)
                angles2 = np.linspace(0, angle_fin, 50)
                angles = np.concatenate([angles1, angles2])
            else:
                angles = np.linspace(angle_inicio, angle_fin, 100)
            
            x_outer = np.cos(angles) * 1.0
            y_outer = np.sin(angles) * 1.0
            x_inner = np.cos(angles) * 0.9
            y_inner = np.sin(angles) * 0.9
            
            x_coords = np.concatenate([x_outer, x_inner[::-1]])
            y_coords = np.concatenate([y_outer, y_inner[::-1]])
            
            self.ax.fill(np.arctan2(y_coords, x_coords), 
                        np.sqrt(x_coords**2 + y_coords**2),
                        color=color, alpha=0.4)
            
            # Símbolo del signo
            self.ax.text(angle_centro, 0.95, SIMBOLOS_SIGNOS[i], 
                        ha='center', va='center', fontsize=14, 
                        weight='bold', color='black')
    
    def dibujar_planetas_revolucion_solar(self, pos_revolucion, ascendente):
        """Dibujar planetas de revolución solar en posición centrada"""
        
        # Planetas de revolución solar en posición estándar (radio 0.75)
        for planeta, data in pos_revolucion.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo del planeta (centrado)
            self.ax.text(rad, 0.75, simbolo, ha='center', va='center', 
                        fontsize=20, weight='bold', color=color)
            
            # Información del planeta (arriba del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 1.12, f"{signo[:3]} {grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=9, weight='bold',
                        color='darkred' if es_retrogrado else 'darkgreen',
                        bbox=dict(boxstyle="round,pad=0.2", 
                        facecolor='lightpink' if es_retrogrado else 'lightyellow', 
                        alpha=0.8))
            
            # Información del planeta (debajo del símbolo) - más pequeña
            self.ax.text(rad, 0.60, f"{signo[:3]}\n{grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=7, 
                        color='darkblue', weight='bold')
    
    def calcular_aspectos_revolucion_solar(self, pos_revolucion, ascendente_rs, mediocielo_rs):
        """Calcular aspectos entre planetas de revolución solar Y también a ASC/MC"""
        aspectos = []
        
        tolerancias = {
            'conjuncion': 8, 'oposicion': 8,
            'cuadratura': 7, 'trigono': 7,
            'sextil': 6,
            'semisextil': 3, 'quincuncio': 3,
            'semicuadratura': 3, 'sesquicuadratura': 3,
            'quintil': 2, 'biquintil': 2
        }
        
        angulos_aspectos = {
            'conjuncion': 0, 'semisextil': 30, 'sextil': 60,
            'cuadratura': 90, 'trigono': 120, 'quincuncio': 150,
            'oposicion': 180, 'semicuadratura': 45, 'sesquicuadratura': 135,
            'quintil': 72, 'biquintil': 144
        }
        
        # ASPECTOS PLANETA-PLANETA (entre planetas de revolución solar)
        planetas_lista = list(pos_revolucion.items())
        for i, (planeta1, data1) in enumerate(planetas_lista):
            for j, (planeta2, data2) in enumerate(planetas_lista[i+1:], i+1):
                grado1 = data1['grado']
                grado2 = data2['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado1 - grado2)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'tipo_aspecto': 'planeta-planeta',
                            'planeta1': planeta1,
                            'planeta2': planeta2,
                            'aspecto': aspecto,
                            'orbe': orbe,
                            'grado1': grado1,
                            'grado2': grado2,
                            'diferencia_angular': diferencia
                        })
                        break
        
        # ASPECTOS PLANETA - ASC/MC
        puntos_angulares = {
            'Ascendente': ascendente_rs,
            'Mediocielo': mediocielo_rs
        }
        
        for planeta, data in pos_revolucion.items():
            for punto_angular, grado_angular in puntos_angulares.items():
                grado_planeta = data['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_planeta - grado_angular)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'tipo_aspecto': 'planeta-punto',
                            'planeta1': planeta,
                            'planeta2': punto_angular,
                            'aspecto': aspecto,
                            'orbe': orbe,
                            'grado1': grado_planeta,
                            'grado2': grado_angular,
                            'diferencia_angular': diferencia
                        })
                        break
        
        return aspectos
    
    def dibujar_aspectos_revolucion_solar(self, aspectos, ascendente):
        """Dibujar líneas de aspectos (solo planeta-planeta)"""
        for aspecto in aspectos:
            # Solo dibujar aspectos planeta-planeta para no saturar la carta
            if aspecto['tipo_aspecto'] != 'planeta-planeta':
                continue
                
            grado1 = aspecto['grado1']
            grado2 = aspecto['grado2']
            
            rad1 = self.grado_a_coordenada_carta(grado1, ascendente)
            rad2 = self.grado_a_coordenada_carta(grado2, ascendente)
            
            color = COLORES_ASPECTOS.get(aspecto['aspecto'], 'purple')
            
            # Línea de aspecto centrada
            self.ax.plot([rad1, rad2], [0.75, 0.75], 
                        color=color, linewidth=1.5, alpha=0.7, linestyle='-')

    def crear_carta_revolucion_solar_sola(self, fecha_natal, lugar_natal, ciudad_natal,
                                         año_revolucion, lugar_revolucion, ciudad_revolucion,
                                         guardar_archivo=True, directorio_salida="static", nombre_archivo=None):
        """Crear la carta de revolución solar sola completa"""
        
        print(f"\n=== CALCULANDO REVOLUCIÓN SOLAR SOLA {año_revolucion} ===")
        
        # Calcular posiciones natales (solo para obtener la posición del Sol natal)
        año_natal, mes_natal, dia_natal, hora_natal, min_natal = fecha_natal
        latitud_natal, longitud_natal = lugar_natal
        jd_natal = self.calcular_julian_day(año_natal, mes_natal, dia_natal, hora_natal, min_natal, 
                                          latitud=latitud_natal, longitud=longitud_natal)
        
        # Obtener posición exacta del Sol natal
        posicion_sol_natal = self.obtener_posicion_sol_natal(jd_natal)
        print(f"Sol natal en: {posicion_sol_natal:.4f}°")
        
        # Calcular fecha exacta de revolución solar
        fecha_revolucion, jd_revolucion = self.calcular_fecha_revolucion_solar(
            año_revolucion, posicion_sol_natal, lugar_revolucion
        )
        
        año_rs, mes_rs, dia_rs, hora_rs, min_rs = fecha_revolucion
        print(f"Fecha de Revolución Solar: {dia_rs:02d}/{mes_rs:02d}/{año_rs} {hora_rs:02d}:{min_rs:02d}")
        
        # Calcular posiciones de revolución solar
        pos_revolucion = self.obtener_posiciones_planetas(jd_revolucion)
        
        # Verificar que el Sol esté en la posición correcta
        sol_revolucion = pos_revolucion['Sol']['grado']
        diferencia_sol = abs(sol_revolucion - posicion_sol_natal)
        if diferencia_sol > 180:
            diferencia_sol = 360 - diferencia_sol
        print(f"Sol revolución en: {sol_revolucion:.4f}° (diferencia: {diferencia_sol:.4f}°)")
        
        # Casas de revolución solar
        latitud_rs, longitud_rs = lugar_revolucion
        cuspides_rs, ascendente_rs, mediocielo_rs = self.calcular_casas_placidus(jd_revolucion, latitud_rs, longitud_rs)
        
        # Dibujar la carta (usando ascendente de revolución solar como referencia)
        self.dibujar_circulos_concentricos()
        self.dibujar_signos_zodiacales(ascendente_rs)
        self.dibujar_divisiones_casas(cuspides_rs, ascendente_rs)
        self.dibujar_ascendente_mediocielo(ascendente_rs, mediocielo_rs)
        self.dibujar_planetas_revolucion_solar(pos_revolucion, ascendente_rs)
        
        # Calcular y dibujar aspectos
        aspectos = self.calcular_aspectos_revolucion_solar(pos_revolucion, ascendente_rs, mediocielo_rs)
        self.dibujar_aspectos_revolucion_solar(aspectos, ascendente_rs)
        
        # Información de la carta
        fecha_natal_str = f"{dia_natal:02d}/{mes_natal:02d}/{año_natal} {hora_natal:02d}:{min_natal:02d}"
        fecha_rs_str = f"{dia_rs:02d}/{mes_rs:02d}/{año_rs} {hora_rs:02d}:{min_rs:02d}"
        
        titulo = f"REVOLUCIÓN SOLAR {año_revolucion}\nPersona nacida: {fecha_natal_str} - {ciudad_natal}\nRevolución Solar: {fecha_rs_str} - {ciudad_revolucion}"
        
        self.fig.text(0.85, 0.95, titulo, 
                     fontsize=10, weight='bold', ha='center', va='top',
                     bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgoldenrodyellow', alpha=0.8))
        
        # Leyenda
        self.crear_leyenda_revolucion_solar_sola()
        
        # Guardar archivo
        if guardar_archivo:
            self.guardar_revolucion_solar_sola_con_nombre_unico(
                fecha_natal, año_revolucion, directorio_salida
            )
        
        # MOSTRAR INFORMACIÓN COMPLETA EN CONSOLA
        self.mostrar_informacion_completa_revolucion_solar_sola(
            pos_revolucion, aspectos, ascendente_rs, mediocielo_rs,
            ciudad_revolucion, fecha_revolucion
        )
        
        return aspectos, pos_revolucion, fecha_revolucion
    
    def mostrar_informacion_completa_revolucion_solar_sola(self, pos_revolucion, aspectos,
                                                          ascendente_rs, mediocielo_rs,
                                                          ciudad_revolucion, fecha_revolucion):
        """Mostrar información completa de la revolución solar sola en consola"""
        
        año_rs, mes_rs, dia_rs, hora_rs, min_rs = fecha_revolucion
        
        print(f"\n" + "="*60)
        print(f"INFORMACIÓN COMPLETA DE REVOLUCIÓN SOLAR {año_rs}")
        print(f"="*60)
        
        # POSICIONES PLANETARIAS REVOLUCIÓN SOLAR
        print(f"\n=== POSICIONES PLANETARIAS ({ciudad_revolucion}) ===")
        print(f"Fecha exacta: {dia_rs:02d}/{mes_rs:02d}/{año_rs} {hora_rs:02d}:{min_rs:02d}")
        for planeta, data in pos_revolucion.items():
            grado = data['grado']
            signo_idx = int(grado // 30)
            grado_en_signo = grado % 30
            signo = NOMBRES_SIGNOS[signo_idx]
            retrogrado = " ℞" if data.get('retrogrado', False) else ""
            print(f"• {planeta}: {signo} {grado_en_signo:.2f}° ({grado:.2f}° absoluto){retrogrado}")
        
        # ASC/MC REVOLUCIÓN SOLAR
        print(f"\n=== PUNTOS ANGULARES ===")
        asc_signo_idx = int(ascendente_rs // 30)
        asc_grado = ascendente_rs % 30
        mc_signo_idx = int(mediocielo_rs // 30)
        mc_grado = mediocielo_rs % 30
        print(f"• Ascendente: {NOMBRES_SIGNOS[asc_signo_idx]} {asc_grado:.2f}° ({ascendente_rs:.2f}° absoluto)")
        print(f"• Mediocielo: {NOMBRES_SIGNOS[mc_signo_idx]} {mc_grado:.2f}° ({mediocielo_rs:.2f}° absoluto)")
        
        # ASPECTOS INTERNOS
        if aspectos:
            print(f"\n=== ASPECTOS INTERNOS DE LA REVOLUCIÓN SOLAR ({len(aspectos)}) ===")
            # Separar aspectos por tipo
            aspectos_planeta_planeta = [a for a in aspectos if a['tipo_aspecto'] == 'planeta-planeta']
            aspectos_planeta_punto = [a for a in aspectos if a['tipo_aspecto'] == 'planeta-punto']
            
            if aspectos_planeta_planeta:
                print(f"\n--- ASPECTOS PLANETA-PLANETA ({len(aspectos_planeta_planeta)}) ---")
                aspectos_planeta_planeta.sort(key=lambda x: x['orbe'])
                for aspecto in aspectos_planeta_planeta:
                    print(f"• {aspecto['planeta1']} {aspecto['aspecto'].upper()} {aspecto['planeta2']} - Orbe: {aspecto['orbe']:.2f}°")
            
            if aspectos_planeta_punto:
                print(f"\n--- ASPECTOS PLANETA-ASC/MC ({len(aspectos_planeta_punto)}) ---")
                aspectos_planeta_punto.sort(key=lambda x: x['orbe'])
                for aspecto in aspectos_planeta_punto:
                    print(f"• {aspecto['planeta1']} {aspecto['aspecto'].upper()} {aspecto['planeta2']} - Orbe: {aspecto['orbe']:.2f}°")
        else:
            print("\n=== NO SE ENCONTRARON ASPECTOS SIGNIFICATIVOS ===")
        
        # PLANETAS RETRÓGRADOS
        print(f"\n=== PLANETAS RETRÓGRADOS ===")
        retrogrados = [planeta for planeta, data in pos_revolucion.items() if data.get('retrogrado', False)]
        if retrogrados:
            for planeta in retrogrados:
                print(f"• {planeta} ℞")
        else:
            print("• Ninguno")
        
        print(f"\n" + "="*60)
    
    def crear_leyenda_revolucion_solar_sola(self):
        """Crear leyenda explicativa de la revolución solar sola"""
        leyenda_texto = [
            "LEYENDA:",
            "• Carta de Revolución Solar únicamente",
            "• Planetas en posiciones del momento exacto", 
            "• cuando el Sol vuelve a su posición natal",
            "• Líneas de colores: Aspectos internos",
            "• ℞ = Planeta retrógrado",
            "• Válida para todo el año solar"
        ]
        
        self.fig.text(0.02, 0.98, '\n'.join(leyenda_texto), 
                     fontsize=8, ha='left', va='top',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgoldenrodyellow', alpha=0.9))

    def guardar_revolucion_solar_sola_con_nombre_unico(self, fecha_natal, año_revolucion, directorio_salida):
        """Guardar la carta con un nombre único"""
        
        # Crear directorio si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
            print(f"Directorio creado: {directorio_salida}")
        
        # Crear nombre base del archivo
        año_natal, mes_natal, dia_natal, hora_natal, min_natal = fecha_natal
        
        # Si se proporciona nombre específico, usarlo
        if hasattr(self, 'nombre_archivo_personalizado') and self.nombre_archivo_personalizado:
            ruta_completa = self.nombre_archivo_personalizado
        else:
            nombre_base = f"revolucion_solar_sola_{año_natal}{mes_natal:02d}{dia_natal:02d}_{hora_natal:02d}{min_natal:02d}_RS{año_revolucion}"
        
            # Buscar un nombre único
            contador = 1
            nombre_archivo = f"{nombre_base}.png"
            ruta_completa = os.path.join(directorio_salida, nombre_archivo)
            
            while os.path.exists(ruta_completa):
                nombre_archivo = f"{nombre_base}_{contador:03d}.png"
                ruta_completa = os.path.join(directorio_salida, nombre_archivo)
                contador += 1
        
        # Guardar el archivo
        try:
            self.fig.savefig(ruta_completa, dpi=300, bbox_inches='tight', 
                     facecolor='white', edgecolor='none')
            print(f"✓ Carta de revolución solar sola guardada como: {ruta_completa}")
            return ruta_completa
        except Exception as e:
            print(f"✗ Error guardando la carta: {e}")
            return None

# FUNCIÓN MAIN PARA REVOLUCIÓN SOLAR SOLA
def main(nombre_archivo_salida=None):
    """Función principal para generar revolución solar sola"""
    print("=== GENERADOR DE CARTA DE REVOLUCIÓN SOLAR SOLA ===")
    print("Calculando revolución solar sola...")
    
    # DATOS NATALES: 1 de octubre de 1959 a las 11:47 h en Barcelona
    fecha_natal = (1959, 10, 1, 11, 47)  # año, mes, día, hora, minuto
    lugar_natal = (41.39, 2.16)          # Barcelona: latitud, longitud
    ciudad_natal = "Barcelona, España"
    
    # REVOLUCIÓN SOLAR PARA AÑO 2024
    año_revolucion = 2024
    lugar_revolucion = (41.39, 2.16)     # Barcelona (donde vive actualmente)
    ciudad_revolucion = "Barcelona, España"
    
    print(f"Natal: {fecha_natal[2]:02d}/{fecha_natal[1]:02d}/{fecha_natal[0]} {fecha_natal[3]:02d}:{fecha_natal[4]:02d} - {ciudad_natal}")
    print(f"Revolución Solar: {año_revolucion} - {ciudad_revolucion}")
    
    try:
        # Crear instancia de la clase
        carta = CartaRevolucionSolarSola(figsize=(16, 14))
        if nombre_archivo_salida:
            carta.nombre_archivo_personalizado = nombre_archivo_salida
        
        # Generar la carta de revolución solar sola
        aspectos, pos_revolucion, fecha_revolucion = carta.crear_carta_revolucion_solar_sola(
            fecha_natal=fecha_natal,
            lugar_natal=lugar_natal,
            ciudad_natal=ciudad_natal,
            año_revolucion=año_revolucion,
            lugar_revolucion=lugar_revolucion,
            ciudad_revolucion=ciudad_revolucion,
            guardar_archivo=True,
            directorio_salida="revoluciones_solares_solas_generadas"
        )
        
        # Mostrar la carta
        plt.tight_layout()
        # plt.show()  # Comentado para servidor
        
        print("\n✓ Carta de revolución solar sola generada exitosamente")
        
    except Exception as e:
        print(f"✗ Error en la generación: {e}")
        import traceback
        traceback.print_exc()

# FUNCIÓN PARA MÚLTIPLES AÑOS
def generar_revoluciones_solas_multiples_años():
    """Generar revoluciones solares solas para múltiples años"""
    print("=== GENERADOR DE REVOLUCIONES SOLARES SOLAS MÚLTIPLES AÑOS ===")
    
    # DATOS NATALES
    fecha_natal = (1959, 10, 1, 11, 47)
    lugar_natal = (41.39, 2.16)
    ciudad_natal = "Barcelona, España"
    
    # LUGAR ACTUAL
    lugar_revolucion = (41.39, 2.16)
    ciudad_revolucion = "Barcelona, España"
    
    # AÑOS A GENERAR
    años_revolucion = [2022, 2023, 2024, 2025, 2026]
    
    for i, año in enumerate(años_revolucion, 1):
        try:
            print(f"\n--- Generando revolución solar sola {i}/{len(años_revolucion)} ---")
            print(f"Año: {año}")
            
            # Crear nueva instancia para cada carta
            carta = CartaRevolucionSolarSola(figsize=(16, 14))
            
            # Generar la carta
            aspectos, pos_revolucion, fecha_revolucion = carta.crear_carta_revolucion_solar_sola(
                fecha_natal=fecha_natal,
                lugar_natal=lugar_natal,
                ciudad_natal=ciudad_natal,
                año_revolucion=año,
                lugar_revolucion=lugar_revolucion,
                ciudad_revolucion=ciudad_revolucion,
                guardar_archivo=True,
                directorio_salida="revoluciones_solas_multiples"
            )
            
            print(f"✓ Revolución Solar Sola {año} completada - Aspectos encontrados: {len(aspectos)}")
            
            # Cerrar figura para liberar memoria
            plt.close()
            
        except Exception as e:
            print(f"✗ Error en revolución {año}: {e}")
    
    print("\n✓ Todas las revoluciones solares solas generadas exitosamente")

# FUNCIÓN PERSONALIZADA PARA SOFIA - CORREGIDA CON DATOS DINÁMICOS
def generar_revolucion_solar_sola_personalizada(datos_usuario=None, nombre_archivo_salida=None):
    """Generar revolución solar sola con datos REALES del usuario"""
    print("=== GENERADOR DE REVOLUCIÓN SOLAR SOLA PERSONALIZADO ===")
    
    if not datos_usuario:
        print("❌ Error: No se proporcionaron datos del usuario")
        return None
    
    try:
        # ✅ EXTRAER DATOS REALES DEL USUARIO
        nombre = datos_usuario.get('nombre', 'Usuario')
        fecha_nac_str = datos_usuario.get('fecha_nacimiento')      # "15/07/1985"
        hora_nac_str = datos_usuario.get('hora_nacimiento')        # "14:30"
        ciudad_nac = datos_usuario.get('ciudad_nacimiento')        # "Barcelona"
        pais_nac = datos_usuario.get('pais_nacimiento', 'España')  # "España"
        residencia = datos_usuario.get('residencia_actual')       # "Madrid"
        ano_rev = datos_usuario.get('ano_revolucion', 2025)       # 2025
        
        # Convertir fecha y hora de string a tupla
        dia, mes, ano = fecha_nac_str.split('/')
        hora, minuto = hora_nac_str.split(':')
        fecha_natal = (int(ano), int(mes), int(dia), int(hora), int(minuto))
        
        # ✅ OBTENER COORDENADAS DINÁMICAS
        coordenadas_ciudades = {
            'Barcelona': (41.38, 2.18),
            'Madrid': (40.42, -3.70),
            'Valencia': (39.47, -0.38),
            'Sevilla': (37.39, -5.98),
            'París': (48.86, 2.34)
        }
        
        lugar_natal = coordenadas_ciudades.get(ciudad_nac, (40.42, -3.70))
        ciudad_natal = f"{ciudad_nac}, {pais_nac}"
        
        año_revolucion = ano_rev
        lugar_revolucion = coordenadas_ciudades.get(residencia, lugar_natal)
        ciudad_revolucion = f"{residencia}, {pais_nac}"
        
        print("Datos configurados:")
        print(f"• Natal: {fecha_natal[2]:02d}/{fecha_natal[1]:02d}/{fecha_natal[0]} {fecha_natal[3]:02d}:{fecha_natal[4]:02d} - {ciudad_natal}")
        print(f"• Revolución Solar: {año_revolucion} - {ciudad_revolucion}")
        
        # ✅ GENERAR CARTA CON DATOS REALES
        carta = CartaRevolucionSolarSola(figsize=(16, 14))
        
        if nombre_archivo_salida:
            carta.nombre_archivo_personalizado = nombre_archivo_salida
        
        aspectos, pos_revolucion, fecha_revolucion = carta.crear_carta_revolucion_solar_sola(
            fecha_natal=fecha_natal,
            lugar_natal=lugar_natal,
            ciudad_natal=ciudad_natal,
            año_revolucion=año_revolucion,
            lugar_revolucion=lugar_revolucion,
            ciudad_revolucion=ciudad_revolucion,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        plt.tight_layout()
        
        print(f"✓ Revolución Solar Sola personalizada generada exitosamente")
        print(f"✓ Usuario: {nombre}")
        print(f"✓ Datos natales: {fecha_natal}")
        print(f"✓ Aspectos encontrados: {len(aspectos)}")
        
        return {
            'success': True,
            'aspectos': aspectos,
            'archivo': nombre_archivo_salida,
            'datos_usados': {
                'nombre': nombre,
                'fecha_natal': fecha_natal,
                'ciudad_natal': ciudad_natal,
                'año_revolucion': año_revolucion,
                'ciudad_revolucion': ciudad_revolucion
            }
        }
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

# EJECUTAR EL PROGRAMA
if __name__ == "__main__":
    main()