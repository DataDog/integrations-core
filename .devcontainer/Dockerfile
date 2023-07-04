# This dockerfile is used to build the devcontainer environment.
# more info about vscode devcontainer: https://code.visualstudio.com/docs/devcontainers/containers
FROM mcr.microsoft.com/devcontainers/python:1-3.9-bullseye
# Need to install `liblz4-dev` `libunwind-dev` packages for ddev installation see: https://github.com/DataDog/integrations-core/issues/14043
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt install -y liblz4-dev libunwind-dev --option=Dpkg::Options::=--force-confdef
