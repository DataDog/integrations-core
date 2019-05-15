FROM quantumobject/docker-cacti
COPY bin/startup.sh bin/startup.sh
CMD mysql -u root -D cacti -e "CREATE USER 'cactiuser'@'localhost' IDENTIFIED BY 'cactipass';"
CMD mysql -u root -D cacti -e "GRANT ALL PRIVILEGES ON *.* TO 'cactiuser'@'localhost'  WITH GRANT OPTION;"
CMD mysql -u root -D cacti -e "CREATE USER 'cactiuser'@'%' IDENTIFIED BY 'cactipass';"
