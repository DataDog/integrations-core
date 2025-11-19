FROM alpine:3.18

# Install OpenSSL and necessary tools
RUN apk add --no-cache openssl bash

COPY start-server.sh /usr/local/bin/start-server.sh
COPY ca.* /tmp/
RUN chmod +x /usr/local/bin/start-server.sh

# Expose port 443
EXPOSE 443
