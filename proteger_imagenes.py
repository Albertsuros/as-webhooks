#!/usr/bin/env python3
"""
🛡️ PROTECTOR DE IMÁGENES CRÍTICAS - AS Cartastral
Evita que el sistema de limpieza automático borre imágenes esenciales
"""

import os
import shutil
import time
from datetime import datetime

# IMÁGENES QUE NUNCA SE DEBEN BORRAR
IMAGENES_CRITICAS = [
    'logo.JPG',
    'astrologia-3.JPG',
    'Tarot y astrologia-5.JPG', 
    'Sinastria.JPG',
    'astrologia-1.JPG',
    'Lectura-de-manos-p.jpg',
    'lectura facial.JPG',
    'coaching-4.JPG',
    'grafologia_2.jpeg'
]

def proteger_imagenes():
    """Copiar imágenes críticas a directorio protegido"""
    
    # Crear directorios necesarios
    os.makedirs('./static/img/', exist_ok=True)
    
    print(f"🛡️ INICIANDO PROTECCIÓN DE IMÁGENES - {datetime.now()}")
    
    protegidas = 0
    no_encontradas = 0
    
    for imagen in IMAGENES_CRITICAS:
        origen = f"./img/{imagen}"
        destino = f"./static/img/{imagen}"
        
        try:
            if os.path.exists(origen):
                # Copiar si no existe o si el original es más nuevo
                if not os.path.exists(destino) or os.path.getmtime(origen) > os.path.getmtime(destino):
                    shutil.copy2(origen, destino)
                    print(f"✅ Protegida: {imagen}")
                    protegidas += 1
                else:
                    print(f"✓ Ya protegida: {imagen}")
            else:
                print(f"⚠️ No encontrada: {imagen}")
                no_encontradas += 1
                
        except Exception as e:
            print(f"❌ Error protegiendo {imagen}: {e}")
    
    print(f"📊 RESUMEN: {protegidas} protegidas, {no_encontradas} no encontradas")
    
    # Crear archivo de control para evitar borrado
    crear_archivo_control()
    
    return protegidas, no_encontradas

def crear_archivo_control():
    """Crear archivo que indica que las imágenes están protegidas"""
    control_file = "./static/img/.PROTEGIDAS_NO_BORRAR"
    
    with open(control_file, 'w') as f:
        f.write(f"""# IMÁGENES PROTEGIDAS - AS Cartastral
# Generado: {datetime.now()}
# 
# ESTAS IMÁGENES SON CRÍTICAS PARA EL SISTEMA:
# - NO BORRAR NUNCA
# - NECESARIAS PARA GENERAR PDFs
# - COPIAS DE SEGURIDAD EN CASO DE LIMPIEZA AUTOMÁTICA
#
# Imágenes protegidas:
""")
        for imagen in IMAGENES_CRITICAS:
            f.write(f"# - {imagen}\n")

def verificar_integridad():
    """Verificar que todas las imágenes críticas están disponibles"""
    
    print(f"🔍 VERIFICANDO INTEGRIDAD DE IMÁGENES...")
    
    disponibles = 0
    faltantes = []
    
    for imagen in IMAGENES_CRITICAS:
        rutas_posibles = [
            f"./static/img/{imagen}",
            f"./img/{imagen}",
            f"/app/img/{imagen}",
            f"/app/static/img/{imagen}"
        ]
        
        encontrada = False
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                print(f"✅ {imagen} → {ruta}")
                disponibles += 1
                encontrada = True
                break
        
        if not encontrada:
            print(f"❌ FALTA: {imagen}")
            faltantes.append(imagen)
    
    porcentaje = (disponibles / len(IMAGENES_CRITICAS)) * 100
    print(f"📊 INTEGRIDAD: {porcentaje:.1f}% ({disponibles}/{len(IMAGENES_CRITICAS)})")
    
    return porcentaje, faltantes

def limpiar_solo_temporales():
    """Función de limpieza segura que NO toca las imágenes críticas"""
    from datetime import timedelta
    import glob
    
    hace_7_dias = datetime.now() - timedelta(days=7)
    borrados = 0
    
    # Limpiar solo archivos temporales generados
    patrones_temporales = [
        "static/carta_natal_*.png",
        "static/progresiones_*.png", 
        "static/transitos_*.png",
        "static/revolucion_*.png",
        "static/sinastria_*.png",
        "static/horaria_*.png",
        "informes/informe_*.pdf",
        "templates/informe_*.html"
    ]
    
    for patron in patrones_temporales:
        for archivo in glob.glob(patron):
            try:
                nombre = os.path.basename(archivo)
                
                # NUNCA borrar imágenes críticas
                if nombre in IMAGENES_CRITICAS:
                    print(f"🛡️ PROTEGIDA (no borrar): {nombre}")
                    continue
                
                # Borrar solo archivos antiguos
                fecha_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
                if fecha_archivo < hace_7_dias:
                    os.remove(archivo)
                    print(f"🗑️ Borrado temporal antiguo: {archivo}")
                    borrados += 1
                else:
                    print(f"⏳ Conservando temporal reciente: {archivo}")
                    
            except Exception as e:
                print(f"⚠️ Error procesando {archivo}: {e}")
    
    print(f"✅ Limpieza segura completada: {borrados} archivos temporales borrados")
    return borrados

if __name__ == "__main__":
    print("🚀 EJECUTANDO PROTECCIÓN DE IMÁGENES...")
    proteger_imagenes()
    porcentaje, faltantes = verificar_integridad()
    
    if porcentaje >= 80:
        print("✅ SISTEMA PROTEGIDO CORRECTAMENTE")
    else:
        print(f"⚠️ ATENCIÓN: Faltan {len(faltantes)} imágenes críticas")
        for img in faltantes:
            print(f"   - {img}")