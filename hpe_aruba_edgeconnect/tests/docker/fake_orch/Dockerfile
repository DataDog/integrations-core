FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY tests/docker/fake_orch/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/certs \
    && openssl req -x509 -newkey rsa:2048 -nodes \
       -keyout /app/certs/key.pem -out /app/certs/cert.pem \
       -days 365 -subj "/CN=localhost"

COPY tests/docker/fake_orch/app.py app.py

EXPOSE 8443

CMD ["python", "app.py"]
