ARG BASE_IMAGE=quay.io/pypa/manylinux2014_x86_64
FROM ${BASE_IMAGE}

ARG PYTHON_MAJOR

ENV IBM_MQ_VERSION="9.2.4.0"
ENV IBM_MQ_SHA256="d0d583eba72daf20b3762976f8831c2e23150ace90509520e12f8cda5b5bdb49"
ENV KRB5_VERSION="1.20.1"
ENV KRB5_SHA256="704aed49b19eb5a7178b34b2873620ec299db08752d6a8574f95d41879ab8851"
ENV OPENSSL_VERSION="3.0.12"
ENV OPENSSL_SHA256="f93c9e8edde5e9166119de31755fc87b4aa34863662f67ddfcba14d0b6b69b61"

ENV PATH="/opt/python/cp${PYTHON_MAJOR}-cp${PYTHON_MAJOR}/bin:${PATH}"

# MQ Client library required by pymqi
RUN mkdir -p /opt/mqm \
 && curl "https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/${IBM_MQ_VERSION}-IBM-MQC-Redist-LinuxX64.tar.gz" -o /tmp/mq_client.tar.gz \
 && echo "${IBM_MQ_SHA256}  /tmp/mq_client.tar.gz" | sha256sum --check \
 && tar -C /opt/mqm -xf /tmp/mq_client.tar.gz \
 && rm -rf /tmp/mq_client.tar.gz

# krb5 for dependencies that require kerberos support
RUN curl "https://kerberos.org/dist/krb5/1.20/krb5-${KRB5_VERSION}.tar.gz" -o /tmp/krb5.tar.gz \
 && echo "${KRB5_SHA256}  /tmp/krb5.tar.gz" | sha256sum --check \
 && tar -C /tmp -xf /tmp/krb5.tar.gz \
 && cd /tmp/krb5-${KRB5_VERSION}/src \
 && ./configure --without-keyutils --without-system-verto --without-libedit --disable-static \
 && make \
 && make install \
 && cd - \
 && rm -rf /tmp/krb5-${KRB5_VERSION}/src \
 && rm -rf /tmp/krb5.tar.gz

# openssl
RUN yum install -y perl-IPC-Cmd
RUN curl "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz" -o /tmp/openssl.tar.gz \
 && tar -C /tmp -xf /tmp/openssl.tar.gz \
 && echo "${OPENSSL_SHA256}  /tmp/openssl.tar.gz" | sha256sum --check \
 && cd /tmp/openssl-${OPENSSL_VERSION} \
 && ./config -Wl,-Bsymbolic-functions -fPIC shared no-ssl2 no-ssl3 \
 && make \
 && make install \
 && rm -rf /tmp/openssl-${OPENSSL_VERSION} \
 && rm -rf /tmp/openssl.tar.gz


CMD ["python", "-m", "pip", "install", "-r", "/home/requirements.in"]
