FROM ubuntu
ARG PYTHON_VERSION=3.9

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt install -yq  software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -yq python${PYTHON_VERSION} python3-pip python${PYTHON_VERSION}-dev python3-venv python${PYTHON_VERSION}-distutils python3-psutil
RUN apt-get install -yq git build-essential liblz4-dev libunwind-dev

RUN pip install pipx
ENV PATH=/root/.local/bin:$PATH
