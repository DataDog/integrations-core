FROM ubuntu:16.04

ARG LIBIOTHSM_STD_URL
ARG IOTEDGE_URL

RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    iproute2 \
    iputils-ping \
    systemd  && \
    rm -rf /var/lib/apt/lists/*

RUN curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > ./microsoft-prod.list && \
    cp ./microsoft-prod.list /etc/apt/sources.list.d/ && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    cp ./microsoft.gpg /etc/apt/trusted.gpg.d/

RUN apt-get update && apt-get install -y --no-install-recommends \
    moby-cli \
    moby-engine && \
    rm -rf /var/lib/apt/lists/*

RUN env

# Only GA versions are available in the Microsoft apt repository, so we need to install RCs from GitHub releases.
# See: https://github.com/MicrosoftDocs/azure-docs/issues/60354
RUN curl -L "$LIBIOTHSM_STD_URL" -o libiothsm-std.deb && \
    dpkg -i ./libiothsm-std.deb
RUN curl -L "$IOTEDGE_URL" -o iotedge.deb && \
    dpkg -i ./iotedge.deb

COPY rund.sh rund.sh

RUN sed -i 's/\r//' ./rund.sh && \
    chmod u+x rund.sh

ENTRYPOINT [ "./rund.sh" ]
