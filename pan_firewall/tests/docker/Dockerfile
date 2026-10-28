# Shared by the fake firewall and the fake Panorama: only the command differs. The tests directory (fixtures and
# `fixture_map`) is mounted read-only at /app/tests by docker-compose.yaml, so the unit fake and these fakes share it.
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Self-signed certificate generated at build time; nothing secret is committed.
RUN mkdir -p /app/certs \
    && openssl req -x509 -newkey rsa:2048 -nodes \
       -keyout /app/certs/key.pem -out /app/certs/cert.pem \
       -days 365 -subj "/CN=localhost"

ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

EXPOSE 443
