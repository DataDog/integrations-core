#run the setup script to create the DB
#do this in a loop because the timing for when the SQL instance is ready is indeterminate
for i in {1..120};
do
    /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P $SA_PASSWORD -d master -i setup.sql
    if [ $? -eq 0 ]
    then
        echo "setup.sql completed"
        break
    else
        echo "not ready yet..."
        sleep 1
    fi
done
