FROM python:3.9-slim

# Instalar dependencias del sistema para WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfribidi0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libfontconfig1 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para fontconfig
ENV FONTCONFIG_PATH=/etc/fonts

WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Exponer puerto (Railway usa PORT environment variable)
EXPOSE 8000

# Usar gunicorn como en tu configuración actual
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "main:app"]