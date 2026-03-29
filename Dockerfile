FROM python:3.12-slim

WORKDIR /app

# System deps for asyncpg, lxml, playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Railway sets PORT env var automatically
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
