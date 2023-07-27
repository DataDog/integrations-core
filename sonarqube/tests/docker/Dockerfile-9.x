ARG SONARQUBE_VERSION=9.9.0

FROM sonarqube:$SONARQUBE_VERSION-community

# Switch to root to install curl
USER 0

RUN apt update && apt install -y curl

# Switch back to sonarqube user as it can not run with root
USER 1000
