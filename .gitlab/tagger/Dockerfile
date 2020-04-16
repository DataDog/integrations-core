FROM ubuntu:18.04

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
# https://help.github.com/en/articles/githubs-ssh-key-fingerprints
RUN mkdir -p ~/.ssh \
 && echo "|1|L3rBLxsTRXA5C48+4DcV8hHvK4Y=|fFirAqNJJWk+xY7wkc703OcVH+w= ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" > ~/.ssh/known_hosts

# Environment
ENV DDEV_ROOT ~/datadog_checks_dev

# Assumes the build context is `integrations-core/datadog_checks_dev`
COPY . ${DDEV_ROOT}

# Install pip
RUN curl -sSL https://raw.githubusercontent.com/pypa/get-pip/master/get-pip.py | python3 \
 # Install ddev for release tagging
 && pip3 install ${DDEV_ROOT}[cli] \
 # Install awscli for access to GitHub deploy key stored in SSM
 && pip3 install awscli==1.16.129
