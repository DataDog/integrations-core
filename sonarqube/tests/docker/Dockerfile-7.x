ARG SONARQUBE_VERSION=7.9.4

FROM sonarqube:$SONARQUBE_VERSION-community
USER root
RUN apt-get update && apt-get -y install curl
USER sonarqube