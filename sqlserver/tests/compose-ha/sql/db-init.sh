#wait for the SQL Server to come up
SLEEP_TIME=$INIT_WAIT
SQL_SCRIPT=$INIT_SCRIPT
echo "sleeping for ${SLEEP_TIME} seconds ..."
sleep ${SLEEP_TIME}

echo "#######    running set up script ${SQL_SCRIPT}   #######"

#run the setup script to create the DB and the schema in the DB
#if this is the primary node, remove the certificate files.
#if docker containers are stopped, but volumes are not removed, this certificate will be persisted
if [ "$SQL_SCRIPT" = "aoag_primary.sql" ]
then
    rm /var/opt/mssql/shared/aoag_certificate.key 2> /dev/null
    rm /var/opt/mssql/shared/aoag_certificate.cert 2> /dev/null
fi

# Define both potential sqlcmd paths
SQLCMD_PATH_18="/opt/mssql-tools18/bin/sqlcmd"
SQLCMD_PATH="/opt/mssql-tools/bin/sqlcmd"

# Check if sqlcmd exists in the first path
if [ -x "$SQLCMD_PATH_18" ]; then
    SQLCMD_EXEC="$SQLCMD_PATH_18"
elif [ -x "$SQLCMD_PATH" ]; then
    SQLCMD_EXEC="$SQLCMD_PATH"
else
    echo "sqlcmd not found in either path."
    exit 1
fi

#use the SA password from the environment variable
$SQLCMD_EXEC -C -N -S localhost -U sa -P $SA_PASSWORD -d master -i $SQL_SCRIPT

echo "#######      AOAG script execution completed     #######"