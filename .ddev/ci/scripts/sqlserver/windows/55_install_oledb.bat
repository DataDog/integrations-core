:: :: https://learn.microsoft.com/en-us/sql/connect/oledb/download-oledb-driver-for-sql-server?view=sql-server-ver16
:: Finding the actual URL not gated by a form was a nightmare
powershell -Command "Invoke-WebRequest https://download.microsoft.com/download/f/1/3/f13ce329-0835-44e7-b110-44decd29b0ad/en-US/19.3.2.0/x64/msoledbsql.msi -OutFile msoledbsql.msi"
msiexec /quiet /passive /qn /i msoledbsql.msi IACCEPTMSODBCSQLLICENSETERMS=YES
del msoledbsql.msi
