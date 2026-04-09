# First build the Scala application
FROM amazoncorretto:8-alpine-jdk AS builder

ARG SPARK_VERSION
ARG HUDI_VERSION

RUN apk add --no-cache bash \
      && wget -O - https://github.com/sbt/sbt/releases/download/v1.9.8/sbt-1.9.8.tgz | gunzip | tar -x -C /usr/local

ENV PATH=/usr/local/sbt/bin:${PATH}

COPY . /usr/src/app/
RUN cd /usr/src/app && sbt update && sbt clean assembly && sbt package

# Then setup the runtime environment
FROM apache/spark:v3.2.4

USER root

ARG HUDI_VERSION
ARG SPARK_VERSION

RUN $SPARK_HOME/bin/spark-submit \
    --packages "org.apache.hudi:hudi-spark3-bundle_2.12:${HUDI_VERSION},org.apache.spark:spark-avro_2.12:${SPARK_VERSION}" \
    --class placeholder /dev/null 2>&1 || true

COPY --from=builder /usr/src/app/target/scala-2.12/app_2.12-0.1.0-SNAPSHOT.jar /usr/src/app/target/scala-2.12/app_2.12-0.1.0-SNAPSHOT.jar
