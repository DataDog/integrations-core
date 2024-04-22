# This dockerfile is used to build the devcontainer environment.
# more info about vscode devcontainer: https://code.visualstudio.com/docs/devcontainers/containers
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y liblz4-dev libunwind-dev ca-certificates curl gnupg
# Docker and docker-compose installation
RUN install -m 0755 -d /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN chmod a+r /etc/apt/keyrings/docker.gpg
# Add the repository to Apt sources:
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt update
RUN DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
RUN sed -i 's\ulimit -Hn 524288\ulimit -n 524288\g' /etc/init.d/docker
