FROM ubuntu as CERT_GETTER

ENV CACERT_BUNDLE_VERSION=2023-12-12
ENV CACERT_BUNDLE_SHA256="ccbdfc2fe1a0d7bbbb9cc15710271acf1bb1afe4c8f1725fe95c4c7733fcbe5a"
RUN apt-get update && apt-get install -y wget
RUN wget https://curl.se/ca/cacert-${CACERT_BUNDLE_VERSION}.pem -O /cacert.pem
RUN echo "${CACERT_BUNDLE_SHA256}  /cacert.pem" | sha256sum --check

FROM --platform=linux/arm64 amazonlinux:2.0.20181114

# Copy cert
COPY --from=CERT_GETTER /cacert.pem /etc/pki/tls/certs/ca-bundle.crt

# Script for the common task of fetching a source tarball, compiling and installing it
COPY install-from-source.sh /

# Install dependencies
RUN yum -y install @development tar \
    && yum clean all

# openssl
RUN yum install -y perl-IPC-Cmd && \
 DOWNLOAD_URL="https://www.openssl.org/source/openssl-{{version}}.tar.gz" \
 VERSION="3.0.12" \
 SHA256="f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61" \
 RELATIVE_PATH="openssl-{{version}}" \
 # no-module prevents the creation of dynamically loaded modules that would be problematic to bundle into Python wheels
 CONFIGURE_SCRIPT="./config" \
 bash install-from-source.sh \
 -fPIC shared \
 # This prevents the creation of dynamically loaded modules that would be problematic to bundle into Python wheels
 no-module \
 no-comp no-idea no-mdc2 no-rc5 no-ssl3 no-gost

# Compile and install Python 3
ENV PYTHON3_VERSION=3.11.5
RUN yum install -y libffi-devel && \
 DOWNLOAD_URL="https://python.org/ftp/python/{{version}}/Python-{{version}}.tgz" \
 VERSION="${PYTHON3_VERSION}" \
 SHA256="a12a0a013a30b846c786c010f2c19dd36b7298d888f7c4bd1581d90ce18b5e58" \
 RELATIVE_PATH="Python-{{version}}" \
 bash install-from-source.sh --prefix=/opt/python/${PYTHON_VERSION} --with-ensurepip=yes --enable-shared --enable-ipv6 --with-dbmliborder=
ENV PATH="/opt/python/${PYTHON_VERSION}/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/python/${PYTHON_VERSION}/lib:${LD_LIBRARY_PATH}"
# Set up virtual environment for Python 3
RUN /opt/python/${PYTHON_VERSION}/bin/python3 -m pip install --no-warn-script-location --upgrade pip \
 && /opt/python/${PYTHON_VERSION}/bin/python3 -m pip install --no-warn-script-location virtualenv \
 && /opt/python/${PYTHON_VERSION}/bin/python3 -m virtualenv /py3

# Set up runner
COPY runner_dependencies.txt /runner_dependencies.txt
RUN python3 -m pip install --no-warn-script-location -r /runner_dependencies.txt

ENTRYPOINT ["python3", "/home/scripts/build_wheels.py"]
