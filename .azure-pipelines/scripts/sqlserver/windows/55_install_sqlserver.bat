:: Install with TCP/IP enabled, see: https://chocolatey.org/packages/sql-server-2017

@echo off
set TRIES=3
set INTERVAL=10

:retry

choco install sql-server-2017 --params="'/TCPENABLED:1'"

if %ERRORLEVEL% neq 0 (
   set /A TRIES=%TRIES%-1
   if %TRIES% gtr 1 (
       echo Failed, retrying in %INTERVAL% seconds...
       timeout /t %INTERVAL%
       goto retry
   ) else (
       echo Failed, aborting
       exit /b 1
   )
)

echo Success

:: Set password
sqlcmd -Q "ALTER LOGIN sa with PASSWORD = 'Password12!';ALTER LOGIN sa ENABLE;"

:: Enable port
powershell -Command "stop-service MSSQLSERVER"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpdynamicports -value ''"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\supersocketnetlib\tcp\ipall' -name tcpport -value 1433"
powershell -Command "set-itemproperty -path 'HKLM:\software\microsoft\microsoft sql server\mssql14.MSSQLSERVER\mssqlserver\' -name LoginMode -value 2"
powershell -Command "start-service MSSQLSERVER"
