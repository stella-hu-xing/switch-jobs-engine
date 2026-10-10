FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run injects $PORT; the request-serving service runs uvicorn.
# The background worker (crawling/enrichment) is deployed as a Cloud Run Job
# overriding the entrypoint with: python -m app.worker
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
