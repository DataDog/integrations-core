ARG HAZELCAST_VERSION
FROM hazelcast/hazelcast:${HAZELCAST_VERSION}

ARG LOG4J2_VERSION=2.13.2

RUN apk update && \
    apk add curl && \
    mkdir /tmp/log4j2 && \
    cd /tmp/log4j2 && \
    curl -LO https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/${LOG4J2_VERSION}/log4j-api-${LOG4J2_VERSION}.jar && \
    curl -LO https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/${LOG4J2_VERSION}/log4j-core-${LOG4J2_VERSION}.jar && \
    cd -
