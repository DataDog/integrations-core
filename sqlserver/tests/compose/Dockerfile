ARG SQLSERVER_IMAGE_TAG

FROM mcr.microsoft.com/mssql/server:${SQLSERVER_IMAGE_TAG}

USER root

EXPOSE 1433

RUN apt-get update && apt-get install -y  \
	curl \
	apt-transport-https

RUN mkdir -p /var/opt/mssql/backup
WORKDIR /var/opt/mssql/backup

# the AdventureWorks test database can be used as a source of test data if needed
# RUN curl -L -o AdventureWorks2017.bak https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks2017.bak

WORKDIR /
COPY *.sh /
COPY *.sql /

RUN chmod +x setup.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT /bin/bash ./entrypoint.sh
