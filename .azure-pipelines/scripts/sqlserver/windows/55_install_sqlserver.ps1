Write-Output "$env:DDEV_SCRIPTS_PATH\common.ps1"

. "$env:DDEV_SCRIPTS_PATH\common.ps1"

:: Install with TCP/IP enabled, see: https://chocolatey.org/packages/sql-server-2017
Retry-Command -ScriptBlock {
    choco install sql-server-2017 --params="'/TCPENABLED:1'"
} -Maximum 5

:: Set password
sqlcmd -Q "ALTER LOGIN sa with PASSWORD = 'Password12!';ALTER LOGIN sa ENABLE;"

:: Enable port
stop-service MSSQLSERVER
set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpdynamicports -value ''
set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpport -value 1433
set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\' -name LoginMode -value 2
start-service MSSQLSERVER
