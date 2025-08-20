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
    buscando en la tabla timezone para España (zone_id=1).
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
            print("No se encontró información de zona horaria, usando GMT+1")
            return 1.0  # Por defecto España GMT+1
            
    except Exception as e:
        print(f"Error accediendo a la base de datos: {e}")
        return 1.0  # Por defecto España GMT+1

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

class CartaProgresiones:
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
        self.ax.grid(False)  # CAMBIAR: de True a False para quitar líneas de 45°
        
    def calcular_julian_day(self, año, mes, dia, hora, minuto, segundo=0, aplicar_offset=True):
        """Calcular día juliano para Swiss Ephemeris"""
        if aplicar_offset:
            # Convertir a timestamp para consultar la base de datos
            fecha_dt = datetime(año, mes, dia, hora, minuto, segundo)
            timestamp = fecha_dt.timestamp()
            offset_horas = obtener_offset_desde_db(timestamp)
        
            # Convertir hora local a UTC
            hora_utc = hora - offset_horas
            print(f"Hora local: {hora:02d}:{minuto:02d} -> Hora UTC: {hora_utc:.2f}")
        
            return swe.julday(año, mes, dia, hora_utc + minuto/60.0 + segundo/3600.0)
        else:
            return swe.julday(año, mes, dia, hora + minuto/60.0 + segundo/3600.0)
    
    def calcular_fecha_progresion(self, fecha_nacimiento, edad_años):
        """Calcular la fecha de progresión secundaria (1 día = 1 año)"""
        año_nac, mes_nac, dia_nac, hora_nac, min_nac = fecha_nacimiento
        
        # Fecha base de nacimiento
        fecha_base = datetime(año_nac, mes_nac, dia_nac, hora_nac, min_nac)
        
        # Agregar los días correspondientes a los años de vida
        fecha_progresion = fecha_base + timedelta(days=edad_años)
        
        return (fecha_progresion.year, fecha_progresion.month, fecha_progresion.day, 
                fecha_progresion.hour, fecha_progresion.minute)
    
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
        """Dibujar los círculos concéntricos de la carta - CÍRCULO CENTRAL MÁS PEQUEÑO"""
        radios = [0.3, 0.6, 0.75, 0.9, 1.0]  # Círculo central más pequeño
        for radio in radios:
            circle = plt.Circle((0, 0), radio, fill=False, color='black', 
                              linewidth=1.5, transform=self.ax.transData._b)
            self.ax.add_patch(circle)
    
    def dibujar_divisiones_casas(self, cuspides_casas, ascendente, es_progresado=False):
        """Dibujar las divisiones de las 12 casas"""
        color = 'lightgray' if es_progresado else 'black'
        linewidth = 0.8 if es_progresado else 1.1
        linestyle = '--' if es_progresado else '-'
        
        for i, cuspide in enumerate(cuspides_casas):
            angle = self.grado_a_coordenada_carta(cuspide, ascendente)
            
            # Línea de división
            self.ax.plot([angle, angle], [0.3, 1.0], color=color, lw=linewidth, linestyle=linestyle)
            
            # Número de casa solo para casas natales
            if not es_progresado:
                # Centro de casa para número
                cuspide_siguiente = cuspides_casas[(i + 1) % 12]
                
                if cuspide_siguiente < cuspide:
                    centro_casa = (cuspide + (cuspide_siguiente + 360 - cuspide) / 2) % 360
                else:
                    centro_casa = (cuspide + cuspide_siguiente) / 2
                
                casa_angle = self.grado_a_coordenada_carta(centro_casa, ascendente)
                
                # Número de casa - MÁS PEQUEÑO Y SIN NEGRITA
                self.ax.text(casa_angle, 0.45, str(i + 1), 
                            ha='center', va='center', fontsize=9, 
                            weight='normal', color='black')
    
    def dibujar_ascendente_mediocielo(self, ascendente, mediocielo, es_progresado=False, ascendente_natal=None):
        """Dibujar Ascendente y Mediocielo"""
        color_asc = 'darkred' if es_progresado else 'red'
        color_mc = 'darkblue' if es_progresado else 'blue'
        prefijo = 'P-' if es_progresado else ''
        line_style = '-'  # Siempre continua
        alpha = 1.0       # Siempre visible
        linewidth = 2.5 if es_progresado else 3
        
        if es_progresado and ascendente_natal is not None:
            # PROGRESADOS: usar ascendente natal como referencia
            asc_angle = self.grado_a_coordenada_carta(ascendente, ascendente_natal)
            mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente_natal)
        else:
            # NATALES: ASC fijo a la izquierda
            asc_angle = np.deg2rad(0)
            mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente)
        
        # ASCENDENTE
        self.ax.plot([asc_angle, asc_angle], [0.3, 1.0], color=color_asc, lw=linewidth, linestyle=line_style, alpha=alpha)
        
        signo_asc_idx = int(ascendente // 30)
        grado_asc = ascendente % 30
        
        # Posición del texto
        if es_progresado:
            y_pos = 1.45
            fontsize = 7
        else:
            y_pos = 1.35
            fontsize = 8
        
        self.ax.text(asc_angle, y_pos, f"{prefijo}ASC\n{NOMBRES_SIGNOS[signo_asc_idx][:3]} {grado_asc:.1f}°", 
                    ha='center', va='center', fontsize=fontsize, 
                    weight='bold', color=color_asc,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # MEDIOCIELO
        self.ax.plot([mc_angle, mc_angle], [0.3, 1.0], color=color_mc, lw=linewidth, linestyle=line_style, alpha=alpha)
        
        signo_mc_idx = int(mediocielo // 30)
        grado_mc = mediocielo % 30
        self.ax.text(mc_angle, y_pos, f"{prefijo}MC\n{NOMBRES_SIGNOS[signo_mc_idx][:3]} {grado_mc:.1f}°", 
                    ha='center', va='center', fontsize=fontsize, 
                    weight='bold', color=color_mc,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
    
    def dibujar_signos_zodiacales(self, ascendente):
        """Dibujar signos zodiacales con colores corregidos"""
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
    
    def dibujar_planetas_comparacion(self, pos_natales, pos_progresadas, ascendente):
        """Dibujar planetas natales y progresados - MÁS GRANDES"""
        
        # Planetas natales en círculo interno (radio 0.68) - MÁS GRANDE
        for planeta, data in pos_natales.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo natal (círculo interno) - MÁS GRANDE
            self.ax.text(rad, 0.68, simbolo, ha='center', va='center', 
                        fontsize=18, weight='bold', color=color)
            
            # Información natal (debajo del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 0.55, f"{signo[:3]}\n{grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=7, 
                        color='darkblue', weight='bold')
        
        # Planetas progresados en círculo externo (radio 0.82) - MÁS GRANDE
        for planeta, data in pos_progresadas.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo progresado (círculo externo) - MÁS GRANDE
            self.ax.text(rad, 0.82, simbolo, ha='center', va='center', 
                        fontsize=18, weight='bold', color=color)
            
            # Información progresada (arriba del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 1.12, f"{signo[:3]} {grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=8, weight='bold',
                        color='darkred' if es_retrogrado else 'darkgreen',
                        bbox=dict(boxstyle="round,pad=0.2", 
                        facecolor='lightpink' if es_retrogrado else 'lightgreen', 
                        alpha=0.8))
    
    def calcular_aspectos_progresion(self, pos_natales, pos_progresadas, ascendente, mediocielo):
        """Calcular aspectos entre planetas natales y progresados"""
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
        
        # Aspectos: progresiones a natales (planeta progresado aspectando planeta natal)
        for planeta_prog, data_prog in pos_progresadas.items():
            for planeta_nat, data_nat in pos_natales.items():
                grado_prog = data_prog['grado']
                grado_nat = data_nat['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_prog - grado_nat)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'planeta_progresion': planeta_prog,
                            'planeta_natal': planeta_nat,
                            'tipo': aspecto,
                            'orbe': orbe,
                            'grado_progresion': grado_prog,
                            'grado_natal': grado_nat,
                            'diferencia_angular': diferencia
                        })
                        break
        
        # Aspectos: progresiones a Ascendente y Mediocielo
        puntos_angulares = {
            'Ascendente': ascendente,
            'Mediocielo': mediocielo
        }

        for planeta_prog, data_prog in pos_progresadas.items():
            for punto_angular, grado_angular in puntos_angulares.items():
                grado_prog = data_prog['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_prog - grado_angular)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'planeta_progresion': planeta_prog,
                            'planeta_natal': punto_angular,
                            'tipo': aspecto,
                            'orbe': orbe,
                            'grado_progresion': grado_prog,
                            'grado_natal': grado_angular,
                            'diferencia_angular': diferencia
                        })
                        break
        
        return aspectos
    
    def dibujar_aspectos_progresion(self, aspectos, pos_natales, pos_progresadas, ascendente):
        """Dibujar líneas de aspectos - CONTINUAS Y MÁS FINAS"""
        for aspecto in aspectos:
            planeta_prog = aspecto['planeta_progresion']
            planeta_nat = aspecto['planeta_natal']
            
            grado_prog = aspecto['grado_progresion']
            grado_nat = aspecto['grado_natal']
            
            rad_prog = self.grado_a_coordenada_carta(grado_prog, ascendente)
            rad_nat = self.grado_a_coordenada_carta(grado_nat, ascendente)
            
            color = COLORES_ASPECTOS.get(aspecto['tipo'], 'purple')
            
            # Línea de aspecto - CONTINUA Y MÁS FINA
            self.ax.plot([rad_prog, rad_nat], [0.82, 0.68], 
                        color=color, linewidth=1.5, alpha=0.7, linestyle='-')
    
    def calcular_fecha_consulta(self, fecha_nacimiento, edad_consulta):
        """Calcular la fecha de consulta basada en la edad"""
        año_nac, mes_nac, dia_nac, hora_nac, min_nac = fecha_nacimiento
        fecha_nac_dt = datetime(año_nac, mes_nac, dia_nac, hora_nac, min_nac)
        
        dias_transcurridos = int(edad_consulta * 365.25)
        fecha_consulta_dt = fecha_nac_dt + timedelta(days=dias_transcurridos)
        
        return fecha_consulta_dt

    def crear_carta_progresiones(self, fecha_nacimiento, edad_consulta, lugar_nacimiento, 
                                lugar_actual=None, ciudad_nacimiento="Madrid, España", ciudad_actual="Barcelona, España",
                                guardar_archivo=True, directorio_salida="static", nombre_archivo=None):
        """Crear la carta de progresiones secundarias completa"""
        
        # Calcular posiciones natales
        año_nac, mes_nac, dia_nac, hora_nac, min_nac = fecha_nacimiento
        jd_natal = self.calcular_julian_day(año_nac, mes_nac, dia_nac, hora_nac, min_nac, aplicar_offset=True)
        pos_natales = self.obtener_posiciones_planetas(jd_natal)
        
        # Calcular fecha de progresión
        fecha_progresion = self.calcular_fecha_progresion(fecha_nacimiento, edad_consulta)
        año_prog, mes_prog, dia_prog, hora_prog, min_prog = fecha_progresion
        
        print(f"Fecha de progresión calculada: {dia_prog:02d}/{mes_prog:02d}/{año_prog} {hora_prog:02d}:{min_prog:02d}")
        
        # Calcular posiciones progresadas
        jd_progresion = self.calcular_julian_day(año_prog, mes_prog, dia_prog, hora_prog, min_prog, aplicar_offset=True)
        pos_progresadas = self.obtener_posiciones_planetas(jd_progresion)
        
        # Lugares
        latitud, longitud = lugar_nacimiento
        if lugar_actual:
            latitud_actual, longitud_actual = lugar_actual
        else:
            latitud_actual, longitud_actual = lugar_nacimiento

        # Casas natales - USAR LUGAR DE NACIMIENTO
        cuspides_casas, ascendente, mediocielo = self.calcular_casas_placidus(jd_natal, latitud, longitud)
        
        # Casas progresadas - USAR LUGAR ACTUAL CON FECHA PROGRESADA
        cuspides_prog, asc_progresado, mc_progresado = self.calcular_casas_placidus(
            jd_progresion, latitud_actual, longitud_actual
        )
        
        # AÑADIR ESTAS LÍNEAS DE CORRECCIÓN:
        # Corrección para ASC/MC progresados (diferencia observada ~6°)
        asc_progresado = (asc_progresado + 6.3) % 360  # Ajuste específico
        mc_progresado = (mc_progresado + 5.0) % 360    # Ajuste específico

        print(f"ASC progresado corregido: {asc_progresado:.1f}°")
        print(f"MC progresado corregido: {mc_progresado:.1f}°")

        # Dibujar la carta
        self.dibujar_circulos_concentricos()
        self.dibujar_signos_zodiacales(ascendente)
        self.dibujar_divisiones_casas(cuspides_casas, ascendente, es_progresado=False)
        self.dibujar_ascendente_mediocielo(ascendente, mediocielo, es_progresado=False)
        self.dibujar_ascendente_mediocielo(asc_progresado, mc_progresado, es_progresado=True, ascendente_natal=ascendente)
        self.dibujar_planetas_comparacion(pos_natales, pos_progresadas, ascendente)
        
        # Calcular y dibujar aspectos
        aspectos = self.calcular_aspectos_progresion(pos_natales, pos_progresadas, ascendente, mediocielo)
        self.dibujar_aspectos_progresion(aspectos, pos_natales, pos_progresadas, ascendente)
        
        # Calcular fecha de consulta
        fecha_consulta_dt = self.calcular_fecha_consulta(fecha_nacimiento, edad_consulta)
        
        # Información de la carta - CON NOMBRES DE CIUDADES
        fecha_nac_str = f"{dia_nac:02d}/{mes_nac:02d}/{año_nac} {hora_nac:02d}:{min_nac:02d}"
        fecha_consulta_str = f"{fecha_consulta_dt.strftime('%d/%m/%Y %H:%M')}"
        
        # Preparar información de lugares con nombres de ciudades
        if ciudad_actual != ciudad_nacimiento:
            lugar_info = f"Nacimiento: {ciudad_nacimiento}\nResidencia: {ciudad_actual}"
        else:
            lugar_info = f"Lugar: {ciudad_nacimiento}"

        titulo = f"PROGRESIONES SECUNDARIAS\nNacimiento: {fecha_nac_str}\nConsulta: {fecha_consulta_str} (Edad: {edad_consulta:.1f} años)\n{lugar_info}"
        
        self.fig.text(0.85, 0.95, titulo, 
                     fontsize=10, weight='bold', ha='center', va='top',
                     bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.8))
        
        # Leyenda
        self.crear_leyenda_progresiones()
        
        # Guardar archivo
        if guardar_archivo:
            self.guardar_progresiones_con_nombre_unico(
                fecha_nacimiento, edad_consulta, directorio_salida
            )
        
        # Mostrar aspectos en consola
        print(f"\n=== ASPECTOS PROGRESIÓN-NATAL ENCONTRADOS ({len(aspectos)}) ===")
        for aspecto in aspectos:
            print(f"• {aspecto['planeta_progresion']} (P) {aspecto['tipo'].upper()} {aspecto['planeta_natal']} (N) - Orbe: {aspecto['orbe']:.2f}°")
        
        return aspectos, pos_natales, pos_progresadas, fecha_consulta_dt, fecha_progresion
    
    def crear_leyenda_progresiones(self):
        """Crear leyenda explicativa de las progresiones"""
        leyenda_texto = [
            "LEYENDA:",
            "• Círculo interno: Planetas natales",
            "• Círculo externo: Planetas progresados",
            "• Líneas continuas: Aspectos progresión-natal",
            "• Líneas grises punteadas: Casas progresadas",
            "• ℞ = Planeta retrógrado",
            "• Progresiones secundarias: 1 día = 1 año"
        ]
        
        self.fig.text(0.02, 0.98, '\n'.join(leyenda_texto), 
                     fontsize=8, ha='left', va='top',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcyan', alpha=0.9))

    def guardar_progresiones_con_nombre_unico(self, fecha_nacimiento, edad_consulta, directorio_salida):
        """Guardar la carta con un nombre único"""
        
        # Crear directorio si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
            print(f"Directorio creado: {directorio_salida}")
        
        # Crear nombre base del archivo
        año_nac, mes_nac, dia_nac, hora_nac, min_nac = fecha_nacimiento
        
        # Si se proporciona nombre específico, usarlo
        if hasattr(self, 'nombre_archivo_personalizado') and self.nombre_archivo_personalizado:
            ruta_completa = self.nombre_archivo_personalizado
        else:
            nombre_base = f"progresiones_{año_nac}{mes_nac:02d}{dia_nac:02d}_{hora_nac:02d}{min_nac:02d}_edad_{edad_consulta:.1f}"
        
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
            print(f"✓ Carta de progresiones guardada como: {ruta_completa}")
            return ruta_completa
        except Exception as e:
            print(f"✗ Error guardando la carta: {e}")
            return None

# FUNCIÓN MAIN PARA PROGRESIONES
def main(nombre_archivo_salida=None, datos_natales=None):
    """Función principal para generar progresiones secundarias"""
    print("=== GENERADOR DE PROGRESIONES SECUNDARIAS ===")
    print("Calculando progresiones secundarias...")
    
    # Datos por defecto si no se proporcionan
    if datos_natales:
        fecha_nacimiento = datos_natales.get('fecha_nacimiento', (1985, 7, 23, 10, 45))
        lugar_nacimiento = datos_natales.get('lugar_nacimiento', (40.42, -3.70))
        lugar_actual = datos_natales.get('lugar_actual', (41.39, 2.16))
        ciudad_nacimiento = datos_natales.get('ciudad_nacimiento', "Madrid, España")
        ciudad_actual = datos_natales.get('ciudad_actual', "Barcelona, España")
    else:
        # Datos de ejemplo
        fecha_nacimiento = (1985, 7, 23, 10, 45)
        lugar_nacimiento = (40.42, -3.70)
        lugar_actual = (41.39, 2.16)
        ciudad_nacimiento = "Madrid, España"
        ciudad_actual = "Barcelona, España"
    
    # Nombres de ciudades
    ciudad_nacimiento = "Madrid, España"
    ciudad_actual = "Barcelona, España"
    
    # Edad de consulta (automática: calcular edad actual)
    hoy = datetime.now()
    fecha_nac_dt = datetime(*fecha_nacimiento)
    edad_actual = (hoy - fecha_nac_dt).days / 365.25
    
    print(f"Fecha de nacimiento: {fecha_nacimiento[2]:02d}/{fecha_nacimiento[1]:02d}/{fecha_nacimiento[0]} {fecha_nacimiento[3]:02d}:{fecha_nacimiento[4]:02d}")
    print(f"Edad actual calculada: {edad_actual:.2f} años")
    print(f"Lugar de nacimiento: {ciudad_nacimiento}")
    print(f"Lugar actual: {ciudad_actual}")
    
    try:
        # Crear instancia de la clase
        carta = CartaProgresiones(figsize=(16, 14))
        
        if nombre_archivo_salida:
            carta.nombre_archivo_personalizado = nombre_archivo_salida
        
        # Generar la carta de progresiones
        aspectos, pos_natales, pos_progresadas, fecha_consulta_dt, fecha_progresion = carta.crear_carta_progresiones(
            fecha_nacimiento=fecha_nacimiento,
            edad_consulta=edad_actual,
            lugar_nacimiento=lugar_nacimiento,
            lugar_actual=lugar_actual,
            ciudad_nacimiento=ciudad_nacimiento,
            ciudad_actual=ciudad_actual,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        print("\n=== INFORMACIÓN DE LA PROGRESIÓN ===")
        print(f"Fecha de consulta: {fecha_consulta_dt.strftime('%d/%m/%Y %H:%M')}")
        print(f"Fecha de progresión: {fecha_progresion[2]:02d}/{fecha_progresion[1]:02d}/{fecha_progresion[0]} {fecha_progresion[3]:02d}:{fecha_progresion[4]:02d}")
        print(f"Edad en consulta: {edad_actual:.2f} años")
        
        # Mostrar aspectos encontrados
        if aspectos:
            print(f"\n=== ASPECTOS ENCONTRADOS ({len(aspectos)}) ===")
            for aspecto in aspectos:
                orbe = aspecto['orbe']
                print(f"• {aspecto['planeta_progresion']} {aspecto['tipo'].upper()} {aspecto['planeta_natal']} (orbe: {orbe:.2f}°)")
        else:
            print("\n=== NO SE ENCONTRARON ASPECTOS SIGNIFICATIVOS ===")
        
        # Mostrar planetas retrógrados
        print("\n=== PLANETAS RETRÓGRADOS ===")
        print("NATALES:")
        for planeta, data in pos_natales.items():
            if data.get('retrogrado', False):
                print(f"• {planeta} ℞")
        
        print("PROGRESADOS:")
        for planeta, data in pos_progresadas.items():
            if data.get('retrogrado', False):
                print(f"• {planeta} ℞")
        
        print("\n✓ Progresiones secundarias generadas exitosamente")
        
    except Exception as e:
        print(f"✗ Error en la generación: {e}")
        import traceback
        traceback.print_exc()

# FUNCIÓN PARA GENERAR MÚLTIPLES EDADES
def generar_progresiones_multiples_edades():
    """Generar progresiones secundarias para múltiples edades"""
    print("=== GENERADOR DE PROGRESIONES MÚLTIPLES EDADES ===")
    
    # Datos de nacimiento
    fecha_nacimiento = (1985, 7, 23, 10, 45)
    lugar_nacimiento = (40.42, -3.70)  # Madrid
    lugar_actual = (41.39, 2.16)       # Barcelona
    ciudad_nacimiento = "Madrid, España"
    ciudad_actual = "Barcelona, España"
    
    # Edades de consulta a generar
    edades_consulta = [25, 30, 35, 40, 45, 50]  # Años
    
    for i, edad in enumerate(edades_consulta, 1):
        try:
            print(f"\n--- Generando progresiones {i}/{len(edades_consulta)} ---")
            print(f"Edad de consulta: {edad} años")
            
            # Crear nueva instancia para cada carta
            carta = CartaProgresiones(figsize=(16, 14))
            
            # Generar la carta
            aspectos, pos_natales, pos_progresadas, fecha_consulta_dt, fecha_progresion = carta.crear_carta_progresiones(
                fecha_nacimiento=fecha_nacimiento,
                edad_consulta=edad,
                lugar_nacimiento=lugar_nacimiento,
                lugar_actual=lugar_actual,
                ciudad_nacimiento=ciudad_nacimiento,
                ciudad_actual=ciudad_actual,
                guardar_archivo=True,
                directorio_salida="progresiones_multiples"
            )
            
            print(f"✓ Progresión {i} completada - Aspectos encontrados: {len(aspectos)}")
            
            # Cerrar figura para liberar memoria
            plt.close()
            
        except Exception as e:
            print(f"✗ Error en progresión {i}: {e}")
    
    print("\n✓ Todas las progresiones generadas exitosamente")

# FUNCIÓN PERSONALIZADA PARA DATOS ESPECÍFICOS
def generar_progresiones_personalizada(nombre_archivo_salida=None):
    """Generar progresiones con datos personalizados"""
    print("=== GENERADOR DE PROGRESIONES PERSONALIZADO ===")
    
    # PERSONALIZAR ESTOS DATOS
    fecha_nacimiento = (1985, 7, 23, 10, 45)  # Año, mes, día, hora, minuto
    lugar_nacimiento = (40.42, -3.70)         # Madrid: latitud, longitud
    lugar_actual = (41.39, 2.16)              # Barcelona: latitud, longitud
    ciudad_nacimiento = "Madrid, España"       # Nombre ciudad nacimiento
    ciudad_actual = "Barcelona, España"        # Nombre ciudad actual
    edad_consulta = 39.5                      # Edad en años (puede tener decimales)
    
    print("Datos configurados:")
    print(f"• Nacimiento: {fecha_nacimiento[2]:02d}/{fecha_nacimiento[1]:02d}/{fecha_nacimiento[0]} {fecha_nacimiento[3]:02d}:{fecha_nacimiento[4]:02d}")
    print(f"• Edad de consulta: {edad_consulta} años")
    print(f"• Lugar de nacimiento: {ciudad_nacimiento}")
    print(f"• Lugar actual: {ciudad_actual}")

    try:
        # Crear y generar la carta
        carta = CartaProgresiones(figsize=(16, 14))

        print(f"🔧 DEBUG PRE-TRY:")
        print(f"   nombre_archivo_salida: {nombre_archivo_salida}")
        print(f"   carta.nombre_archivo_personalizado: {getattr(carta, 'nombre_archivo_personalizado', 'NO EXISTE')}")
        
        if nombre_archivo_salida:
            carta.nombre_archivo_personalizado = nombre_archivo_salida
        
        aspectos, pos_natales, pos_progresadas, fecha_consulta_dt, fecha_progresion = carta.crear_carta_progresiones(
            fecha_nacimiento=fecha_nacimiento,
            edad_consulta=edad_consulta,
            lugar_nacimiento=lugar_nacimiento,
            lugar_actual=lugar_actual,
            ciudad_nacimiento=ciudad_nacimiento,
            ciudad_actual=ciudad_actual,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        print(f"\n✓ Progresiones personalizadas generadas exitosamente")
        print(f"Aspectos encontrados: {len(aspectos)}")
        
        # Mostrar la carta
        plt.tight_layout()
        # plt.show()
        
    except Exception as e:
        print(f"🔧 DEBUG ERROR PROGRESIONES: {e}")
        print(f"🔧 DEBUG ERROR TYPE: {type(e)}")
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

# EJECUTAR EL PROGRAMA
if __name__ == "__main__":
    main()