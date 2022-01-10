#!/bin/sh
mysql -u root -pmysqlpsswd < /var/backups/alldb_backup.sql
