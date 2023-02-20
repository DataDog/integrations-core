ARG SQLSERVER_BASE_IMAGE

FROM $SQLSERVER_BASE_IMAGE

COPY setup.sql setup.sql
COPY sqlserver-entrypoint.ps1 sqlserver-entrypoint.ps1
CMD powershell -F .\sqlserver-entrypoint.ps1
