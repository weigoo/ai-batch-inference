# worker/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system deps (minimal)
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY worker/requirements.txt .

# Install CPU-only PyTorch
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining deps
RUN pip install --no-cache-dir \
    -r requirements.txt

COPY worker/ ./worker/
COPY shared/ ./shared/

CMD ["python", "-u", "-m", "worker.worker"]