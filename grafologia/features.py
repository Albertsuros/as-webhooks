import json
import os

def cargar_conocimiento_grafologia():
    """Cargar base de conocimiento de grafología"""
    try:
        ruta = os.path.join(os.path.dirname(__file__), 'grafologia_knowledge.json')
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando conocimiento: {e}")
        return {}

def interpretar_caracteristicas(caracteristicas):
    """Interpretar características usando la base de conocimiento"""
    conocimiento = cargar_conocimiento_grafologia()
    interpretacion = []
    
    for tipo, valor in caracteristicas.items():
        if tipo in conocimiento['caracteristicas']:
            if valor in conocimiento['caracteristicas'][tipo]:
                info = conocimiento['caracteristicas'][tipo][valor]
                interpretacion.append({
                    'caracteristica': tipo,
                    'valor': valor,
                    'significado': info['significado'],
                    'personalidad': info['personalidad']
                })
    
    return interpretacion