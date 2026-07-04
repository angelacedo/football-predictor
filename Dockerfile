FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts
COPY schema.sql ./

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/predict_upcoming.py"]
