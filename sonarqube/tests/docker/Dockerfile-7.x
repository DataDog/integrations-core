ARG SONARQUBE_VERSION=7.9.6

FROM sonarqube:$SONARQUBE_VERSION-community
USER root
RUN apt-get -y install curl
USER sonarqube