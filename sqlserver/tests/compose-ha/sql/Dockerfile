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
COPY compose-ha/sql/db-init.sh /
COPY compose-ha/sql/entrypoint.sh /
COPY compose-ha/sql/aoag_primary.sql /
COPY compose-ha/sql/aoag_secondary.sql /
COPY sql/column_statistics.sql /

RUN chmod +x db-init.sh

RUN /opt/mssql/bin/mssql-conf set sqlagent.enabled true
RUN /opt/mssql/bin/mssql-conf set hadr.hadrenabled  1
RUN /opt/mssql/bin/mssql-conf set memory.memorylimitmb 2048

CMD /bin/bash ./entrypoint.sh
