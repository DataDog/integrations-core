#start import script in background, then SQL Server
/opt/mssql/bin/mssql-conf set sqlagent.enabled true
/setup.sh & /opt/mssql/bin/sqlservr

