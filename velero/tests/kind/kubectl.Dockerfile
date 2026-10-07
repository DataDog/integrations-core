FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg coreutils ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY download-kubectl.sh /tmp/download-kubectl.sh

RUN sh /tmp/download-kubectl.sh /tmp/kubectl && \
    install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl && \
    rm /tmp/kubectl /tmp/download-kubectl.sh
