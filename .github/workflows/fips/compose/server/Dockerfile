ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY start-server.sh .
COPY ca.* ./
RUN chmod +x start-server.sh

# Install OpenSSL and necessary tools
RUN apk add --no-cache openssl bash curl

# Expose port 443
EXPOSE 443
