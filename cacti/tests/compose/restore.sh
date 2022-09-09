#!/bin/bash

# script to restore a cacti backup 
# ./restore.sh <backup file>

# check if argument has dependencies
if [ -z $1 ]; then
echo "restore.sh <backupfilename>"
	exit 2
fi

# create temp workspace
echo "$(date +%F_%R) [Restore] Prepping workspace for restore."
rm -rf /tmp/restore
mkdir /tmp/restore

# preflight checks
# database availablity check - http://stackoverflow.com/questions/4922943/test-from-shell-script-if-remote-tcp-port-is-open
while ! timeout 1 bash -c 'cat < /dev/null > /dev/tcp/${DB_HOST}/${DB_PORT}'; do sleep 3; done
echo "$(date +%F_%R) [Restore] Database check ok! - DB located at ${DB_HOST}:${DB_PORT}."

# unzip backup file to temp directory
echo "$(date +%F_%R) [Restore] Decompressing backup file $1."
tar -xzf $1 -C /tmp/restore

# cleanup active Cacti /rra folder
echo "$(date +%F_%R) [Restore] Cleaning up current active instance."
rm -rf /cacti/*
rm -rf /spine/*

# move Cacti directory to /cacti
echo "$(date +%F_%R) [Restore] Moving Cacti files..."
mv -f /tmp/restore/cacti/* /cacti/

# move Spine directory to /spine
echo "$(date +%F_%R) [Restore] Moving Spine files..."
mv -f /tmp/restore/spine/* /spine/

# fixing permissions
echo "$(date +%F_%R) [Restore] Setting cacti file permissions."
chown -R apache.apache /cacti/resource/
chown -R apache.apache /cacti/cache/
chown -R apache.apache /cacti/log/
chown -R apache.apache /cacti/scripts/
chown -R apache.apache /cacti/rra/

# fresh install db merge
echo "$(date +%F_%R) [Restore] Merging cactibackup.sql file to database."
mysql -h ${DB_HOST} -u${DB_USER} -p${DB_PASS} ${DB_NAME} < /cacti/cactibackup.sql

# be nice and clean up
echo "$(date +%F_%R) [Restore] Removing temp files."
rm -rf /tmp/restore

# write note in cacti.log that a restore is complete
echo "$(date +%F_%R) [Restore] Cacti Restore $1 Complete!" >> /cacti/log/cacti.log

echo "$(date +%F_%R) [Restore] Restore from $1 Complete!"
