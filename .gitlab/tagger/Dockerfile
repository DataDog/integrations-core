# Use a separate image to build ddev from source so the final image doesn't need git
FROM python:3.11 AS ddev-python
COPY . /home
RUN python -m pip install build
RUN python -m build -s ./home/ddev
RUN mv ./home/ddev/dist/*.tar.gz ddev.tar.gz 

FROM registry.ddbuild.io/images/mirror/ubuntu:22.04

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
 && echo "|1|L3rBLxsTRXA5C48+4DcV8hHvK4Y=|fFirAqNJJWk+xY7wkc703OcVH+w= ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=" > ~/.ssh/known_hosts

# Locales are required to be set to use click
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Copy in ddev.tar.gz from the other image
COPY --from=ddev-python ddev.tar.gz /

# Install pip
RUN curl -sSL https://bootstrap.pypa.io/get-pip.py | python3 \
 # Install ddev for release tagging
 && pip3 install --no-cache-dir ddev.tar.gz \
 # Install awscli for access to GitHub deploy key stored in SSM
 && pip3 install --no-cache-dir awscli==1.29.7
