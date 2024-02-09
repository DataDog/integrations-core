FROM maven:3-eclipse-temurin-11
ARG TOMCAT_VERSION

COPY app /tmp/app
RUN cd /tmp/app && mvn package "-Dtomcat.version=${TOMCAT_VERSION}"
ENTRYPOINT ["/tmp/app/target/bin/webapp"]
