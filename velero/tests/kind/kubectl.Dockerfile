FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg coreutils ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN wget -q -O kubectl https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl
