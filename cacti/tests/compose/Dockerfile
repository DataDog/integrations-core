FROM quantumobject/docker-cacti
RUN mysql -u root -D cacti -e "CREATE USER 'cactiuser'@'localhost' IDENTIFIED BY 'cactipass';"
RUN mysql -u root -D cacti -e "GRANT ALL PRIVILEGES ON *.* TO 'cactiuser'@'localhost'  WITH GRANT OPTION;"
RUN mysql -u root -D cacti -e "CREATE USER 'cactiuser'@'%' IDENTIFIED BY 'cactipass';"
RUN mysql -u root -D cacti -e "GRANT ALL PRIVILEGES ON *.* TO 'cactiuser'@'%' WITH GRANT OPTION;"
