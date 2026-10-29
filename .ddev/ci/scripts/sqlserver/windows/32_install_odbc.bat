:: https://docs.microsoft.com/en-us/sql/connect/odbc/windows/system-requirements-installation-and-driver-files
:: Finding the actual URL not gated by a form was a nightmare
:: VALIDATION ONLY: fault injection for the download retry
set "INJECT=none"
if "%TARGET_ENV%"=="py3.13-windows-odbc-2019-single" set "INJECT=first"
if "%TARGET_ENV%"=="py3.13-windows-SQLOLEDB-2019-single" set "INJECT=all"
echo INJECTED: mode %INJECT% for %TARGET_ENV%
powershell -NoProfile -Command "Get-OdbcDriver | Where-Object Name -like '*SQL Server*' | Format-Table Name,Platform -AutoSize"
:: Retry the download and fail setup on errors, otherwise a transient failure leaves the driver missing and every test errors
powershell -NoProfile -Command "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'; $n = 0; foreach ($delay in 5, 10, 20, 40, 0) { $n++; $url = 'https://download.microsoft.com/download/4/f/e/4fed6f4b-dc42-4255-b4b4-70f8e2a35a63/en-US/18.3.2.1/x64/msodbcsql.msi'; if ($env:INJECT -eq 'all' -or ($env:INJECT -eq 'first' -and $n -eq 1)) { $url = 'https://unreachable.invalid/msodbcsql.msi' }; Write-Host ('Download attempt ' + $n + ' at ' + (Get-Date -Format 'HH:mm:ss') + ': ' + $url); try { Invoke-WebRequest $url -OutFile msodbcsql.msi; exit 0 } catch { Write-Host ('Download failed: ' + $_); if ($delay -eq 0) { exit 1 }; Start-Sleep -Seconds $delay } }"
if errorlevel 1 exit /b 1
msiexec /quiet /passive /qn /i msodbcsql.msi IACCEPTMSODBCSQLLICENSETERMS=YES
if %errorlevel% neq 0 if %errorlevel% neq 3010 exit /b %errorlevel%
echo INJECTED: msiexec exit code %errorlevel%
powershell -NoProfile -Command "Get-OdbcDriver | Where-Object Name -like '*SQL Server*' | Format-Table Name,Platform -AutoSize"
del msodbcsql.msi
