ARG HAZELCAST_VERSION
FROM hazelcast/hazelcast:${HAZELCAST_VERSION}

RUN apk update && \
    apk add curl tar && \
    curl -LO https://downloads.apache.org/logging/log4j/2.13.1/apache-log4j-2.13.1-bin.tar.gz && \
    tar -xzf apache-log4j-2.13.1-bin.tar.gz && \
    mkdir /tmp/log4j2 && \
    mv apache-log4j-2.13.1-bin/log4j-api-2.13.1.jar /tmp/log4j2/ && \
    mv apache-log4j-2.13.1-bin/log4j-core-2.13.1.jar /tmp/log4j2/
