#FROM mcr.microsoft.com/mssql/rhel/server:2019-CU4-rhel-8
FROM mcr.microsoft.com/mssql/server:2017-latest-ubuntu

EXPOSE 1433
EXPOSE 2500
EXPOSE 2600

RUN apt-get update && apt-get install -y  \
	curl \
	apt-transport-https


#RUN apt-get install unixodbc unixodbc-dev freetds-dev freetds-bin tdsodbc

WORKDIR /
COPY db-init.sh /
COPY entrypoint.sh /
COPY aoag_primary.sql /
COPY aoag_secondary.sql /

#COPY odbc.ini /opt/datadog-agent/embedded/etc
#COPY odbcinst.ini /opt/datadog-agent/embedded/etc

#USER root
RUN chmod +x db-init.sh

RUN /opt/mssql/bin/mssql-conf set sqlagent.enabled true
RUN /opt/mssql/bin/mssql-conf set hadr.hadrenabled  1
RUN /opt/mssql/bin/mssql-conf set memory.memorylimitmb 2048

CMD /bin/bash ./entrypoint.sh
