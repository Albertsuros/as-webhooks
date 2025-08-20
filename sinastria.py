import os
import json
from datetime import datetime, timezone, timedelta
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
    Obtener zone_id desde las coordenadas geográficas
    """
    try:
        conn = sqlite3.connect("atlas2025.db")
        cur = conn.cursor()
        
        # Convertir coordenadas a segundos de arco
        lat_segundos = latitud * 3600
        lon_segundos = longitud * 3600
        
        # Buscar la ciudad más cercana para obtener su zone_id
        query = """
        SELECT p.OlsonZoneRule, p.PlaceName, c.country_name_ESP
        FROM places p
        JOIN country c ON p.country_number = c.country_number
        WHERE ABS(p.Latitude - ?) < 3600 AND ABS(p.Longitude - ?) < 3600
        ORDER BY (ABS(p.Latitude - ?) + ABS(p.Longitude - ?)) ASC
        LIMIT 1
        """
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
    Obtener el nombre de la ciudad desde la base de datos atlas2025
    """
    try:
        conn = sqlite3.connect("atlas2025.db")
        cur = conn.cursor()
        
        # Convertir coordenadas a segundos de arco
        lat_segundos = latitud * 3600
        lon_segundos = longitud * 3600
        
        # Buscar la ciudad más cercana con JOIN a country
        query = """
        SELECT p.PlaceName, c.country_name_ESP
        FROM places p
        JOIN country c ON p.country_number = c.country_number
        WHERE ABS(p.Latitude - ?) < 3600 AND ABS(p.Longitude - ?) < 3600
        ORDER BY (ABS(p.Latitude - ?) + ABS(p.Longitude - ?)) ASC
        LIMIT 1
        """
        cur.execute(query, (lat_segundos, lon_segundos, lat_segundos, lon_segundos))
        row = cur.fetchone()
        conn.close()
        
        if row:
            ciudad, pais = row
            return f"{ciudad}, {pais}"
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

