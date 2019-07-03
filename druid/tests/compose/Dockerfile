FROM openjdk:8-jre

ENV DRUID_HOME=/usr/local/druid
ENV DRUID_VERSION=0.15.0-incubating

RUN apt-get update \
    && apt-get install -y perl # needed for running some druid scripts

RUN mkdir -p $DRUID_HOME

RUN curl "https://archive.apache.org/dist/incubator/druid/$DRUID_VERSION/apache-druid-$DRUID_VERSION-bin.tar.gz" \
      | tar zxf - --strip-components 1 -C $DRUID_HOME

WORKDIR $DRUID_HOME
