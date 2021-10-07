FROM registry.ddbuild.io/images/mirror/python:3.8-alpine
RUN apk add --update --no-cache git
RUN python3 -m pip install awscli==1.16.159
WORKDIR /app
COPY validate_consul_sync.py /app/validate_consul_sync.py
