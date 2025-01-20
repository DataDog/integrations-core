ARG BASE_IMAGE

FROM ${BASE_IMAGE}

SHELL ["sh", "-c"]

COPY start-server.sh /usr/local/bin/start-server.sh
COPY ca.* /tmp/
RUN chmod +x /usr/local/bin/start-server.sh

# Install OpenSSL and necessary tools
RUN apk add --no-cache openssl bash

# Expose port 443
EXPOSE 443
