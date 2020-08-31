FROM ubuntu:16.04

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

# 1.0.9 (GA)
RUN apt-get update && apt-get install -y --no-install-recommends \
    iotedge && \
    rm -rf /var/lib/apt/lists/*

# 1.0.10-rc2 (Beta)
# # RCs are not released to the Microsoft repositories.
# # Install directly from GitHub releases.
# # See: https://github.com/MicrosoftDocs/azure-docs/issues/60354
# RUN curl -L https://github.com/Azure/azure-iotedge/releases/download/1.0.10-rc2/libiothsm-std_1.0.10.rc2-1_ubuntu16.04_amd64.deb -o libiothsm-std.deb && \
#     dpkg -i ./libiothsm-std.deb
# RUN curl -L https://github.com/Azure/azure-iotedge/releases/download/1.0.10-rc2/iotedge_1.0.10.rc2-1_ubuntu16.04_amd64.deb -o iotedge.deb && \
#     dpkg -i ./iotedge.deb

COPY rund.sh rund.sh

RUN sed -i 's/\r//' ./rund.sh && \
    chmod u+x rund.sh

ENTRYPOINT [ "./rund.sh" ]
