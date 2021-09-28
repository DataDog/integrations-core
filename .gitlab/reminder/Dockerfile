FROM registry.ddbuild.io/images/mirror/python:3.7.2-alpine3.9 AS reqs

WORKDIR /

COPY requirements.in /

RUN pip install pip-tools

RUN pip-compile --quiet --generate-hashes --output-file requirements.txt requirements.in

# Our actual image
FROM registry.ddbuild.io/images/mirror/python:3.7.2-alpine3.9

RUN apk add --update --no-cache bash

# Copy our resolved requirements
COPY --from=reqs requirements.txt /

RUN pip install -r requirements.txt
