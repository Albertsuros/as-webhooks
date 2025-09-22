import json
import matplotlib.pyplot as plt
import numpy as np

# Cargar datos desde JSON
with open("data/carta.json", encoding="utf-8") as f:
    data = json.load(f)

planetas = data.get("planets", {})
casas = data.get("houses", {})

# Crear figura
fig, ax = plt.subplots(figsize=(6,6), dpi=150)
ax.set_xlim(-1.1, 1.1)
ax.set_ylim(-1.1, 1.1)
ax.axis("off")

# Dibujar círculo exterior
circ = plt.Circle((0, 0), 1, fill=False, linewidth=2)
ax.add_patch(circ)

# Dibujar las casas (líneas radiales)
for casa, grado in casas.items():
    angulo = np.deg2rad(grado - 90)  # ajustamos para iniciar en ascendente
    x = [0, np.cos(angulo)]
    y = [0, np.sin(angulo)]
    ax.plot(x, y, color='gray', linestyle='--', linewidth=1)

    # Etiqueta de la casa
    ax.text(1.1 * np.cos(angulo), 1.1 * np.sin(angulo), casa.strip(), fontsize=8, ha='center', va='center')

# Lista de signos en orden zodiacal
signos = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"
]

# Ángulos donde colocar cada signo (30° por signo)
for i, signo in enumerate(signos):
    angulo = np.deg2rad(i * 30 - 90)
    x = 1.2 * np.cos(angulo)
    y = 1.2 * np.sin(angulo)
    ax.text(x, y, signo, fontsize=9, color="darkred", ha='center', va='center')

# Dibujar divisiones de casas (12)
for i in range(12):
    angle = i * 30
    x = np.cos(np.radians(angle))
    y = np.sin(np.radians(angle))
    ax.plot([0,x],[0,y], color="gray", linestyle="--")

# Dibujar símbolos zodiacales en el borde exterior
zodiac_symbols = ["♈︎","♉︎","♊︎","♋︎","♌︎","♍︎","♎︎","♏︎","♐︎","♑︎","♒︎","♓︎"]
for i, symbol in enumerate(zodiac_symbols):
    angle = np.deg2rad(i * 30 + 15)  # posición central de cada signo
    x = 1.07 * np.cos(angle)  # un poco más afuera del círculo
    y = 1.07 * np.sin(angle)
    ax.text(x, y, symbol, fontsize=16, ha='center', va='center')

# Dibujar los planetas con etiquetas
for planeta, grados in planetas.items():
    angulo = np.radians(grados)
    x = 0.9 * np.cos(angulo)
    y = 0.9 * np.sin(angulo)
    ax.plot(x,y,"o", markersize=8, label=planeta)
    # Etiqueta con nombre y grado
    etiqueta = f"{planeta}\n{grados:.1f}°"
    ax.text(x,y, etiqueta, fontsize=8, ha='center', va='center')

# Guardar imagen
plt.savefig("static/carta.png", dpi=300, bbox_inches="tight")
print("✅ Imagen con etiquetas generada correctamente: carta.png")

import shutil
import glob
import os

# Buscar la carta más reciente en la carpeta cartas_generadas
try:
    archivos = glob.glob("cartas_generadas/*.png")
    if archivos:
        archivo_mas_reciente = max(archivos, key=os.path.getmtime)
        shutil.copy(archivo_mas_reciente, "static/carta.png")
        print(f"✅ Imagen copiada a static/carta.png desde {archivo_mas_reciente}")
    else:
        print("⚠️ No se encontró ninguna imagen de carta para copiar.")
except Exception as e:
    print(f"⚠️ Error copiando imagen a static: {e}")