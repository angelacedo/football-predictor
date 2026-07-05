FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir ".[web]"

COPY web ./web

ENV PYTHONUNBUFFERED=1
WORKDIR /app/web

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
