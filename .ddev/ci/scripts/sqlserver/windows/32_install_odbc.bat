:: https://docs.microsoft.com/en-us/sql/connect/odbc/windows/system-requirements-installation-and-driver-files
:: Finding the actual URL not gated by a form was a nightmare
:: Retry the download and fail setup on errors, otherwise a transient failure leaves the driver missing and every test errors
powershell -NoProfile -Command "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'; foreach ($delay in 5, 10, 20, 40, 0) { try { Invoke-WebRequest https://download.microsoft.com/download/4/f/e/4fed6f4b-dc42-4255-b4b4-70f8e2a35a63/en-US/18.3.2.1/x64/msodbcsql.msi -OutFile msodbcsql.msi; exit 0 } catch { Write-Host ('Download failed: ' + $_); if ($delay -eq 0) { exit 1 }; Start-Sleep -Seconds $delay } }"
if errorlevel 1 exit /b 1
msiexec /quiet /passive /qn /i msodbcsql.msi IACCEPTMSODBCSQLLICENSETERMS=YES
if %errorlevel% neq 0 if %errorlevel% neq 3010 exit /b %errorlevel%
del msodbcsql.msi
