FROM openjdk:8-jdk-alpine

ARG SPARK_VERSION
ARG HADOOP_VERSION
ARG HUDI_VERSION

# adapted from https://github.com/big-data-europe/docker-spark/blob/master/template/scala/Dockerfile
RUN apk add --no-cache bash wget

WORKDIR /usr/src/app

COPY . .

# Download Spark if not already present
RUN set -e; \
    BASE="spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}"; \
    TARBALL="${BASE}.tgz"; \
    if [ -f "${TARBALL}" ]; then \
      echo "Using cached Spark tarball"; \
    else \
      echo "Downloading Spark tarball from Apache archive"; \
      wget https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/"${TARBALL}"; \
    fi; \
    tar -xvzf "${TARBALL}" \
    && mv "${BASE}" spark \
    && rm "${TARBALL}"

RUN wget -O - https://github.com/sbt/sbt/releases/download/v1.4.1/sbt-1.4.1.tgz | gunzip | tar -x -C /usr/local

ENV PATH /usr/local/sbt/bin:${PATH}
RUN sbt update && sbt clean assembly && sbt package
