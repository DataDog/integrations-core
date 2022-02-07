ARG SQLSERVER_IMAGE_TAG

FROM mcr.microsoft.com/mssql/server:${SQLSERVER_IMAGE_TAG}

USER root

EXPOSE 1433
EXPOSE 2500
EXPOSE 2600

RUN apt-get update && apt-get install -y  \
	curl \
	apt-transport-https

WORKDIR /
COPY db-init.sh /
COPY entrypoint.sh /
COPY aoag_primary.sql /
COPY aoag_secondary.sql /

RUN chmod +x db-init.sh

RUN /opt/mssql/bin/mssql-conf set sqlagent.enabled true
RUN /opt/mssql/bin/mssql-conf set hadr.hadrenabled  1
RUN /opt/mssql/bin/mssql-conf set memory.memorylimitmb 2048

CMD /bin/bash ./entrypoint.sh
