import os
import json
from datetime import datetime, timezone
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

def decimal_a_sexagesimal(grado_decimal):
    """Convertir grado decimal a formato sexagesimal (grados, minutos, segundos)"""
    grados = int(grado_decimal)
    minutos_decimal = (grado_decimal - grados) * 60
    minutos = int(minutos_decimal)
    segundos = (minutos_decimal - minutos) * 60
    
    return grados, minutos, segundos

def formato_sexagesimal(grado_decimal):
    """Formatear grado decimal como string sexagesimal"""
    grados, minutos, segundos = decimal_a_sexagesimal(grado_decimal)
    return f"{grados}°{minutos:02d}'{segundos:04.1f}\""

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

class CartaAstralSwissEph:
    def __init__(self, figsize=(12, 12)):
        self.fig = plt.figure(figsize=figsize, facecolor='white')
        self.ax = self.fig.add_subplot(111, polar=True)
        self.configurar_ejes()
        
    def configurar_ejes(self):
        """Configurar los ejes polares - Ascendente fijo a la izquierda"""
        self.ax.set_theta_direction(1)      # Sentido antihorario
        self.ax.set_theta_offset(np.pi)     # 0° a la izquierda (Ascendente)
        self.ax.set_ylim(0, 1.4)
        self.ax.set_yticklabels([])
        self.ax.grid(True, alpha=0.3)
        
    def calcular_julian_day(self, año, mes, dia, hora, minuto, segundo=0):
        """Calcular día juliano para Swiss Ephemeris"""
        return swe.julday(año, mes, dia, hora + minuto/60.0 + segundo/3600.0)
    
   # Modificación en la función obtener_posiciones_planetas
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
        radios = [0.1, 0.7, 0.9, 1.0]
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
            self.ax.text(casa_angle, 0.4, str(i + 1), 
                        ha='center', va='center', fontsize=12, 
                        weight='bold', color='darkblue')
            
            # CORRECCIÓN: Solo mostrar info de cúspide si NO es el Ascendente
            if i != 0:  # Casa 1 es el Ascendente, no mostrar info duplicada
                signo_idx = int(cuspide // 30)
                grado_en_signo = cuspide % 30
                texto_cuspide = f"{NOMBRES_SIGNOS[signo_idx][:3]} {grado_en_signo:.0f}°"
                
                self.ax.text(angle, 1.02, texto_cuspide,
                            ha='center', va='center', fontsize=7, 
                            color='darkred', weight='bold')
    
    def dibujar_ascendente_mediocielo(self, ascendente, mediocielo):
        """Dibujar Ascendente y Mediocielo"""
        # ASCENDENTE: Siempre a la izquierda
        asc_angle = np.deg2rad(0)
        self.ax.plot([asc_angle, asc_angle], [0.1, 1.0], color='red', lw=4)
        
        signo_asc_idx = int(ascendente // 30)
        grado_asc = ascendente % 30
        self.ax.text(asc_angle, 1.25, f"ASC\n{NOMBRES_SIGNOS[signo_asc_idx][:3]} {formato_sexagesimal(grado_asc)}", 
                    ha='center', va='center', fontsize=10, 
                    weight='bold', color='red',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # MEDIOCIELO
        mc_angle = self.grado_a_coordenada_carta(mediocielo, ascendente)
        self.ax.plot([mc_angle, mc_angle], [0.1, 1.0], color='blue', lw=4)
        
        signo_mc_idx = int(mediocielo // 30)
        grado_mc = mediocielo % 30
        self.ax.text(mc_angle, 1.25, f"MC\n{NOMBRES_SIGNOS[signo_mc_idx][:3]} {formato_sexagesimal(grado_mc)}", 
                    ha='center', va='center', fontsize=10, 
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
                        color=color, alpha=0.3)
            
            # Símbolo del signo
            self.ax.text(angle_centro, 0.95, SIMBOLOS_SIGNOS[i], 
                        ha='center', va='center', fontsize=16, 
                        weight='bold', color='black')
    
    def calcular_posicion_planeta(self, grado, ascendente):
        """Convertir grado zodiacal a coordenadas de carta"""
        return self.grado_a_coordenada_carta(grado, ascendente)
    
    def evitar_solapamiento_textos(self, posiciones_planetas, ascendente):
        """Calcular posiciones de texto evitando solapamientos - MEJORADO"""
        planetas_info = []
        
        for planeta, data in posiciones_planetas.items():
            grado = data['grado']
            rad = self.calcular_posicion_planeta(grado, ascendente)
            planetas_info.append({
                'planeta': planeta,
                'angulo': rad,
                'grado': grado,
                'angulo_grados': np.rad2deg(rad) % 360
            })
        
        planetas_info.sort(key=lambda x: x['angulo_grados'])
        
        posiciones_finales = {}
        radio_base = 1.12
        separacion_angular = 25  # Aumentado para evitar solapamientos
        
        for i, info in enumerate(planetas_info):
            angulo_actual = info['angulo_grados']
            
            # Algoritmo mejorado para evitar solapamientos
            nivel_radio = 0
            for j in range(i):
                angulo_anterior = planetas_info[j]['angulo_grados']
                diferencia = min(abs(angulo_actual - angulo_anterior), 
                               360 - abs(angulo_actual - angulo_anterior))
                
                if diferencia < separacion_angular:
                    nivel_radio = max(nivel_radio, 
                                    posiciones_finales[planetas_info[j]['planeta']]['nivel'] + 1)
            
            radio = radio_base + 0.08 * nivel_radio
            
            posiciones_finales[info['planeta']] = {
                'angulo': info['angulo'],
                'radio': radio,
                'grado': info['grado'],
                'nivel': nivel_radio
            }
        
        return posiciones_finales
    
    # Modificación en la función dibujar_planetas para mostrar símbolo retrógrado
    def dibujar_planetas(self, posiciones_planetas, ascendente):
        """Dibujar planetas - CON INDICACIÓN DE RETRÓGRADOS"""
        posiciones_texto = self.evitar_solapamiento_textos(posiciones_planetas, ascendente)
        
        radios_planetas = np.linspace(0.72, 0.88, len(posiciones_planetas))
        
        for i, (planeta, data) in enumerate(posiciones_planetas.items()):
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            rad = self.calcular_posicion_planeta(grado, ascendente)
            radio_planeta = radios_planetas[i]
            
            color = COLORES_PLANETAS.get(planeta, 'black')
            simbolo = SIMBOLOS_PLANETAS.get(planeta, planeta[0])
            
            # Añadir ℞ si está retrógrado
            if es_retrogrado:
                simbolo += "℞"
            
            # Símbolo del planeta
            self.ax.text(rad, radio_planeta, simbolo, ha='center', va='center', 
                        fontsize=18, weight='bold', color=color)
            
            # Información del planeta
            pos_info = posiciones_texto[planeta]
            grado_en_signo = grado % 30
            signo_idx = int(grado // 30)
            signo = NOMBRES_SIGNOS[signo_idx]
            
            # Texto con indicación de retrógrado
            texto = f"{planeta}"
            if es_retrogrado:
                texto += " ℞"
            texto += f"\n{signo[:3]} {formato_sexagesimal(grado_en_signo)}"
            
            self.ax.text(pos_info['angulo'], pos_info['radio'], texto, 
                        ha='center', va='center', fontsize=8, weight='bold',
                        bbox=dict(boxstyle="round,pad=0.2", 
                        facecolor='lightpink' if es_retrogrado else 'white', 
                        alpha=0.7, edgecolor='gray'))
    
    def calcular_aspectos(self, posiciones_planetas, ascendente=None, mediocielo=None):
        """Calcular aspectos entre planetas"""
        aspectos = []
        planetas = list(posiciones_planetas.keys())
        # Añadir Ascendente y Mediocielo si se proporcionan
        puntos_importantes = {}
        if ascendente is not None:
            puntos_importantes['Ascendente'] = ascendente
        if mediocielo is not None:
            puntos_importantes['Mediocielo'] = mediocielo
        tolerancias = {
            'conjuncion': 8, 'oposicion': 8,
            'cuadratura': 7, 'trigono': 7,
            'sextil': 6,
            'semisextil': 2.5, 'quincuncio': 2.5,
            'semicuadratura': 2.5, 'sesquicuadratura': 2.5,
            'quintil': 2.5, 'biquintil': 2.5
        }
        
        angulos_aspectos = {
            'conjuncion': 0, 'semisextil': 30, 'sextil': 60,
            'cuadratura': 90, 'trigono': 120, 'quincuncio': 150,
            'oposicion': 180, 'semicuadratura': 45, 'sesquicuadratura': 135,
            'quintil': 72, 'biquintil': 144
        }
        
        for i in range(len(planetas)):
            for j in range(i + 1, len(planetas)):
                planeta1 = planetas[i]
                planeta2 = planetas[j]
                grado1 = posiciones_planetas[planeta1]['grado']
                grado2 = posiciones_planetas[planeta2]['grado']
                
                diferencia = abs(grado1 - grado2)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    if abs(diferencia - angulo) <= tolerancia:
                        aspectos.append({
                            'planeta1': planeta1,
                            'planeta2': planeta2,
                            'tipo': aspecto,
                            'orbe': abs(diferencia - angulo)
                        })
                        break
            # Calcular aspectos entre planetas y puntos importantes (ASC/MC)
        for planeta in planetas:
            for punto, grado_punto in puntos_importantes.items():
                grado_planeta = posiciones_planetas[planeta]['grado']
                
                diferencia = abs(grado_planeta - grado_punto)
                if diferencia > 180:
                    diferencia = 360 - diferencia
                
                for aspecto, angulo in angulos_aspectos.items():
                    tolerancia = tolerancias[aspecto]
                    if abs(diferencia - angulo) <= tolerancia:
                        aspectos.append({
                            'planeta1': planeta,
                            'planeta2': punto,
                            'tipo': aspecto,
                            'orbe': abs(diferencia - angulo)
                        })
                        break
                        
        return aspectos
    
    def dibujar_aspectos(self, aspectos, posiciones_planetas, ascendente, mediocielo=None):
        """Dibujar líneas de aspectos"""
        # Crear diccionario con todas las posiciones (planetas + puntos importantes)
        todas_posiciones = {}
        for planeta, data in posiciones_planetas.items():
            todas_posiciones[planeta] = data['grado']
        todas_posiciones['Ascendente'] = ascendente
        if mediocielo is not None:
            todas_posiciones['Mediocielo'] = mediocielo
    
        for aspecto in aspectos:
            planeta1 = aspecto['planeta1']
            planeta2 = aspecto['planeta2']
            tipo = aspecto['tipo']
            
            grado1 = todas_posiciones[planeta1]
            grado2 = todas_posiciones[planeta2]
            
            rad1 = self.calcular_posicion_planeta(grado1, ascendente)
            rad2 = self.calcular_posicion_planeta(grado2, ascendente)
            
            color = COLORES_ASPECTOS.get(tipo, 'gray')
            
            self.ax.plot([rad1, rad2], [0.65, 0.65], color=color, 
                        linewidth=1.5, alpha=0.7)
    
    def obtener_info_lugar(self, latitud, longitud):
        """Obtener información del lugar"""
        lugares_conocidos = {
            (41.39, 2.16): "Barcelona, España",
            (40.42, -3.70): "Madrid, España",
            (25.76, -80.19): "Miami, Estados Unidos",
            (40.71, -74.01): "Nueva York, Estados Unidos",
            (48.86, 2.35): "París, Francia",
            (51.51, -0.13): "Londres, Reino Unido",
            (-34.61, -58.38): "Buenos Aires, Argentina",
            (19.43, -99.13): "Ciudad de México, México",
            (-23.55, -46.64): "São Paulo, Brasil",
            (35.68, 139.69): "Tokio, Japón"
        }
        
        mejor_distancia = float('inf')
        lugar_encontrado = f"Lat: {latitud:.2f}°, Lon: {longitud:.2f}°"
        
        for (lat_ref, lon_ref), nombre in lugares_conocidos.items():
            distancia = ((latitud - lat_ref)**2 + (longitud - lon_ref)**2)**0.5
            if distancia < mejor_distancia and distancia < 1.0:
                mejor_distancia = distancia
                lugar_encontrado = nombre
        
        return lugar_encontrado
    
    def guardar_carta_con_nombre_unico(self, año, mes, dia, hora, minuto, directorio_salida="cartas_generadas"):
        """Guardar la carta con un nombre único para evitar sobrescritura"""
        
        # Crear directorio si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
            print(f"Directorio creado: {directorio_salida}")
        
        # Crear nombre base del archivo
        nombre_base = f"carta_{año}{mes:02d}{dia:02d}_{hora:02d}{minuto:02d}"
        
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
            print(f"✓ Carta guardada como: {ruta_completa}")
            return ruta_completa
        except Exception as e:
            print(f"✗ Error guardando la carta: {e}")
            return None
        
    def crear_carta_completa(self, fecha_nacimiento, lugar_nacimiento, hora_oficial=None, guardar_archivo=True, directorio_salida="cartas_generadas"):
        """Crear la carta astral completa"""
        año, mes, dia, hora, minuto = fecha_nacimiento
        latitud, longitud = lugar_nacimiento
        
        jd = self.calcular_julian_day(año, mes, dia, hora, minuto)
        posiciones_planetas = self.obtener_posiciones_planetas(jd)
        cuspides_casas, ascendente, mediocielo = self.calcular_casas_placidus(jd, latitud, longitud)
        
        self.dibujar_circulos_concentricos()
        self.dibujar_signos_zodiacales(ascendente)
        self.dibujar_divisiones_casas(cuspides_casas, ascendente)
        self.dibujar_ascendente_mediocielo(ascendente, mediocielo)
        self.dibujar_planetas(posiciones_planetas, ascendente)
        
        aspectos = self.calcular_aspectos(posiciones_planetas, ascendente, mediocielo)
        self.dibujar_aspectos(aspectos, posiciones_planetas, ascendente, mediocielo)
        
        # Usar hora oficial si se proporciona, sino usar hora UTC
        if hora_oficial:
            hora_mostrar, minutos_mostrar = hora_oficial
            fecha_str = f"{dia:02d}/{mes:02d}/{año} {hora_mostrar:02d}:{minutos_mostrar:02d}"
        else:
            fecha_str = f"{dia:02d}/{mes:02d}/{año} {hora:02d}:{minuto:02d}"
            
        lugar_str = self.obtener_info_lugar(latitud, longitud)
        
        self.fig.text(0.85, 0.95, f"Carta Astral Natal\n{fecha_str}\n{lugar_str}", 
                     fontsize=14, weight='bold', ha='center', va='top',
                     bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.8))
        
        self.crear_leyenda_aspectos(aspectos)
        
        # NUEVA FUNCIONALIDAD: Guardar archivo con nombre único
        if guardar_archivo:
            self.guardar_carta_con_nombre_unico(año, mes, dia, hora, minuto, directorio_salida)
        
        return aspectos, posiciones_planetas, cuspides_casas, ascendente, mediocielo
    
    def crear_leyenda_aspectos(self, aspectos):
        """Crear leyenda con los aspectos encontrados"""
        tipos_aspectos = list(set([a['tipo'] for a in aspectos]))
        if tipos_aspectos:
            leyenda_elementos = []
            for tipo in sorted(tipos_aspectos):
                color = COLORES_ASPECTOS.get(tipo, 'gray')
                leyenda_elementos.append(plt.Line2D([0], [0], color=color, 
                                                   linewidth=2, label=tipo.title()))
            
            self.ax.legend(handles=leyenda_elementos, loc='upper left', 
                          bbox_to_anchor=(-0.15, 1.0), fontsize=9)

def main():
    print("=== GENERADOR DE CARTA ASTRAL ===")
    print("Datos de nacimiento requeridos:")

    try:
        # Datos de ejemplo
        fecha_nacimiento = (1959, 10, 1)
        hora_oficial = 11
        minutos_oficial = 47
        
        lugar_nacimiento = (41.39, 2.16)  # Barcelona (latitud, longitud)

        # Calcular timestamp para la fecha (medianoche UTC)
        fecha_medianoche_utc = datetime(
            fecha_nacimiento[0], fecha_nacimiento[1], fecha_nacimiento[2],
            0, 0, 0, tzinfo=timezone.utc
        )
        fecha_timestamp = fecha_medianoche_utc.timestamp()
        
        # Obtener offset real de la base de datos atlas2025
        offset_horas = obtener_offset_desde_db(fecha_timestamp, zone_id=1)
        
        # Calcular hora UTC manualmente usando el offset de la BD
        hora_decimal_local = hora_oficial + minutos_oficial/60
        hora_decimal_utc = hora_decimal_local - offset_horas
        
        print(f"Fecha: {fecha_nacimiento[0]}-{fecha_nacimiento[1]:02d}-{fecha_nacimiento[2]:02d}")
        print(f"Hora oficial española: {hora_oficial:02d}:{minutos_oficial:02d}")
        print(f"Offset aplicado: GMT{offset_horas:+.1f}")
        print(f"Hora UTC calculada: {hora_decimal_utc:.2f}")

        # Crear carta astral
        carta = CartaAstralSwissEph(figsize=(14, 12))

        aspectos, posiciones, cuspides, asc, mc = carta.crear_carta_completa(
            (fecha_nacimiento[0], fecha_nacimiento[1], fecha_nacimiento[2], 
             int(hora_decimal_utc), int((hora_decimal_utc % 1)*60)),
            lugar_nacimiento,
            hora_oficial=(hora_oficial, minutos_oficial),
            guardar_archivo=True,
            directorio_salida="cartas_generadas"
        )

       # Crear datos para guardar en JSON
        datos_carta = {
            "fecha_nacimiento": {
                "año": fecha_nacimiento[0],
                "mes": fecha_nacimiento[1],
                "dia": fecha_nacimiento[2],
                "hora_oficial": f"{hora_oficial:02d}:{minutos_oficial:02d}",
                "hora_utc": f"{hora_decimal_utc:.2f}"
            },
            "lugar": {
                "latitud": lugar_nacimiento[0],
                "longitud": lugar_nacimiento[1],
                "descripcion": carta.obtener_info_lugar(lugar_nacimiento[0], lugar_nacimiento[1])
            },
            "posiciones_planetas": {},
            "aspectos": aspectos,
            "ascendente": {
                "grado": asc,
                "signo": NOMBRES_SIGNOS[int(asc//30)],
                "grado_en_signo": asc % 30
            },
            "mediocielo": {
                "grado": mc,
                "signo": NOMBRES_SIGNOS[int(mc//30)],
                "grado_en_signo": mc % 30
            },
            "cuspides_casas": [
                {
                    "casa": i+1,
                    "grado": cuspide,
                    "signo": NOMBRES_SIGNOS[int(cuspide//30)],
                    "grado_en_signo": cuspide % 30
                } for i, cuspide in enumerate(cuspides)
            ]
        }
        
       # Agregar posiciones de planetas al diccionario (MODIFICADO)
        for planeta, data in posiciones.items():
            grado = data['grado']
            es_retrogrado = data.get('retrogrado', False)
            velocidad = data.get('velocidad', 0)
            signo_idx = int(grado // 30)
            grado_en_signo = grado % 30
            
            datos_carta["posiciones_planetas"][planeta] = {
                "grado_absoluto": grado,
                "signo": NOMBRES_SIGNOS[signo_idx],
                "grado_en_signo": formato_sexagesimal(grado_en_signo),
                "elemento": ELEMENTOS_SIGNOS[signo_idx],
                "retrogrado": es_retrogrado,
                "velocidad_diaria": round(velocidad, 4)
    }
        
        # GUARDADO DE ARCHIVO JSON CON NOMBRE ÚNICO
        import json
        import os
        
        directorio_salida = "cartas_generadas"
        os.makedirs(directorio_salida, exist_ok=True)
        
        # Crear nombre base para JSON
        nombre_base_json = f"carta_{fecha_nacimiento[0]:04d}{fecha_nacimiento[1]:02d}{fecha_nacimiento[2]:02d}_{int(hora_decimal_utc):02d}{int((hora_decimal_utc%1)*60):02d}"
        nombre_archivo_json = f"{nombre_base_json}.json"
        
        # Buscar nombre único para JSON
        contador = 1
        while os.path.exists(os.path.join(directorio_salida, nombre_archivo_json)):
            nombre_archivo_json = f"{nombre_base_json}_{contador:03d}.json"
            contador += 1
        
        # Guardar archivo JSON
        try:
            with open(os.path.join(directorio_salida, nombre_archivo_json), "w", encoding="utf-8") as f:
                json.dump(datos_carta, f, indent=4, ensure_ascii=False)
            print(f"✓ Datos guardados en: {os.path.join(directorio_salida, nombre_archivo_json)}")
        except Exception as e:
            print(f"✗ Error guardando archivo JSON: {e}")
        
        # Mostrar información calculada
        print("\n=== INFORMACIÓN CALCULADA ===")
        print(f"Ascendente: {asc:.2f}° ({NOMBRES_SIGNOS[int(asc//30)]} {asc%30:.1f}°)")
        print(f"Medio Cielo: {mc:.2f}° ({NOMBRES_SIGNOS[int(mc//30)]} {mc%30:.1f}°)")
        print(f"Aspectos encontrados: {len(aspectos)}")
        
        # Mostrar aspectos
        if aspectos:
            print("\n=== ASPECTOS PRINCIPALES ===")
            for aspecto in aspectos[:5]:  # Mostrar solo los primeros 5
                print(f"• {aspecto['planeta1']} {aspecto['tipo']} {aspecto['planeta2']} (orbe: {aspecto['orbe']:.1f}°)")
        
        # Mostrar la carta
        plt.show()

    except Exception as e:
        print(f"Error generando la carta: {e}")
        print("Verifica que:")
        print("1. pyswisseph esté instalado correctamente")
        print("2. atlas2025.db esté en el directorio actual")
        print("3. La carpeta 'cartas_generadas' tenga permisos de escritura")
        
    finally:
        print("\n>>> Listo para próxima consulta <<<")

if __name__ == "__main__":
    main()