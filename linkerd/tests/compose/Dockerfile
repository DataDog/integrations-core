FROM bash:5.2.15
ENV LINKERD2_VERSION=stable-2.10.2
ENV KUBECTL_VERSION=v1.23.17
RUN apk --no-cache add dumb-init gettext ca-certificates openssl curl \
    && curl -Lo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl \
    && curl -sL https://run.linkerd.io/install | sh \
    && ln -s /root/.linkerd2/bin/linkerd /usr/local/bin/linkerd

WORKDIR /
COPY install-linkerd.sh /
RUN chmod +x install-linkerd.sh

ENTRYPOINT /usr/local/bin/bash /install-linkerd.sh
