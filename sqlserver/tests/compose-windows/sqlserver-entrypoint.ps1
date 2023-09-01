echo "INFO: waiting for SQL Server to come up"
(Get-Service MSSQLSERVER).WaitForStatus('Running')

echo "INFO: enabling TCP"
# https://docs.microsoft.com/en-us/sql/powershell/how-to-enable-tcp-sqlps?view=sql-server-ver15
[reflection.assembly]::LoadWithPartialName("Microsoft.SqlServer.SqlWmiManagement")
$wmi = New-Object 'Microsoft.SqlServer.Management.Smo.Wmi.ManagedComputer' localhost
$tcp = $wmi.ServerInstances['MSSQLSERVER'].ServerProtocols['Tcp']
$tcp.IsEnabled = $true
$tcp.Alter()

echo "INFO: setting LoginMode=Mixed"
### https://www.mode19.net/posts/changesqlauthmodewithps/
[System.Reflection.Assembly]::LoadWithPartialName('Microsoft.SqlServer.SMO')
$smo = New-Object 'Microsoft.SqlServer.Management.Smo.Server' localhost
$smo.Settings.LoginMode = "Mixed"
$smo.Alter()

echo "INFO: running setup.sql for integration tests"
sqlcmd -d master -i setup.sql -b -f 65001
if (-Not $?) {
    throw "ERROR: setup.sql failed"
}
echo "INFO: setup.sql completed"

echo "INFO: restarting MSSQLSERVER"
Restart-Service -Name MSSQLSERVER
(Get-Service MSSQLSERVER).WaitForStatus('Running')
echo "INFO: MSSQLSERVER running."

echo "INFO: Container initialization complete."
ping -t localhost | out-null
