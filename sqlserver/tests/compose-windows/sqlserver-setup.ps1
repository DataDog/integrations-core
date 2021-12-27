#### enable tcp
# https://docs.microsoft.com/en-us/sql/powershell/how-to-enable-tcp-sqlps?view=sql-server-ver15
[reflection.assembly]::LoadWithPartialName("Microsoft.SqlServer.SqlWmiManagement")
$wmi = New-Object 'Microsoft.SqlServer.Management.Smo.Wmi.ManagedComputer' localhost
$tcp = $wmi.ServerInstances['MSSQLSERVER'].ServerProtocols['Tcp']
$tcp.IsEnabled = $true
$tcp.Alter()

### set login mode https://www.mode19.net/posts/changesqlauthmodewithps/
[System.Reflection.Assembly]::LoadWithPartialName('Microsoft.SqlServer.SMO')
$smo = New-Object 'Microsoft.SqlServer.Management.Smo.Server' localhost
$smo.Settings.LoginMode = "Mixed"
$smo.Alter()

Restart-Service -Name MSSQLSERVER -Force

sqlcmd -Q "ALTER login sa ENABLE;"
sqlcmd -Q "ALTER login sa WITH PASSWORD = 'Password123';"
