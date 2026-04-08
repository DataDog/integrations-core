FROM registry.ddbuild.io/images/mirror/ubuntu:25.04

# Get uv — manages Python installations on demand, no system Python pinning needed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

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
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Mount the build context (including .git for hatch-vcs) without adding it to the image.
# Copy to a writable location since hatch-vcs writes the version file during build.
# Both the copy and the removal happen in one RUN so the source never lands in the image.
RUN --mount=type=bind,source=.,target=/src \
    cp -r /src /tmp/repo \
 && uv tool install /tmp/repo/ddev \
 && uv tool install 'awscli==1.29.7' \
 && rm -rf /tmp/repo
