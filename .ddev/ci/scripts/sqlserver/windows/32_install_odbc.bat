:: https://docs.microsoft.com/en-us/sql/connect/odbc/windows/system-requirements-installation-and-driver-files
:: Finding the actual URL not gated by a form was a nightmare
powershell -Command "Invoke-WebRequest https://download.microsoft.com/download/E/6/B/E6BFDC7A-5BCD-4C51-9912-635646DA801E/en-US/17.5.2.1/x64/msodbcsql.msi -OutFile msodbcsql.msi"
msiexec /quiet /passive /qn /i msodbcsql.msi IACCEPTMSODBCSQLLICENSETERMS=YES
del msodbcsql.msi
