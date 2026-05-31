FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=pinn_web.settings

WORKDIR /app

# libgomp es necesaria para PyTorch CPU en Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar PyTorch CPU-only primero (evita descargar las variantes CUDA)
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
      torch==2.4.0

# Resto de dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código de la aplicación
COPY . /app/

RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
