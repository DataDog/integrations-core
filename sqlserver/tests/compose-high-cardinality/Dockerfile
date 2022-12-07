ARG SQLSERVER_IMAGE_TAG

FROM mcr.microsoft.com/mssql/server:${SQLSERVER_IMAGE_TAG}

USER root

EXPOSE 1433

RUN apt-get update && apt-get install -y  \
	curl \
	apt-transport-https

RUN mkdir -p /var/opt/mssql/backup
WORKDIR /var/opt/mssql/backup

WORKDIR /
COPY *.sh /
COPY *.sql /

RUN chmod +x setup.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT /bin/bash ./entrypoint.sh
