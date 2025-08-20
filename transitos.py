import os
import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
import swisseph as swe
import sqlite3

# Configuración de colores por elemento
COLORES_ELEMENTOS = {
    'fuego': '#FF6B6B',    # Rojo para Aries, Leo, Sagitario
    'tierra': '#4ECDC4',   # Verde para Tauro, Virgo, Capricornio
    'aire': '#FFE66D',     # Amarillo para Géminis, Libra, Acuario
    'agua': '#4D96FF'      # Azul para Cáncer, Escorpio, Piscis
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

COLORES_ASPECTOS = {
    'conjuncion': '#000000',        # Negro
    'semisextil': '#00FF00',        # Verde
    'sextil': '#00FF00',            # Verde
    'trigono': '#00FF00',           # Verde
    'semicuadratura': '#FF0000',    # Rojo
    'cuadratura': '#FF0000',        # Rojo
    'sesquicuadratura': '#8B4513',  # Marrón
    'oposicion': '#FF0000',         # Rojo
    'quincuncio': '#FFFF00',        # Amarillo
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

class CartaTransitos:
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
        self.ax.grid(True, alpha=0.3)
        
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
        radios = [0.1, 0.6, 0.75, 0.9, 1.0]
        for radio in radios:
            circle = plt.Circle((0, 0), radio, fill=False, color='black', 
                              linewidth=1.5, transform=self.ax.transData._b)
            self.ax.add_patch(circle)
    
    def dibujar_divisiones_casas(self, cuspides_casas, ascendente):
        """Dibujar las divisiones de las 12 casas"""
        for i, cuspide in enumerate(cuspides_casas):
            angle = self.grado_a_coordenada_carta(cuspide, ascendente)
            
            # Línea de división
            self.ax.plot([angle, angle], [0.1, 1.0], color='black', lw=2)
            
            # Centro de casa para número
            cuspide_siguiente = cuspides_casas[(i + 1) % 12]
            
            if cuspide_siguiente < cuspide:
                centro_casa = (cuspide + (cuspide_siguiente + 360 - cuspide) / 2) % 360
            else:
                centro_casa = (cuspide + cuspide_siguiente) / 2
            
            casa_angle = self.grado_a_coordenada_carta(centro_casa, ascendente)
            
            # Número de casa
            self.ax.text(casa_angle, 0.35, str(i + 1), 
                        ha='center', va='center', fontsize=10, 
                        weight='bold', color='darkblue')
    
    def dibujar_ascendente_mediocielo(self, ascendente, mediocielo):
        """Dibujar Ascendente y Mediocielo"""
        # ASCENDENTE: Siempre a la izquierda
        asc_angle = np.deg2rad(0)
        self.ax.plot([asc_angle, asc_angle], [0.1, 1.0], color='red', lw=4)
        
        signo_asc_idx = int(ascendente // 30)
        grado_asc = ascendente % 30
        self.ax.text(asc_angle, 1.35, f"ASC\n{NOMBRES_SIGNOS[signo_asc_idx][:3]} {grado_asc:.1f}°", 
                    ha='center', va='center', fontsize=9, 
                    weight='bold', color='red',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # MEDIOCIELO
        mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente)
        self.ax.plot([mc_angle, mc_angle], [0.1, 1.0], color='blue', lw=4)
        
        signo_mc_idx = int(mediocielo // 30)
        grado_mc = mediocielo % 30
        self.ax.text(mc_angle, 1.35, f"MC\n{NOMBRES_SIGNOS[signo_mc_idx][:3]} {grado_mc:.1f}°", 
                    ha='center', va='center', fontsize=9, 
                    weight='bold', color='blue',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
    
    def dibujar_signos_zodiacales(self, ascendente):
        """Dibujar signos zodiacales"""
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
                        color=color, alpha=0.2)
            
            # Símbolo del signo
            self.ax.text(angle_centro, 0.95, SIMBOLOS_SIGNOS[i], 
                        ha='center', va='center', fontsize=14, 
                        weight='bold', color='black')
    
    def dibujar_planetas_comparacion(self, pos_natales, pos_transitos, ascendente):
        """Dibujar planetas natales y en tránsito en círculos diferentes"""
        
        # Planetas natales en círculo interno (radio 0.68)
        for planeta, data in pos_natales.items():
            grado = data['grado']
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Símbolo natal (círculo interno)
            self.ax.text(rad, 0.68, simbolo, ha='center', va='center', 
                        fontsize=16, weight='bold', color=color)
            
            # Información natal (debajo del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 0.55, f"{signo[:3]}\n{grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=7, 
                        color='darkblue', weight='bold')
        
        # Planetas en tránsito en círculo externo (radio 0.82)
        for planeta, data in pos_transitos.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.grado_a_coordenada_carta(grado, ascendente)
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo tránsito (círculo externo)
            self.ax.text(rad, 0.82, simbolo, ha='center', va='center', 
                        fontsize=16, weight='bold', color=color)
            
            # Información tránsito (arriba del símbolo)
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            self.ax.text(rad, 1.12, f"{signo[:3]} {grado_en_signo:.1f}°", 
                        ha='center', va='center', fontsize=8, weight='bold',
                        color='darkred' if es_retrogrado else 'darkgreen',
                        bbox=dict(boxstyle="round,pad=0.2", 
                        facecolor='lightyellow' if es_retrogrado else 'lightgreen', 
                        alpha=0.8))
    
    def calcular_aspectos_transito(self, pos_natales, pos_transitos, ascendente, mediocielo):
        """Calcular aspectos entre planetas natales y en tránsito"""
        aspectos = []
        
        tolerancias = {
            'conjuncion': 8, 'oposicion': 8,
            'cuadratura': 7, 'trigono': 7,
            'sextil': 6,
            'semisextil': 3, 'quincuncio': 3,
            'semicuadratura': 3, 'sesquicuadratura': 3
        }
        
        angulos_aspectos = {
            'conjuncion': 0, 'semisextil': 30, 'sextil': 60,
            'cuadratura': 90, 'trigono': 120, 'quincuncio': 150,
            'oposicion': 180, 'semicuadratura': 45, 'sesquicuadratura': 135
        }
        
        # Aspectos: tránsitos a natales (planeta de tránsito aspectando planeta natal)
        for planeta_trans, data_trans in pos_transitos.items():
            for planeta_nat, data_nat in pos_natales.items():
                grado_trans = data_trans['grado']
                grado_nat = data_nat['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_trans - grado_nat)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'planeta_transito': planeta_trans,
                            'planeta_natal': planeta_nat,
                            'tipo': aspecto,
                            'orbe': orbe,
                            'grado_transito': grado_trans,
                            'grado_natal': grado_nat,
                            'diferencia_angular': diferencia
                        })
                        break
        
        # Aspectos: tránsitos a Ascendente y Mediocielo
        puntos_angulares = {
            'Ascendente': ascendente,
            'Mediocielo': mediocielo
        }

        for planeta_trans, data_trans in pos_transitos.items():
            for punto_angular, grado_angular in puntos_angulares.items():
                grado_trans = data_trans['grado']
                
                # Calcular diferencia angular
                diferencia = abs(grado_trans - grado_angular)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                # Verificar cada tipo de aspecto
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    orbe = abs(diferencia - angulo)
                    
                    if orbe <= tolerancia:
                        aspectos.append({
                            'planeta_transito': planeta_trans,
                            'planeta_natal': punto_angular,
                            'tipo': aspecto,
                            'orbe': orbe,
                            'grado_transito': grado_trans,
                            'grado_natal': grado_angular,
                            'diferencia_angular': diferencia
                        })
                        break
        
        return aspectos
    
    def dibujar_aspectos_transito(self, aspectos, pos_natales, pos_transitos, ascendente):
        """Dibujar líneas de aspectos entre planetas natales y en tránsito"""
        for aspecto in aspectos:
            planeta_trans = aspecto['planeta_transito']
            planeta_nat = aspecto['planeta_natal']
            
            grado_trans = aspecto['grado_transito']
            grado_nat = aspecto['grado_natal']
            
            rad_trans = self.grado_a_coordenada_carta(grado_trans, ascendente)
            rad_nat = self.grado_a_coordenada_carta(grado_nat, ascendente)
            
            color = COLORES_ASPECTOS.get(aspecto['tipo'], 'purple')
            
            # Línea de aspecto desde planeta de tránsito (radio 0.82) a planeta natal (radio 0.68)
            self.ax.plot([rad_trans, rad_nat], [0.82, 0.68], 
                        color=color, linewidth=2, alpha=0.7, linestyle='--')
            
            # Opcional: marcar el punto medio con el tipo de aspecto
            radio_medio = 0.75
            angulo_medio = (rad_trans + rad_nat) / 2
            
            # Ajustar si los ángulos están en lados opuestos del círculo
            if abs(rad_trans - rad_nat) > np.pi:
                angulo_medio = (rad_trans + rad_nat + 2*np.pi) / 2
                if angulo_medio > 2*np.pi:
                    angulo_medio -= 2*np.pi
            
            # Mostrar símbolo del aspecto en el punto medio
            simbolos_aspectos = {
                'conjuncion': '☌', 'oposicion': '☍', 'cuadratura': '□',
                'trigono': '△', 'sextil': '⚹', 'semisextil': '⚺',
                'quincuncio': '⚻', 'semicuadratura': '∠', 'sesquicuadratura': '∠'
            }
            
            simbolo_aspecto = simbolos_aspectos.get(aspecto['tipo'], '●')
            self.ax.text(angulo_medio, radio_medio, simbolo_aspecto, 
                        ha='center', va='center', fontsize=10, 
                        color=color, weight='bold',
                        bbox=dict(boxstyle="circle,pad=0.1", 
                        facecolor='white', alpha=0.8, edgecolor=color))
                        
    def obtener_info_lugar(self, latitud, longitud):
        """Obtener información del lugar basada en coordenadas usando la base de datos"""
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

    def crear_carta_transitos(self, fecha_nacimiento, fecha_transito, lugar_nacimiento, 
                                guardar_archivo=True, directorio_salida="static", nombre_archivo=None):
        """Crear la carta de tránsitos completa"""
        
        # Calcular posiciones natales
        año_nac, mes_nac, dia_nac, hora_nac, min_nac = fecha_nacimiento
        jd_natal = self.calcular_julian_day(año_nac, mes_nac, dia_nac, hora_nac, min_nac, aplicar_offset=True)
        pos_natales = self.obtener_posiciones_planetas(jd_natal)
        
        # Calcular posiciones en tránsito
        año_trans, mes_trans, dia_trans, hora_trans, min_trans = fecha_transito
        jd_transito = self.calcular_julian_day(año_trans, mes_trans, dia_trans, hora_trans, min_trans, aplicar_offset=True)
        pos_transitos = self.obtener_posiciones_planetas(jd_transito)
        
        # Usar casas natales como referencia
        latitud, longitud = lugar_nacimiento
        cuspides_casas, ascendente, mediocielo = self.calcular_casas_placidus(jd_natal, latitud, longitud)
        
        # Dibujar la carta
        self.dibujar_circulos_concentricos()
        self.dibujar_signos_zodiacales(ascendente)
        self.dibujar_divisiones_casas(cuspides_casas, ascendente)
        self.dibujar_ascendente_mediocielo(ascendente, mediocielo)
        self.dibujar_planetas_comparacion(pos_natales, pos_transitos, ascendente)
        
        # Calcular y dibujar aspectos
        aspectos = self.calcular_aspectos_transito(pos_natales, pos_transitos, ascendente, mediocielo)
        self.dibujar_aspectos_transito(aspectos, pos_natales, pos_transitos, ascendente)
        
        # Calcular edad
        fecha_nac_dt = datetime(año_nac, mes_nac, dia_nac, hora_nac, min_nac)
        fecha_trans_dt = datetime(año_trans, mes_trans, dia_trans, hora_trans, min_trans)
        edad = (fecha_trans_dt - fecha_nac_dt).days / 365.25
        
        # Información de la carta
        fecha_nac_str = f"{dia_nac:02d}/{mes_nac:02d}/{año_nac} {hora_nac:02d}:{min_nac:02d}"
        fecha_trans_str = f"{dia_trans:02d}/{mes_trans:02d}/{año_trans} {hora_trans:02d}:{min_trans:02d}"
        lugar_str = self.obtener_info_lugar(latitud, longitud)
        
        titulo = f"TRÁNSITOS\nNacimiento: {fecha_nac_str}\nTránsito: {fecha_trans_str} (Edad: {edad:.1f} años)\n{lugar_str}"
        
        self.fig.text(0.85, 0.95, titulo, 
                     fontsize=10, weight='bold', ha='center', va='top',
                     bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgreen', alpha=0.8))
        
        # Leyenda
        self.crear_leyenda_transitos()
        
        # Guardar archivo
        if guardar_archivo:
            self.guardar_transitos_con_nombre_unico(
                fecha_nacimiento, fecha_transito, directorio_salida
            )
        
        # Mostrar aspectos en consola
        print(f"\n=== ASPECTOS TRÁNSITO-NATAL ENCONTRADOS ({len(aspectos)}) ===")
        for aspecto in aspectos:
            print(f"• {aspecto['planeta_transito']} (T) {aspecto['tipo'].upper()} {aspecto['planeta_natal']} (N) - Orbe: {aspecto['orbe']:.2f}°")
        
        return aspectos, pos_natales, pos_transitos, fecha_trans_dt, edad
    
    def crear_leyenda_transitos(self):
        """Crear leyenda explicativa de los tránsitos"""
        leyenda_texto = [
            "LEYENDA:",
            "• Círculo interno: Planetas natales",
            "• Círculo externo: Planetas en tránsito",
            "• Líneas punteadas: Aspectos tránsito-natal",
            "• ℞ = Retrógrado",
            "• Símbolos en líneas = Tipo de aspecto"
        ]
        
        self.fig.text(0.02, 0.98, '\n'.join(leyenda_texto), 
                     fontsize=8, ha='left', va='top',
                     bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.9))

    def guardar_transitos_con_nombre_unico(self, fecha_nacimiento, fecha_transito, directorio_salida):
        """Guardar la carta con un nombre único"""
        
        # Crear directorio si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
            print(f"Directorio creado: {directorio_salida}")
        
        # Crear nombre base del archivo
        año_nac, mes_nac, dia_nac, hora_nac, min_nac = fecha_nacimiento
        año_trans, mes_trans, dia_trans, hora_trans, min_trans = fecha_transito
        
        # Si se proporciona nombre específico, usarlo
        if hasattr(self, 'nombre_archivo_personalizado') and self.nombre_archivo_personalizado:
            ruta_completa = self.nombre_archivo_personalizado
        else:
            nombre_base = f"transitos_{año_nac}{mes_nac:02d}{dia_nac:02d}_{hora_nac:02d}{min_nac:02d}_to_{año_trans}{mes_trans:02d}{dia_trans:02d}_{hora_trans:02d}{min_trans:02d}"
        
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
            print(f"✓ Carta de tránsitos guardada como: {ruta_completa}")
            return ruta_completa
        except Exception as e:
            print(f"✗ Error guardando la carta: {e}")
            return None

# FUNCIÓN MAIN CORREGIDA - FUERA DE LA CLASE
def main(nombre_archivo_salida=None):
    """Función principal para generar tránsitos"""
    print("=== GENERADOR DE TRÁNSITOS ===")
    print("Calculando tránsitos...")
    
    # Fecha de consulta (automática: día actual)
    hoy = datetime.now()
    fecha_transito = (hoy.year, hoy.month, hoy.day, hoy.hour, hoy.minute)
    print(f"Fecha actual detectada: {hoy.strftime('%d/%m/%Y %H:%M:%S')}")
    
    try:
        # Datos de nacimiento (ejemplo)
        fecha_nacimiento = (1985, 7, 23, 10, 45)  # año, mes, día, hora, minuto
        lugar_nacimiento = (40.42, -3.70)  # Madrid: latitud, longitud
        
        print(f"Fecha de nacimiento: {fecha_nacimiento[2]:02d}/{fecha_nacimiento[1]:02d}/{fecha_nacimiento[0]} {fecha_nacimiento[3]:02d}:{fecha_nacimiento[4]:02d}")
        print(f"Fecha de tránsito: {fecha_transito[2]:02d}/{fecha_transito[1]:02d}/{fecha_transito[0]} {fecha_transito[3]:02d}:{fecha_transito[4]:02d}")
        print(f"Lugar: Madrid (Lat: {lugar_nacimiento[0]:.2f}°, Lon: {lugar_nacimiento[1]:.2f}°)")
        
        # Crear instancia de la clase
        carta = CartaTransitos(figsize=(16, 14))
        
        # Generar la carta de tránsitos
        aspectos, pos_natales, pos_transitos, fecha_trans_dt, edad = carta.crear_carta_transitos(
            fecha_nacimiento=fecha_nacimiento,
            fecha_transito=fecha_transito,
            lugar_nacimiento=lugar_nacimiento,
            guardar_archivo=True,
            directorio_salida="static"
        )
        
        print("\n=== INFORMACIÓN DEL TRÁNSITO ===")
        print(f"Fecha de tránsito: {fecha_trans_dt.strftime('%d/%m/%Y %H:%M')}")
        print(f"Edad en fecha de tránsito: {edad:.2f} años")
        
        # Mostrar aspectos encontrados
        if aspectos:
            print(f"\n=== ASPECTOS ENCONTRADOS ({len(aspectos)}) ===")
            for aspecto in aspectos:
                orbe = aspecto['orbe']
                print(f"• {aspecto['planeta_transito']} {aspecto['tipo'].upper()} {aspecto['planeta_natal']} (orbe: {orbe:.2f}°)")
        else:
            print("\n=== NO SE ENCONTRARON ASPECTOS SIGNIFICATIVOS ===")
        
        # Mostrar movimientos planetarios más significativos
        print("\n=== MOVIMIENTOS PLANETARIOS MÁS SIGNIFICATIVOS ===")
        movimientos = []
        
        for planeta in pos_natales:
            grado_natal = pos_natales[planeta]['grado']
            grado_transito = pos_transitos[planeta]['grado']
            
            # Calcular diferencia
            diferencia = (grado_transito - grado_natal) % 360
            if diferencia > 180:
                diferencia = diferencia - 360
            
            movimientos.append({
                'planeta': planeta,
                'diferencia': abs(diferencia),
                'diferencia_real': diferencia,
                'retrogrado': pos_transitos[planeta].get('retrogrado', False)
            })
        
        # Ordenar por mayor movimiento
        movimientos.sort(key=lambda x: x['diferencia'], reverse=True)
        
        for mov in movimientos[:5]:  # Mostrar los 5 más significativos
            planeta = mov['planeta']
            diferencia = mov['diferencia_real']
            retrogrado_texto = " (R)" if mov['retrogrado'] else ""
            
            if abs(diferencia) > 1:
                print(f"• {planeta}: {diferencia:+.2f}° {retrogrado_texto}")
        
        print("\n✓ Tránsitos generados exitosamente")
        
    except Exception as e:
        print(f"✗ Error en la generación: {e}")
        import traceback
        traceback.print_exc()

# FUNCIÓN PARA GENERAR MÚLTIPLES FECHAS
def generar_transitos_multiples_fechas():
    """Generar tránsitos para múltiples fechas de consulta"""
    print("=== GENERADOR DE TRÁNSITOS MÚLTIPLES ===")
    
    # Datos de nacimiento
    fecha_nacimiento = (1985, 7, 23, 10, 45)
    lugar_nacimiento = (40.42, -3.70)  # Madrid
    
    # Fechas de consulta a generar
    fechas_transito = [
        (2024, 1, 1, 12, 0),   # Año nuevo 2024
        (2024, 6, 21, 12, 0),  # Solsticio de verano 2024
        (2024, 12, 21, 12, 0), # Solsticio de invierno 2024
        (2025, 1, 1, 12, 0),   # Año nuevo 2025
        (2025, 7, 5, 12, 0),   # Fecha actual
    ]
    
    for i, fecha_transito in enumerate(fechas_transito, 1):
        try:
            print(f"\n--- Generando tránsitos {i}/{len(fechas_transito)} ---")
            print(f"Fecha de tránsito: {fecha_transito[2]:02d}/{fecha_transito[1]:02d}/{fecha_transito[0]} {fecha_transito[3]:02d}:{fecha_transito[4]:02d}")
            
            # Crear nueva instancia para cada carta
            carta = CartaTransitos(figsize=(16, 14))
            
            # Generar la carta
            aspectos, pos_natales, pos_transitos, fecha_trans_dt, edad = carta.crear_carta_transitos(
                fecha_nacimiento=fecha_nacimiento,
                fecha_transito=fecha_transito,
                lugar_nacimiento=lugar_nacimiento,
                guardar_archivo=True,
                directorio_salida="transitos_multiples"
            )
            
            print(f"✓ Tránsito {i} completado - Aspectos encontrados: {len(aspectos)}")
            
            # Cerrar figura para liberar memoria
            plt.close()
            
        except Exception as e:
            print(f"✗ Error en tránsito {i}: {e}")
    
    print("\n✓ Todos los tránsitos generados exitosamente")

# FUNCIÓN PERSONALIZADA PARA DATOS ESPECÍFICOS
def generar_transitos_personalizada(nombre_archivo_salida=None):
    """Generar tránsitos con datos personalizados"""
    print("=== GENERADOR DE TRÁNSITOS PERSONALIZADO ===")
    
    # PERSONALIZAR ESTOS DATOS
    fecha_nacimiento = (1985, 7, 23, 10, 45)  # Año, mes, día, hora, minuto
    lugar_nacimiento = (40.42, -3.70)         # Madrid: latitud, longitud
    fecha_transito = (2025, 7, 5, 14, 0)      # Año, mes, día, hora, minuto de tránsito
    
    print("Datos configurados:")
    print(f"• Nacimiento: {fecha_nacimiento[2]:02d}/{fecha_nacimiento[1]:02d}/{fecha_nacimiento[0]} {fecha_nacimiento[3]:02d}:{fecha_nacimiento[4]:02d}")
    print(f"• Tránsito: {fecha_transito[2]:02d}/{fecha_transito[1]:02d}/{fecha_transito[0]} {fecha_transito[3]:02d}:{fecha_transito[4]:02d}")
    print(f"• Lugar: Madrid (Lat: {lugar_nacimiento[0]:.2f}°, Lon: {lugar_nacimiento[1]:.2f}°)")

    try:
        # Crear y generar la carta
        carta = CartaTransitos(figsize=(16, 14))

        print(f"🔧 DEBUG PRE-TRY:")
        print(f"   nombre_archivo_salida: {nombre_archivo_salida}")
        print(f"   carta.nombre_archivo_personalizado: {getattr(carta, 'nombre_archivo_personalizado', 'NO EXISTE')}")
        
        if nombre_archivo_salida:
            carta.nombre_archivo_personalizado = nombre_archivo_salida
        
        aspectos, pos_natales, pos_transitos, fecha_trans_dt, edad = carta.crear_carta_transitos(
            fecha_nacimiento=fecha_nacimiento,
            fecha_transito=fecha_transito,
            lugar_nacimiento=lugar_nacimiento,
            guardar_archivo=True,
            directorio_salida="transitos_personalizados"
        )
        
        print(f"\n✓ Tránsitos personalizados generados exitosamente")
        print(f"Aspectos encontrados: {len(aspectos)}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

# EJECUTAR EL PROGRAMA
if __name__ == "__main__":
    main()