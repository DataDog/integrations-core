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

# Run the setup script to create the DB.
# Do this in a loop because the timing for when the SQL instance is ready is indeterminate.
for i in {1..120};
do
    $SQLCMD_EXEC -C -N -S localhost -U sa -P $SA_PASSWORD -d master -q "SELECT count(*) from sys.databases" -b
    if [ $? -eq 0 ]
    then
        echo "INFO: sqlserver is running."
        break
    else
        echo "INFO: sqlserver not running yet. Retrying in 1 second."
        sleep 1
    fi
done

$SQLCMD_EXEC -C -N -S localhost -U sa -P $SA_PASSWORD -d master -i setup.sql -b
if [ $? -eq 0 ]
then
    echo "INFO: setup.sql completed."
else
    echo "ERROR: setup.sql failed."
    exit 1
fi
