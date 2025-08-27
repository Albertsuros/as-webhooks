# ===========================================
# DIRECTORIO DE AGENTES VAPI - AS ASESORES
# ===========================================

AGENTES = {
    # === AS ASESORES ===
    'veronica': '6bf7a773-8174-4127-93b4-9c935f954fae',
    
    # Asesores (nombres reales en VAPI)
    'albert': '6e9b95a9-8862-4939-9ab2-88e9b23c4ca4',      # Antes "Vendedor 1"
    'juan': '65ae8980-6786-4272-8424-b040b6940a40',     # Antes "Vendedor 2"  
    'carlos': 'a4d83ab5-869d-45b7-9e8b-fddb99a39b65',    # Antes "Vendedor 3"
    'alex': '2da38d9d-9ff8-499f-8241-b1c955ebac39',      # Antes "Técnico Soporte"
    
    # === AS CARTASTRAL ===
    'sofia': '0bfe7461-69d5-4077-99b8-2e02c76b5287',

    # Asesores (nombres reales en VAPI)
    'diana': 'asst_78f4bfbd-cf67-46cb-910d-c8f0f8adf3fc',     # Antes "Astrologa Cartastral"
    'luna': 'asst_9513ec30-f231-4171-959c-26c8588d248e',      # Antes "Astrologa Revolsolar"
    'olga': 'asst_9960b33c-db72-4ebd-ae3e-69ce6f7e6660',     # Antes "Astrologa Sinastria"
    'oscar': 'asst_d218cde4-d4e1-4943-8fd9-a1df9404ebd6', # Antes "Astrologa Astrolhoraria"
    'diana': 'asst_63a0f9b9-c5d5-4df6-ba6f-52d700b51275',    # Antes "Psico Coaching"
    'paloma': 'asst_8473d3ab-22a7-479c-ae34-427e992023de',   # Antes "Lectura Manos"
    'iris': 'asst_9cae2faa-2a8e-498b-b8f4-ab7af65bf734',     # Antes "Lectura Facial"
    'roman': 'asst_84c67029-8059-4066-a5ae-8532b99fd24c'     # Antes "Grafólogo"
}

ESPECIALIDADES = {
    # AS Asesores
    'juan': 'Consultor Comercial',
    'carlos': 'Especialista Servicios',
    'albert': 'Responsable Ventas',
    'alex': 'Soporte Técnico',
    
    # AS Cartastral
    'marco': 'Astrólogo Carta Astral',
    'luna': 'Astróloga Revolución Solar',
    'venus': 'Especialista Sinastría',
    'oscar': 'Astrólogo Horario',
    'diana': 'Coach Psicológica',
    'paloma': 'Quiromante',
    'iris': 'Fisonomista',
    'roman': 'Grafólogo'
}

# Funciones
def get_agent_id(nombre):
    return AGENTES.get(nombre.lower())

def get_especialidad(nombre):
    return ESPECIALIDADES.get(nombre.lower())