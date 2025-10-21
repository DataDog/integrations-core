FROM openjdk:8-jdk-alpine

ARG SPARK_VERSION
ARG HADOOP_VERSION
ARG HUDI_VERSION

# adapted from https://github.com/big-data-europe/docker-spark/blob/master/template/scala/Dockerfile
RUN apk add --no-cache curl bash

# Copy pre-downloaded Spark tarball if available (from GHA cache), otherwise download it
COPY spark-*-bin-hadoop*.tgz* ./spark-download/ 2>/dev/null || mkdir -p ./spark-download
RUN if [ -f ./spark-download/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz ]; then \
      echo "Using cached Spark tarball from build context"; \
      mv ./spark-download/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz .; \
    else \
      echo "Downloading Spark tarball from Apache archive"; \
      wget https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz; \
    fi \
    && rm -rf ./spark-download \
    && tar -xvzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} spark \
    && rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

RUN wget -O - https://github.com/sbt/sbt/releases/download/v1.4.1/sbt-1.4.1.tgz | gunzip | tar -x -C /usr/local

ENV PATH /usr/local/sbt/bin:${PATH}

COPY . /usr/src/app/
RUN cd /usr/src/app && sbt update && sbt clean assembly && sbt package
