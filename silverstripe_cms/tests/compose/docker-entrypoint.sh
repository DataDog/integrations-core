#!/bin/bash
set -e

# Start MySQL
service mysql start

# Wait for MySQL to be ready
while ! mysqladmin ping -h"localhost" --silent; do
    echo 'Waiting for MySQL to be ready...'
    sleep 1
done

# Change to the Silverstripe directory
cd /var/www/html/silverstripe

# Run Silverstripe database build
vendor/bin/sake dev/build flush=1

# Start Apache in the foreground
apache2ctl -D FOREGROUND