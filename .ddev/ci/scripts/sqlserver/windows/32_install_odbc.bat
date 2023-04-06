:: https://docs.microsoft.com/en-us/sql/connect/odbc/windows/system-requirements-installation-and-driver-files
:: Finding the actual URL not gated by a form was a nightmare
powershell -Command "Invoke-WebRequest https://download.microsoft.com/download/c/5/4/c54c2bf1-87d0-4f6f-b837-b78d34d4d28a/en-US/18.2.1.1/x64/msodbcsql.msi -OutFile msodbcsql.msi"
msiexec /quiet /passive /qn /i msodbcsql.msi IACCEPTMSODBCSQLLICENSETERMS=YES
del msodbcsql.msi
