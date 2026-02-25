# Semantic Code Search backend - Railway deployment
FROM python:3.12-slim

WORKDIR /app

# Install system deps for sentence-transformers (optional, for faster loading)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and pre-built ChromaDB
COPY . .

# Expose port for Railway
EXPOSE 8000

# Run FastAPI with uvicorn
# Railway sets PORT env var; default 8000 for local
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
