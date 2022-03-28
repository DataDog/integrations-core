ARG SQLSERVER_BASE_IMAGE

FROM $SQLSERVER_BASE_IMAGE

COPY sqlserver-setup.ps1 sqlserver-setup.ps1
RUN powershell -F .\sqlserver-setup.ps1

COPY setup.sql setup.sql
RUN sqlcmd -d master -i setup.sql -b -f 65001

COPY sqlserver-entrypoint.ps1 sqlserver-entrypoint.ps1
CMD powershell -F .\sqlserver-entrypoint.ps1
