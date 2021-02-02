FROM quantumobject/docker-cacti:latest

# username and password is admin/Admin23@
COPY alldb_backup.sql /var/backups/
COPY rra.tar.gz /var/backups/

RUN chown www-data:www-data /var/www/html/cacti/rra
RUN chown -R www-data:www-data /var/www/html/cacti/rra
