ARG HAZELCAST_VERSION
FROM hazelcast/hazelcast:${HAZELCAST_VERSION}

ARG HAZELCAST_VERSION
ARG LOG4J2_VERSION=2.16.0

COPY log4j2.properties /opt/hazelcast/config/log4j2.properties

# in the hazelcast 4 dev env we need to download log4j too
RUN if [ ${HAZELCAST_VERSION} = 4.0.1 ] ; then \
    apk update && \
    apk add curl && \
    mkdir /tmp/log4j2 && \
    cd /tmp/log4j2 && \
    curl -LO https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/${LOG4J2_VERSION}/log4j-api-${LOG4J2_VERSION}.jar && \
    curl -LO https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/${LOG4J2_VERSION}/log4j-core-${LOG4J2_VERSION}.jar \
    ; fi
