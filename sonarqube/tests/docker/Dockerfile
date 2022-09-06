ARG SONARQUBE_VERSION

FROM sonarqube:$SONARQUBE_VERSION-community
USER root
RUN apt-get update && apt-get -y install curl