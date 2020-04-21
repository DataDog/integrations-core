call "$env:DDEV_SCRIPTS_PATH\common.bat"

:: Install with TCP/IP enabled, see: https://chocolatey.org/packages/sql-server-2017
Retry-Command -ScriptBlock {
    choco install sql-server-2017 --params="'/TCPENABLED:1'"
} -Maximum 5

:: Set password
sqlcmd -Q "ALTER LOGIN sa with PASSWORD = 'Password12!';ALTER LOGIN sa ENABLE;"

:: Enable port
powershell -Command "stop-service MSSQLSERVER"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpdynamicports -value ''"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpport -value 1433"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\' -name LoginMode -value 2"
powershell -Command "start-service MSSQLSERVER"
