FROM openjdk:8-jre

ENV DRUID_HOME=/usr/local/druid

RUN mkdir -p $DRUID_HOME

ENV DRUID_VERSION=0.15.0-incubating
ENV ZOOKEEPR_VERSION=3.4.11

RUN curl "https://www-eu.apache.org/dist/incubator/druid/$DRUID_VERSION/apache-druid-$DRUID_VERSION-bin.tar.gz" \
      | tar zxf - --strip-components 1 -C $DRUID_HOME

RUN mkdir -p $DRUID_HOME/zk
RUN curl "https://archive.apache.org/dist/zookeeper/zookeeper-$ZOOKEEPR_VERSION/zookeeper-$ZOOKEEPR_VERSION.tar.gz" \
      | tar zxf - --strip-components 1 -C $DRUID_HOME/zk

RUN apt-get update
RUN apt-get install -y perl

WORKDIR $DRUID_HOME

EXPOSE 8081-8083 8090

CMD ["bin/run-druid", "coordinator-overlord", "conf/druid/single-server/micro-quickstart"]
