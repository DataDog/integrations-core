ARG SQLSERVER_BASE_IMAGE

FROM $SQLSERVER_BASE_IMAGE

COPY compose-windows/setup.sql setup.sql
COPY sql/column_statistics.sql column_statistics.sql
COPY compose-windows/sqlserver-entrypoint.ps1 sqlserver-entrypoint.ps1
CMD powershell -F .\sqlserver-entrypoint.ps1
