FROM bash:5.2.15
ENV LINKERD2_VERSION=stable-2.10.2
ENV KUBECTL_VERSION=v1.23.17
RUN set -eux; \
    apk --no-cache add dumb-init gettext ca-certificates openssl curl; \
    kubectl_arch="$(apk --print-arch)"; \
    case "$kubectl_arch" in \
        x86_64) kubectl_arch="amd64" ;; \
        aarch64) kubectl_arch="arm64" ;; \
        *) echo "Unsupported architecture: $kubectl_arch"; exit 1 ;; \
    esac; \
    curl -Lo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${kubectl_arch}/kubectl"; \
    chmod +x /usr/local/bin/kubectl; \
    curl -sL https://run.linkerd.io/install | sh; \
    ln -s /root/.linkerd2/bin/linkerd /usr/local/bin/linkerd

WORKDIR /
COPY install-linkerd.sh /
RUN chmod +x install-linkerd.sh

ENTRYPOINT /usr/local/bin/bash /install-linkerd.sh
