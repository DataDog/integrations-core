FROM mcr.microsoft.com/mssql/server:2017-latest-ubuntu

EXPOSE 1433

RUN apt-get update && apt-get install -y  \
	curl \
	apt-transport-https

RUN mkdir -p /var/opt/mssql/backup
WORKDIR /var/opt/mssql/backup

RUN curl -L -o AdventureWorks2017.bak https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks2017.bak

WORKDIR /
COPY setup.* /
COPY entrypoint.sh /

RUN chmod +x setup.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT /bin/bash ./entrypoint.sh
