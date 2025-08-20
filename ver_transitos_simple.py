import matplotlib.pyplot as plt
import sys
import os

# Importar la clase desde tu archivo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transitos import CartaTransitos  # Cambiar nombre

def mostrar_carta_transitos():
    """Función simple para mostrar la carta de transitos"""
    print("=== MOSTRANDO CARTA DE TRANSITOS ===")
    
    try:
        # Datos de ejemplo (modifica según necesites)
        fecha_nacimiento = (1959, 10, 1, 11, 47)  # año, mes, día, hora, minuto
        lugar_nacimiento = (41.39, 2.16)  # Barcelona (latitud, longitud)
        fecha_consulta = (2024, 12, 1)  # año, mes, día
        
        # Crear carta de transitos
        carta = CartaTransitos(figsize=(14, 12))  # Corregir nombre de clase
        
        # Generar carta completa
        aspectos, pos_natales, pos_transitos, fecha_transito, edad = carta.crear_carta_transitos(
            fecha_nacimiento,
            fecha_consulta,
            lugar_nacimiento,
            guardar_archivo=True,
            directorio_salida="cartas_generadas"
        )
        
        print(f"✓ Carta generada exitosamente")
        print(f"  - Fecha transito: {fecha_transito.strftime('%Y-%m-%d %H:%M')}")
        print(f"  - Edad: {edad:.1f} años")
        print(f"  - Aspectos encontrados: {len(aspectos)}")
        
        # Mostrar la carta en pantalla
        plt.show()
        
        return True
        
    except Exception as e:
        print(f"✗ Error generando la carta: {e}")
        return False

if __name__ == "__main__":  # Corregir esta línea
    mostrar_carta_transitos()