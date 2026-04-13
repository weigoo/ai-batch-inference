# api/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY api/ ./api/
COPY shared/ ./shared/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]