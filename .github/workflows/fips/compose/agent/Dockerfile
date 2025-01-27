ARG BASE_IMAGE

FROM ${BASE_IMAGE}

RUN echo "Using base image: ${BASE_IMAGE}"

# TODO: Remove this once cryptography is taken care of
# ENV OPENSSL_CONF /opt/datadog-agent/embedded/ssl/openssl.cnf
# ENV OPENSSL_MODULES /opt/datadog-agent/embedded/lib/ossl-modules

ADD conf.d/* /etc/datadog-agent/conf.d/
ADD checks.d/* /etc/datadog-agent/checks.d/
