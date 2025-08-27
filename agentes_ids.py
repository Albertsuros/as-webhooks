# ===========================================
# DIRECTORIO DE AGENTES VAPI - AS ASESORES
# ===========================================

AGENTES = {
    # === AS ASESORES - VERÓNICA Y TRANSFERENCIAS ===
    'veronica': 'ID_DE_VERONICA',
    
    'vendedor_1': '6e9b95a9-8862-4939-9ab2-88e9b23c4ca4',  # Juan Vendedor
    'vendedor_2': '65ae8980-6786-4272-8424-b040b6940a40',  # María Comercial  
    'vendedor_3': 'a4d83ab5-869d-45b7-9e8b-fddb99a39b65',  # Carlos Ventas
    'soporte': '2da38d9d-9ff8-499f-8241-b1c955ebac39',     # Alex Soporte
    
    # === AS CARTASTRAL - SOFÍA Y ESPECIALISTAS ===
    'sofia': 'ID_DE_SOFIA',
    
    'carta_astral': 'asst_78f4bfbd-cf67-46cb-910d-c8f0f8adf3fc',      # Marco Astrólogo
    'revolucion_solar': 'asst_9513ec30-f231-4171-959c-26c8588d248e',  # Luna Astróloga
    'sinastria': 'asst_9960b33c-db72-4ebd-ae3e-69ce6f7e6660',        # Venus Sinastría
    'horaria': 'asst_d218cde4-d4e1-4943-8fd9-a1df9404ebd6',          # Mercurio Horario
    'psico_coaching': 'asst_63a0f9b9-c5d5-4df6-ba6f-52d700b51275',   # Diana Coach
    'lectura_manos': 'asst_8473d3ab-22a7-479c-ae34-427e992023de',    # Paloma Quiromancia
    'lectura_facial': 'asst_9cae2faa-2a8e-498b-b8f4-ab7af65bf734',   # Iris Facial
    'grafologia': 'asst_84c67029-8059-4066-a5ae-8532b99fd24c'        # Román Grafólogo
}

# Función para obtener ID por nombre
def get_agent_id(nombre_agente):
    return AGENTES.get(nombre_agente)

# Función para obtener nombre legible  
def get_agent_name(nombre_agente):
    nombres_legibles = {
        'vendedor_1': 'Juan (Vendedor Senior)',
        'vendedor_2': 'María (Comercial)',
        'vendedor_3': 'Carlos (Ventas)',
        'soporte': 'Alex (Soporte Técnico)',
        'carta_astral': 'Marco (Astrólogo Carta Astral)',
        'revolucion_solar': 'Luna (Astróloga Revolución Solar)',
        # etc...
    }
    return nombres_legibles.get(nombre_agente, nombre_agente)