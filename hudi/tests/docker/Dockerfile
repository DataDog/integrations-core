FROM openjdk:8-jdk-alpine

ARG SPARK_VERSION
ARG HADOOP_VERSION
ARG HUDI_VERSION

# adapted from https://github.com/big-data-europe/docker-spark/blob/master/template/scala/Dockerfile
RUN apk add --no-cache curl bash \
      && wget https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
      && tar -xvzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
      && mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} spark \
      && rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
      && cd /

RUN wget -O - https://github.com/sbt/sbt/releases/download/v1.4.1/sbt-1.4.1.tgz | gunzip | tar -x -C /usr/local

ENV PATH /usr/local/sbt/bin:${PATH}

COPY . /usr/src/app/
RUN cd /usr/src/app && sbt update && sbt clean assembly && sbt package
