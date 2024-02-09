ARG BASE_IMAGE=quay.io/pypa/manylinux2014_aarch64
FROM ${BASE_IMAGE}

# Choose Python version by putting it in path
ENV PATH="/opt/python/cp311-cp311/bin:${PATH}"

# Script for the common task of fetching a source tarball, compiling and installing it
COPY install-from-source.sh /

ENV CFLAGS="-O2"
# Auditwheel will only set RPATH's for copied libs if an existing RPATH is found,
# so we may as well set it to origin here anyway.
ENV LDFLAGS="-Wl,-rpath,'\$\$ORIGIN'"

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

# Set up Python3
RUN python3 -m pip install --no-warn-script-location --upgrade pip \
 && python3 -m pip install --no-warn-script-location virtualenv \
 && python3 -m virtualenv /py3

# krb5 for dependencies that require kerberos support
RUN \
 DOWNLOAD_URL="https://kerberos.org/dist/krb5/1.20/krb5-{{version}}.tar.gz" \
 VERSION="1.20.1" \
 SHA256="704aed49b19eb5a7178b34b2873620ec299db08752d6a8574f95d41879ab8851" \
 RELATIVE_PATH="krb5-{{version}}/src" \
 bash install-from-source.sh --without-keyutils --without-system-verto --without-libedit --disable-static

# Set up runner
COPY runner_dependencies.txt /runner_dependencies.txt
RUN python3 -m pip install --no-warn-script-location -r /runner_dependencies.txt
RUN python3 -c 'import platform; print(platform.machine())'

COPY build_script.sh /build_script.sh
ENV DD_BUILD_COMMAND="bash /build_script.sh"

ENTRYPOINT ["python3", "/home/scripts/build_wheels.py"]