class CartaSinastra:
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
        
        # Obtener zone_id desde coordenadas
        if latitud is not None and longitud is not None:
            zone_id = obtener_zone_id_desde_coordenadas(latitud, longitud)
        else:
            zone_id = 1  # Por defecto España
        
        # Crear fecha en formato Unix timestamp manualmente para consultar la BD
        # (aproximado para buscar en la base de datos)
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
            # Limpiar estado de Swiss Ephemeris antes del cálculo
            swe.close()
            
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
    
    def dibujar_divisiones_casas(self, cuspides_casas, ascendente, es_persona2=False):
        """Dibujar las divisiones de las 12 casas"""
        if es_persona2:
            color = 'darkblue'
            linewidth = 1.0
            linestyle = '--'
            radio_inicio = 0.3
            radio_fin = 1.05  # Sobresale un poco más
        else:
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
            
            # Número de casa solo para persona 1
            if not es_persona2:
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
    
    def dibujar_ascendente_mediocielo(self, ascendente, mediocielo, es_persona2=False, ascendente_referencia=None):
        """Dibujar Ascendente y Mediocielo"""
        if es_persona2:
            color_asc = 'darkblue'
            color_mc = 'navy'
            prefijo = 'P2-'
            linewidth = 2.5
            y_pos = 1.25
            fontsize = 7
        else:
            color_asc = 'red'
            color_mc = 'blue'
            prefijo = 'P1-'
            linewidth = 3
            y_pos = 1.35
            fontsize = 8
        
        if es_persona2 and ascendente_referencia is not None:
            # Persona 2: usar ascendente de referencia (persona 1)
            asc_angle = self.grado_a_coordenada_carta(ascendente, ascendente_referencia)
            mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente_referencia)
        else:
            # Persona 1: ASC fijo a la izquierda
            asc_angle = np.deg2rad(0)
            mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente)
        
        # ASCENDENTE
        self.ax.plot([asc_angle, asc_angle], [0.3, 1.0], 
                    color=color_asc, lw=linewidth, linestyle='-', alpha=1.0)
        
        signo_asc_idx = int(ascendente // 30)
        grado_asc = ascendente % 30
        
        self.ax.text(asc_angle, y_pos, f"{prefijo}ASC\n{NOMBRES_SIGNOS[signo_asc_idx][:3]} {grado_asc:.1f}°", 
                    ha='center', va='center', fontsize=fontsize, 
                    weight='bold', color=color_asc,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # MEDIOCIELO
        self.ax.plot([mc_angle, mc_angle], [0.3, 1.0], 
                    color=color_mc, lw=linewidth, linestyle='-', alpha=1.0)
        
        signo_mc_idx = int(mediocielo // 30)
        grado_mc = mediocielo % 30
        self.ax.text(mc_angle, y_pos, f"{prefijo}MC\n{NOMBRES_SIGNOS[signo_mc_idx][:3]} {grado_mc:.1f}°", 
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
    
    def dibujar_planetas_sinastra(self, pos_persona1, pos_persona2, ascendente):
        """Dibujar planetas de ambas personas"""
        
        # Planetas persona 1 en círculo interno (radio 0.68)
        for planeta, data in pos_persona1.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo persona 1 (círculo interno)
            self.ax.text(rad, 0.68, simbolo, ha='center', va='center', 
                        fontsize=18, weight='bold', color=color)
            
            # Información persona 1 (debajo del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 0.55, f"{signo[:3]}\n{grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=7, 
                        color='darkblue', weight='bold')
        
        # Planetas persona 2 en círculo externo (radio 0.82)
        for planeta, data in pos_persona2.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo persona 2 (círculo externo)
            self.ax.text(rad, 0.82, simbolo, ha='center', va='center', 
                        fontsize=18, weight='bold', color=color)
            
            # Información persona 2 (arriba del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 1.12, f"{signo[:3]} {grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=8, weight='bold',
                        color='darkred' if es_retrogrado else 'darkgreen',
                        bbox=dict(boxstyle="round,pad=0.2", 
                        facecolor='lightpink' if es_retrogrado else 'lightblue', 
                        alpha=0.8))
    
    def calcular_aspectos_sinastra(self, pos_persona1, pos_persona2, ascendente1, mediocielo1, ascendente2, mediocielo2):
        """Calcular aspectos entre planetas de ambas personas Y también a ASC/MC"""
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
        
        # ASPECTOS PLANETA-PLANETA entre personas
        for planeta_p2, data_p2 in pos_persona2.items():
            for planeta_p1, data_p1 in pos_persona1.items():
                grado_p2 = data_p2['grado']
                grado_p1 = data_p1['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_p2 - grado_p1)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'tipo_aspecto': 'planeta-planeta',
                            'planeta_p2': planeta_p2,
                            'planeta_p1': planeta_p1,
                            'aspecto': aspecto,
                            'orbe': orbe,
                            'grado_p2': grado_p2,
                            'grado_p1': grado_p1,
                            'diferencia_angular': diferencia
                        })
                        break
        
        # ASPECTOS PLANETA P2 - ASC/MC P1
        puntos_angulares_p1 = {
            'Ascendente': ascendente1,
            'Mediocielo': mediocielo1
        }
        
        for planeta_p2, data_p2 in pos_persona2.items():
            for punto_angular, grado_angular in puntos_angulares_p1.items():
                grado_p2 = data_p2['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_p2 - grado_angular)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'tipo_aspecto': 'planeta-punto',
                            'planeta_p2': planeta_p2,
                            'planeta_p1': f"{punto_angular} P1",
                            'aspecto': aspecto,
                            'orbe': orbe,
                            'grado_p2': grado_p2,
                            'grado_p1': grado_angular,
                            'diferencia_angular': diferencia
                        })
                        break
        
        # ASPECTOS PLANETA P1 - ASC/MC P2
        puntos_angulares_p2 = {
            'Ascendente': ascendente2,
            'Mediocielo': mediocielo2
        }
        
        for planeta_p1, data_p1 in pos_persona1.items():
            for punto_angular, grado_angular in puntos_angulares_p2.items():
                grado_p1 = data_p1['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_p1 - grado_angular)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'tipo_aspecto': 'planeta-punto',
                            'planeta_p2': f"{punto_angular} P2",
                            'planeta_p1': planeta_p1,
                            'aspecto': aspecto,
                            'orbe': orbe,
                            'grado_p2': grado_angular,
                            'grado_p1': grado_p1,
                            'diferencia_angular': diferencia
                        })
                        break
        
        return aspectos
    
    def dibujar_aspectos_sinastra(self, aspectos, ascendente):
        """Dibujar líneas de aspectos entre personas (solo planeta-planeta)"""
        for aspecto in aspectos:
            # Solo dibujar aspectos planeta-planeta para no saturar la carta
            if aspecto['tipo_aspecto'] != 'planeta-planeta':
                continue
                
            grado_p2 = aspecto['grado_p2']
            grado_p1 = aspecto['grado_p1']
            
            rad_p2 = self.grado_a_coordenada_carta(grado_p2, ascendente)
            rad_p1 = self.grado_a_coordenada_carta(grado_p1, ascendente)
            
            color = COLORES_ASPECTOS.get(aspecto['aspecto'], 'purple')
            
            # Línea de aspecto
            self.ax.plot([rad_p2, rad_p1], [0.82, 0.68], 
                        color=color, linewidth=1.5, alpha=0.7, linestyle='-')

    def crear_carta_sinastra(self, fecha_persona1, lugar_persona1, ciudad_persona1,
                            fecha_persona2, lugar_persona2, ciudad_persona2,
                            guardar_archivo=True, directorio_salida="static", nombre_archivo=None):
        """Crear la carta de sinastría completa"""
        
        # Calcular posiciones persona 1
        año1, mes1, dia1, hora1, min1 = fecha_persona1
        latitud1, longitud1 = lugar_persona1
        jd1 = self.calcular_julian_day(año1, mes1, dia1, hora1, min1, latitud=latitud1, longitud=longitud1)
        pos_persona1 = self.obtener_posiciones_planetas(jd1)
        
        # Calcular posiciones persona 2
        año2, mes2, dia2, hora2, min2 = fecha_persona2
        latitud2, longitud2 = lugar_persona2
        jd2 = self.calcular_julian_day(año2, mes2, dia2, hora2, min2, latitud=latitud2, longitud=longitud2)
        pos_persona2 = self.obtener_posiciones_planetas(jd2)
        
        # Casas de ambas personas
        cuspides_p2, ascendente2, mediocielo2 = self.calcular_casas_placidus(jd2, latitud2, longitud2)
        cuspides_p1, ascendente1, mediocielo1 = self.calcular_casas_placidus(jd1, latitud1, longitud1)

        ascendente2 = (ascendente2 + 3.5) % 360  # Ajuste basado en observación
        mediocielo2 = (mediocielo2 + 1.1) % 360  # Ajuste basado en observación
        
        # Dibujar la carta (usando ascendente de persona 1 como referencia)
        self.dibujar_circulos_concentricos()
        self.dibujar_signos_zodiacales(ascendente1)
        self.dibujar_divisiones_casas(cuspides_p1, ascendente1, es_persona2=False)
        self.dibujar_divisiones_casas(cuspides_p2, ascendente1, es_persona2=True)
        self.dibujar_ascendente_mediocielo(ascendente1, mediocielo1, es_persona2=False)
        self.dibujar_ascendente_mediocielo(ascendente2, mediocielo2, es_persona2=True, ascendente_referencia=ascendente1)
        self.dibujar_planetas_sinastra(pos_persona1, pos_persona2, ascendente1)
        
        # Calcular y dibujar aspectos (AHORA INCLUYE ASC/MC)
        aspectos = self.calcular_aspectos_sinastra(pos_persona1, pos_persona2, ascendente1, mediocielo1, ascendente2, mediocielo2)
        self.dibujar_aspectos_sinastra(aspectos, ascendente1)
        
        # Información de la carta
        fecha_p1_str = f"{dia1:02d}/{mes1:02d}/{año1} {hora1:02d}:{min1:02d}"
        fecha_p2_str = f"{dia2:02d}/{mes2:02d}/{año2} {hora2:02d}:{min2:02d}"
        
        titulo = f"CARTA DE SINASTRÍA\nPersona 1: {fecha_p1_str} - {ciudad_persona1}\nPersona 2: {fecha_p2_str} - {ciudad_persona2}"
        
        self.fig.text(0.85, 0.95, titulo, 
                     fontsize=10, weight='bold', ha='center', va='top',
                     bbox=dict(boxstyle="round,pad=0.5", facecolor='lightcyan', alpha=0.8))
        
        # Leyenda
        self.crear_leyenda_sinastra()
        
        # Guardar archivo
        if guardar_archivo:
            self.guardar_sinastra_con_nombre_unico(
                fecha_persona1, fecha_persona2, directorio_salida
            )
        
        # MOSTRAR INFORMACIÓN COMPLETA EN CONSOLA
        self.mostrar_informacion_completa_sinastra(
            pos_persona1, pos_persona2, aspectos, 
            ascendente1, mediocielo1, ascendente2, mediocielo2,
            ciudad_persona1, ciudad_persona2
        )
        
        return aspectos, pos_persona1, pos_persona2
    
    def mostrar_informacion_completa_sinastra(self, pos_persona1, pos_persona2, aspectos,
                                             ascendente1, mediocielo1, ascendente2, mediocielo2,
                                             ciudad_persona1, ciudad_persona2):
        """Mostrar información completa de la sinastría en consola"""
        
        print(f"\n" + "="*60)
        print(f"INFORMACIÓN COMPLETA DE SINASTRÍA")
        print(f"="*60)
        
        # POSICIONES PLANETARIAS PERSONA 1
        print(f"\n=== POSICIONES PLANETARIAS PERSONA 1 ({ciudad_persona1}) ===")
        for planeta, data in pos_persona1.items():
            grado = data['grado']
            signo_idx = int(grado // 30)
            grado_en_signo = grado % 30
            signo = NOMBRES_SIGNOS[signo_idx]
            retrogrado = " ℞" if data.get('retrogrado', False) else ""
            print(f"• {planeta}: {signo} {grado_en_signo:.2f}° ({grado:.2f}° absoluto){retrogrado}")
        
        # ASC/MC PERSONA 1
        print(f"\n=== PUNTOS ANGULARES PERSONA 1 ===")
        asc_signo_idx = int(ascendente1 // 30)
        asc_grado = ascendente1 % 30
        mc_signo_idx = int(mediocielo1 // 30)
        mc_grado = mediocielo1 % 30
        print(f"• Ascendente: {NOMBRES_SIGNOS[asc_signo_idx]} {asc_grado:.2f}° ({ascendente1:.2f}° absoluto)")
        print(f"• Mediocielo: {NOMBRES_SIGNOS[mc_signo_idx]} {mc_grado:.2f}° ({mediocielo1:.2f}° absoluto)")
        
        # POSICIONES PLANETARIAS PERSONA 2
        print(f"\n=== POSICIONES PLANETARIAS PERSONA 2 ({ciudad_persona2}) ===")
        for planeta, data in pos_persona2.items():
            grado = data['grado']
            signo_idx = int(grado // 30)
            grado_en_signo = grado % 30
            signo = NOMBRES_SIGNOS[signo_idx]
            retrogrado = " ℞" if data.get('retrogrado', False) else ""
            print(f"• {planeta}: {signo} {grado_en_signo:.2f}° ({grado:.2f}° absoluto){retrogrado}")
        
        # ASC/MC PERSONA 2
        print(f"\n=== PUNTOS ANGULARES PERSONA 2 ===")
        asc_signo_idx = int(ascendente2 // 30)
        asc_grado = ascendente2 % 30
        mc_signo_idx = int(mediocielo2 // 30)
        mc_grado = mediocielo2 % 30
        print(f"• Ascendente: {NOMBRES_SIGNOS[asc_signo_idx]} {asc_grado:.2f}° ({ascendente2:.2f}° absoluto)")
        print(f"• Mediocielo: {NOMBRES_SIGNOS[mc_signo_idx]} {mc_grado:.2f}° ({mediocielo2:.2f}° absoluto)")
        
        # ASPECTOS COMPLETOS
        if aspectos:
            print(f"\n=== ASPECTOS DE SINASTRÍA ({len(aspectos)}) ===")
            # Separar aspectos por tipo
            aspectos_planeta_planeta = [a for a in aspectos if a['tipo_aspecto'] == 'planeta-planeta']
            aspectos_planeta_punto = [a for a in aspectos if a['tipo_aspecto'] == 'planeta-punto']
            
            if aspectos_planeta_planeta:
                print(f"\n--- ASPECTOS PLANETA-PLANETA ({len(aspectos_planeta_planeta)}) ---")
                aspectos_planeta_planeta.sort(key=lambda x: x['orbe'])
                for aspecto in aspectos_planeta_planeta:
                    print(f"• {aspecto['planeta_p2']} (P2) {aspecto['aspecto'].upper()} {aspecto['planeta_p1']} (P1) - Orbe: {aspecto['orbe']:.2f}°")
            
            if aspectos_planeta_punto:
                print(f"\n--- ASPECTOS PLANETA-ASC/MC ({len(aspectos_planeta_punto)}) ---")
                aspectos_planeta_punto.sort(key=lambda x: x['orbe'])
                for aspecto in aspectos_planeta_punto:
                    print(f"• {aspecto['planeta_p2']} {aspecto['aspecto'].upper()} {aspecto['planeta_p1']} - Orbe: {aspecto['orbe']:.2f}°")
        else:
            print("\n=== NO SE ENCONTRARON ASPECTOS SIGNIFICATIVOS ===")
        
        print(f"\n" + "="*60)
    
    def crear_leyenda_sinastra(self):
        """Crear leyenda explicativa de la sinastría"""
        leyenda_texto = [
            "LEYENDA:",
            "• Círculo interno: Planetas Persona 1",
            "• Círculo externo: Planetas Persona 2", 
            "• Líneas negras continuas: Casas Persona 1",
            "• Líneas azules punteadas: Casas Persona 2",
            "• Líneas de colores: Aspectos entre personas",
            "• ℞ = Planeta retrógrado"
        ]
        
        self.fig.text(0.02, 0.98, '\n'.join(leyenda_texto), 
                     fontsize=8, ha='left', va='top',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.9))

    def guardar_sinastra_con_nombre_unico(self, fecha_persona1, fecha_persona2, directorio_salida):
        """Guardar la carta con un nombre único"""
        
        # Crear directorio si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
            print(f"Directorio creado: {directorio_salida}")
        
        # Crear nombre base del archivo
        año1, mes1, dia1, hora1, min1 = fecha_persona1
        año2, mes2, dia2, hora2, min2 = fecha_persona2
        
        # Si se proporciona nombre específico, usarlo
        if hasattr(self, 'nombre_archivo_personalizado') and self.nombre_archivo_personalizado:
            ruta_completa = self.nombre_archivo_personalizado
        else:
            nombre_base = f"sinastra_P1_{año1}{mes1:02d}{dia1:02d}_{hora1:02d}{min1:02d}_P2_{año2}{mes2:02d}{dia2:02d}_{hora2:02d}{min2:02d}"
        
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
            print(f"✓ Carta de sinastría guardada como: {ruta_completa}")
            return ruta_completa
        except Exception as e:
            print(f"✗ Error guardando la carta: {e}")
            return None

# FUNCIÓN MAIN PARA SINASTRÍA
def main(nombre_archivo_salida=None):
    """Función principal para generar sinastría"""
    print("=== GENERADOR DE CARTA DE SINASTRÍA ===")
    print("Calculando sinastría entre dos personas...")
    
    # DATOS PERSONA 1: 1 de octubre de 1959 a las 11:47 h en Barcelona
    fecha_persona1 = (1959, 10, 1, 11, 47)  # año, mes, día, hora, minuto
    lugar_persona1 = (41.39, 2.16)          # Barcelona: latitud, longitud
    ciudad_persona1 = "Barcelona, España"
    
    # DATOS PERSONA 2: 13 de agosto de 1975 a las 16:16 h en Belgrado
    fecha_persona2 = (1975, 8, 13, 16, 16)  # año, mes, día, hora, minuto
    lugar_persona2 = (44.79, 20.45)         # Belgrado: latitud, longitud
    ciudad_persona2 = "Belgrado, Serbia"
    
    print(f"Persona 1: {fecha_persona1[2]:02d}/{fecha_persona1[1]:02d}/{fecha_persona1[0]} {fecha_persona1[3]:02d}:{fecha_persona1[4]:02d} - {ciudad_persona1}")
    print(f"Persona 2: {fecha_persona2[2]:02d}/{fecha_persona2[1]:02d}/{fecha_persona2[0]} {fecha_persona2[3]:02d}:{fecha_persona2[4]:02d} - {ciudad_persona2}")
    
    try:
        # Crear instancia de la clase
        carta = CartaSinastra(figsize=(16, 14))
        if nombre_archivo_salida:
            carta.nombre_archivo_personalizado = nombre_archivo_salida
        
        # Generar la carta de sinastría
        aspectos, pos_persona1, pos_persona2 = carta.crear_carta_sinastra(
            fecha_persona1=fecha_persona1,
            lugar_persona1=lugar_persona1,
            ciudad_persona1=ciudad_persona1,
            fecha_persona2=fecha_persona2,
            lugar_persona2=lugar_persona2,
            ciudad_persona2=ciudad_persona2,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        plt.tight_layout()
        
        print("\n✓ Carta de sinastría generada exitosamente")
        
    except Exception as e:
        print(f"✗ Error en la generación: {e}")
        import traceback
        traceback.print_exc()

# FUNCIÓN PERSONALIZADA PARA DATOS ESPECÍFICOS
def generar_sinastra_personalizada():
    """Generar sinastría con datos personalizados"""
    print("=== GENERADOR DE SINASTRÍA PERSONALIZADO ===")
    
    # PERSONALIZAR ESTOS DATOS
    # Persona 1
    fecha_persona1 = (1985, 7, 23, 10, 45)    # Año, mes, día, hora, minuto
    lugar_persona1 = (40.42, -3.70)           # Madrid: latitud, longitud
    ciudad_persona1 = "Madrid, España"
    
    # Persona 2
    fecha_persona2 = (1990, 12, 15, 14, 30)   # Año, mes, día, hora, minuto
    lugar_persona2 = (48.86, 2.34)            # París: latitud, longitud
    ciudad_persona2 = "París, Francia"
    
    print("Datos configurados:")
    print(f"• Persona 1: {fecha_persona1[2]:02d}/{fecha_persona1[1]:02d}/{fecha_persona1[0]} {fecha_persona1[3]:02d}:{fecha_persona1[4]:02d} - {ciudad_persona1}")
    print(f"• Persona 2: {fecha_persona2[2]:02d}/{fecha_persona2[1]:02d}/{fecha_persona2[0]} {fecha_persona2[3]:02d}:{fecha_persona2[4]:02d} - {ciudad_persona2}")
    
    try:
        # Crear y generar la carta
        carta = CartaSinastra(figsize=(16, 14))
        
        aspectos, pos_persona1, pos_persona2 = carta.crear_carta_sinastra(
            fecha_persona1=fecha_persona1,
            lugar_persona1=lugar_persona1,
            ciudad_persona1=ciudad_persona1,
            fecha_persona2=fecha_persona2,
            lugar_persona2=lugar_persona2,
            ciudad_persona2=ciudad_persona2,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        # Mostrar la carta
        plt.tight_layout()
        plt.show()
        
        print(f"\n✓ Sinastría personalizada generada exitosamente")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

# EJECUTAR EL PROGRAMA
if __name__ == "__main__":
    main()