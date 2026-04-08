# Build ddev sdist so the final image doesn't need hatchling/hatch-vcs
FROM registry.ddbuild.io/images/mirror/python:3.13.0 AS ddev-python
COPY . /home
RUN python -m pip install build \
 && python -m build -s /home/ddev \
 && mv /home/ddev/dist/*.tar.gz /ddev.tar.gz

FROM registry.ddbuild.io/images/mirror/ubuntu:25.04

# Update sources and install required packages
RUN apt-get update \
 && apt-get -y install --no-install-recommends \
      apt-transport-https \
      build-essential \
      ca-certificates \
      curl \
      gcc \
      git \
      libffi-dev \
      libssl-dev \
      moreutils \
      openssh-client \
      pipx \
      python3-dev \
 # Clean up
 && apt-get -y autoremove \
 && apt-get -y clean \
 && rm -rf /tmp/* \
 && rm -rf /var/lib/apt/lists/* \
 && rm -rf /var/tmp/*

# Add GitHub public host key to the list of known hosts
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
RUN mkdir -p ~/.ssh \
 && ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

# dd-octo-sts CLI for GitHub token exchange (replaces SSH deploy key)
# To update: crane ls registry.ddbuild.io/dd-octo-sts | sort -V | tail -1
#            crane digest registry.ddbuild.io/dd-octo-sts:<version>
COPY --from=registry.ddbuild.io/dd-octo-sts:v1.10.4@sha256:20edc79b3fc3f9cd58eb0aeba7391a8e63ccb79c0b969a4a62a745cf5b2e39c2 /usr/local/bin/dd-octo-sts /usr/local/bin/dd-octo-sts

# Locales are required to be set to use click
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PIPX_HOME=/opt/pipx
ENV PIPX_BIN_DIR=/usr/local/bin

COPY --from=ddev-python /ddev.tar.gz /

# Install ddev for release tagging and awscli for signing integrations-extras and marketplace packages
RUN pipx install awscli==1.29.7 \
 && pipx install /ddev.tar.gz
