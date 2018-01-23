cat /docker-entrypoint-initdb.d/02_datadog_test.psql | PGPASSWORD=datadog psql -h localhost -p 5432 datadog_test -U datadog
cat /docker-entrypoint-initdb.d/03_dogs.psql | PGPASSWORD=datadog psql -h localhost -p 5432 dogs -U datadog
