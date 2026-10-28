# Built from the official Teleport release tarball instead of pulling
# public.ecr.aws/gravitational/teleport-distroless, because anonymous ECR Public
# pulls from GitHub runners fail with "toomanyrequests: Data limit exceeded".
FROM debian:bookworm-slim

ARG TELEPORT_VERSION=17.2.9
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl dumb-init \
    && curl -fsSL "https://cdn.teleport.dev/teleport-v${TELEPORT_VERSION}-linux-${TARGETARCH}-bin.tar.gz" \
        | tar -xz -C /usr/local/bin --strip-components=1 teleport/teleport \
    && apt-get purge -y curl \
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/usr/bin/dumb-init", "/usr/local/bin/teleport", "start", "-c", "/etc/teleport/teleport.yaml"]
