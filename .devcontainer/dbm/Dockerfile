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
RUN DEBIAN_FRONTEND=noninteractive apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# Install msodbcsql18, psql
RUN curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc
RUN curl https://packages.microsoft.com/config/debian/11/prod.list | tee /etc/apt/sources.list.d/mssql-release.list
RUN DEBIAN_FRONTEND=noninteractive apt update && ACCEPT_EULA=Y apt install -y msodbcsql18 mssql-tools18 unixodbc-dev libgssapi-krb5-2 postgresql-client
RUN echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
# Install pipx & ddev
RUN python3 -m pip install pipx && python3 -m pipx ensurepath && python3 -m pipx install ddev
