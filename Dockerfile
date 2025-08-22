FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "main.py"]
