FROM python:3.9-bullseye

# Instalar dependencias manualmente para evitar conflictos
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Instalar solo el navegador, sin dependencias automáticas
RUN playwright install chromium

# Copiar todo el código
COPY . .

# Puerto para Railway
EXPOSE 5000

# Comando de inicio
CMD ["python", "main.py"]