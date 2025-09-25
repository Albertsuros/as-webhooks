FROM python:3.11-bookworm

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    xvfb \
    fonts-liberation \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    xfonts-75dpi \
    xfonts-base \
    && rm -rf /var/lib/apt/lists/*

# Instalar Playwright y sus dependencias
RUN pip install playwright
RUN playwright install --with-deps chromium

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]