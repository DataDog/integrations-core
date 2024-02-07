:: https://docs.microsoft.com/en-us/sql/connect/odbc/windows/system-requirements-installation-and-driver-files
:: Finding the actual URL not gated by a form was a nightmare
powershell -Command "Invoke-WebRequest https://download.microsoft.com/download/4/f/e/4fed6f4b-dc42-4255-b4b4-70f8e2a35a63/en-US/18.3.2.1/x64/msodbcsql.msi -OutFile msodbcsql.msi"
msiexec /quiet /passive /qn /i msodbcsql.msi IACCEPTMSODBCSQLLICENSETERMS=YES
del msodbcsql.msi
