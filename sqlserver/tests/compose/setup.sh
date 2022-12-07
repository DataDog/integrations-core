#run the setup script to create the DB
#do this in a loop because the timing for when the SQL instance is ready is indeterminate
for i in {1..120};
do
    /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P $SA_PASSWORD -d master -i is_running.sql -b
    if [ $? -eq 0 ]
    then
        echo "INFO: sqlserver is running."
        break
    else
        echo "INFO: sqlserver not running yet. Retrying in 1 second."
        sleep 1
    fi
done

/opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P $SA_PASSWORD -d master -i setup.sql -b
if [ $? -eq 0 ]
then
    echo "INFO: setup.sql completed."
    exit 0
else
    echo "ERROR: setup.sql failed."
    exit 1
fi
