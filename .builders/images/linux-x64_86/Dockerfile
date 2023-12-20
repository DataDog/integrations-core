ARG BASE_IMAGE=quay.io/pypa/manylinux2014_x86_64
FROM ${BASE_IMAGE}

ARG PYTHON_MAJOR

ENV IBM_MQ_VERSION="9.2.4.0"
ENV IBM_MQ_SHA256="d0d583eba72daf20b3762976f8831c2e23150ace90509520e12f8cda5b5bdb49"

ENV PATH="/opt/python/cp${PYTHON_MAJOR}-cp${PYTHON_MAJOR}/bin:${PATH}"

RUN mkdir -p /opt/mqm \
    && curl "https://s3.amazonaws.com/dd-agent-omnibus/ibm-mq-backup/${IBM_MQ_VERSION}-IBM-MQC-Redist-LinuxX64.tar.gz" -o /tmp/mq_client.tar.gz \
    && echo "${IBM_MQ_SHA256}  /tmp/mq_client.tar.gz" | sha256sum --check \
    && tar -C /opt/mqm -xf /tmp/mq_client.tar.gz \
    && rm -rf /tmp/mq_client.tar.gz

CMD ["python", "-m", "pip", "install", "-r", "/home/requirements.in"]
