ARG HAZELCAST_VERSION
FROM hazelcast/hazelcast:${HAZELCAST_VERSION}


ARG LOG4J2_VERSION

RUN apk update && \
    apk add curl tar && \
    curl -LO https://downloads.apache.org/logging/log4j/${LOG4J2_VERSION}/apache-log4j-${LOG4J2_VERSION}-bin.tar.gz && \
    tar -xzf apache-log4j-${LOG4J2_VERSION}-bin.tar.gz && \
    mkdir /tmp/log4j2 && \
    mv apache-log4j-${LOG4J2_VERSION}-bin/log4j-api-${LOG4J2_VERSION}.jar /tmp/log4j2/ && \
    mv apache-log4j-${LOG4J2_VERSION}-bin/log4j-core-${LOG4J2_VERSION}.jar /tmp/log4j2/
