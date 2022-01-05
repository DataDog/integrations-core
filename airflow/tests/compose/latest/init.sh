#!/usr/bin/env bash

# Wait for db
while ! nc $DB__HOST $DB__PORT; do
  >&2 echo "Waiting for postgres to be up and running..."
  sleep 1
done

export PGPASSWORD=${DB__PASSWORD}
export AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg2://${DB__USERNAME}:${DB__PASSWORD}@${DB__HOST}:${DB__PORT}/${DB__NAME}"

# check on db if admin exists
echo "First psql connection..."
psql -h ${DB__HOST} -p ${DB__PORT} -U ${DB__USERNAME} ${DB__NAME} -t

# Initialize db
echo "Airflow database upgrade"
airflow db upgrade

echo "Creating admin user.."
airflow users create -r Admin -u "$SECURITY__ADMIN_USERNAME" -e "$SECURITY__ADMIN_EMAIL" -f "$SECURITY__ADMIN_FIRSTNAME" -l "$SECURITY__ADMIN_LASTNAME" -p "$SECURITY__ADMIN_PASSWORD"

# Run scheduler 
airflow scheduler &

# Run webserver
exec airflow webserver
