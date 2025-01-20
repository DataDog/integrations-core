ARG BASE_IMAGE

FROM ${BASE_IMAGE}

RUN echo "Using base image: ${BASE_IMAGE}"

ADD conf.d/connections.yaml /etc/datadog-agent/conf.d/connections.yaml
ADD checks.d/connections.py /etc/datadog-agent/checks.d/connections.py
