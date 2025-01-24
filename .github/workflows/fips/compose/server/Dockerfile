FROM alpine:3.14

COPY start-server.sh .
COPY ca.* ./
RUN chmod +x start-server.sh

# Install OpenSSL and necessary tools
RUN apk add --no-cache openssl bash

# Expose port 443
EXPOSE 443
