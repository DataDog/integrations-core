powershell -Command "Invoke-WebRequest https://download.microsoft.com/download/F/3/C/F3C64941-22A0-47E9-BC9B-1A19B4CA3E88/ENU/x64/sqlncli.msi -OutFile sqlncli.msi"
msiexec /quiet /passive /qn /i sqlncli.msi IACCEPTSQLNCLILICENSETERMS=YES
del sqlncli.msi
