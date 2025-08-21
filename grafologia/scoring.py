from .features import interpretar_caracteristicas

def generar_interpretacion_ia(caracteristicas):
    """Generar interpretación usando IA + conocimiento base"""
    interpretacion_base = interpretar_caracteristicas(caracteristicas)
    
    # Aquí puedes combinar con OpenAI para una interpretación más rica
    prompt = f"Basándome en estas características grafológicas: {interpretacion_base}, genera un análisis personalizado..."
    
    return interpretacion_base