:: Set password
sqlcmd -Q "ALTER LOGIN sa with PASSWORD = 'Password12!';ALTER LOGIN sa ENABLE;"
sqlcmd -Q "CREATE LOGIN datadog WITH PASSWORD = 'Hey-there-datadog123!';"
sqlcmd -Q "CREATE USER datadog FOR LOGIN datadog;"
sqlcmd -Q "GRANT VIEW SERVER STATE to datadog;"
sqlcmd -Q "GRANT CONNECT ANY DATABASE to datadog;"
sqlcmd -Q "GRANT VIEW ANY DEFINITION to datadog;"


:: Enable port
powershell -Command "stop-service MSSQLSERVER"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpdynamicports -value ''"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpport -value 1433"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\' -name LoginMode -value 2"
powershell -Command "start-service MSSQLSERVER"
