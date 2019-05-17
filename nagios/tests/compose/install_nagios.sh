#! /bin/bash

# Install script copied from https://github.com/QuantumObject/docker-nagios

echo "postfix postfix/mailname string example.com" | debconf-set-selections
echo "postfix postfix/main_mailer_type string 'Internet Site'" | debconf-set-selections

#add repository and update the container - ENSURE DISTIRB IS RIGHT
echo "
# Non free
deb http://deb.debian.org/debian stretch main contrib non-free
deb-src http://deb.debian.org/debian stretch main contrib non-free

deb http://security.debian.org/debian-security/ stretch/updates main contrib non-free
deb-src http://security.debian.org/debian-security/ stretch/updates main contrib non-free

deb http://deb.debian.org/debian stretch-updates main contrib non-free
deb-src http://deb.debian.org/debian stretch-updates main contrib non-free
" >> /etc/apt/sources.list

#Installation of nesesary package/software for this containers...
apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -q  wget \
                    build-essential \
                    apache2 \
                    apache2-utils \
                    iputils-ping \
                    php-gd \
                    libapache2-mod-php \
                    postfix \
                    libssl-dev \
                    unzip \
                    libdigest-hmac-perl \
                    libnet-snmp-perl \
                    libcrypt-des-perl \
                    mailutils \
                    snmp \
                    lm-sensors snmp-mibs-downloader \
                    dnsutils \
                    nagios-nrpe-plugin \
                    && rm -R /var/www/html \
                    && apt-get clean \
                    && rm -rf /tmp/* /var/tmp/*  \
                    && rm -rf /var/lib/apt/lists/*

##startup scripts
#Pre-config scrip that maybe need to be run one time only when the container run the first time .. using a flag to don't
#run it again ... use for conf for service ... when run the first time ...
mkdir -p /etc/my_init.d
cat > /etc/my_init.d/startup.sh <<- EOM
#!/bin/bash

set -e

if [ -f /etc/configured ]; then
        echo 'already configured'
        postfix start 2>&1 &
else\
        #code that need to run only one time ....
        #needed for fix problem with ubuntu and cron
        update-locale
        echo 'root:  root@example.com' >>/etc/aliases
        newaliases
        #add container Network Docker0 and container ip to postfix configuration , it will fail is custom container network
        postconf -e inet_interfaces=all
        postconf -e myorigin=/etc/mailname
        postconf -e mynetworks='127.0.0.1/32 192.168.0.0/16 172.16.0.0/12 10.0.0.0/8'
        postconf -e myhostname=$HOSTNAME
        postconf -e mydestination=$HOSTNAME
        # to make sure nagios email permision are correct
        touch /var/mail/nagios
        chown nagios:mail /var/mail/nagios
        chmod o-r /var/mail/nagios
        chmod g+rw /var/mail/nagios
        #start postfix
        postfix start 2>&1 &
        date > /etc/configured
fi
EOM

chmod +x /etc/my_init.d/startup.sh

##Get Mibs
bash /usr/bin/download-mibs
echo 'mibs +ALL' >> /etc/snmp/snmp.conf


##Adding Deamons to containers
# to add apache2 deamon to runit
mkdir -p /etc/service/apache2  /var/log/apache2 ; sync
mkdir /etc/service/apache2/log
cat > /etc/service/apache2/run <<- EOM
#!/bin/sh
### In apache2.sh (make sure this file is chmod +x):
# /sbin/setuser www-data runs the given command as the user www-data.
# If you omit that part, the command will be run as root.

source /etc/apache2/envvars
exec chpst -u root apache2ctl -D FOREGROUND 2>&1
EOM

cat > /etc/service/apache2/log/run <<- EOM
#!/bin/sh

exec chpst -u www-data svlogd -tt /var/log/apache2/
EOM
chmod +x /etc/service/apache2/run /etc/service/apache2/log/run
cp /var/log/cron/config /var/log/apache2/
chown -R www-data /var/log/apache2

# to add nagios deamon to runit
mkdir /etc/service/nagios /var/log/nagios ; sync
mkdir /etc/service/nagios/log

cat > /etc/service/nagios/run <<- EOM
#!/bin/bash
### In nagios.sh (make sure this file is chmod +x):
# chpst -u root runs the given command as the user xxxxx.
# If you omit that part, the command will be run as root.

sv -w4 check apache2

exec chpst -u root /usr/local/nagios/bin/nagios /usr/local/nagios/etc/nagios.cfg 2>&1
EOM

cat > /etc/service/nagios/log/run <<- EOM
#!/bin/sh

exec chpst -u root svlogd -tt /var/log/nagios/
EOM

chmod +x /etc/service/nagios/run /etc/service/nagios/log/run
cp /var/log/cron/config /var/log/nagios/
chown -R root /var/log/nagios

#pre-config scritp for different service that need to be run when container image is create
#maybe include additional software that need to be installed ... with some service running ... like example mysqld
cat > /sbin/pre-conf <<- EOM
#!/bin/bash

#reason of this script is that dockerfile only execute one command at the time but we need sometimes at the moment we create
#the docker image to run more that one software for expecified configuration like when you need mysql running to chnage or create
#database for the container ...

 useradd --system --home /usr/local/nagios -M nagios
 groupadd --system nagcmd
 usermod -a -G nagcmd nagios
 usermod -a -G nagcmd www-data
 usermod -G nagios www-data
 cd /tmp
 wget https://sourceforge.net/projects/nagios/files/nagios-4.x/nagios-4.4.2/nagios-4.4.2.tar.gz
 wget http://nagios-plugins.org/download/nagios-plugins-2.2.1.tar.gz
 wget https://sourceforge.net/projects/nagios/files/nrpe-3.x/nrpe-3.2.1/nrpe-3.2.1.tar.gz
 tar -xvf nagios-4.4.2.tar.gz
 tar -xvf nagios-plugins-2.2.1.tar.gz
 tar -xvf nrpe-3.2.1.tar.gz

 #installing nagios
 cd /tmp/nagios-4.4.2
  ./configure --with-nagios-group=nagios --with-command-group=nagcmd --with-mail=/usr/sbin/sendmail --with-httpd_conf=/etc/apache2/conf-available
  make all
  make install
  make install-init
  make install-config
  make install-commandmode
  make install-webconf
  cp -R contrib/eventhandlers/ /usr/local/nagios/libexec/
  chown -R nagios:nagios /usr/local/nagios/libexec/eventhandlers
  mkdir -p /usr/local/nagios/var/spool
  mkdir -p /usr/local/nagios/var/spool/checkresults
  chown -R nagios:nagios /usr/local/nagios/var
  /usr/local/nagios/bin/nagios -v /usr/local/nagios/etc/nagios.cfg
  ln -s /etc/init.d/nagios /etc/rcS.d/S99nagios

  #installing plugins
  cd /tmp/nagios-plugins-2.2.1/
  ./configure --with-nagios-user=nagios --with-nagios-group=nagios --enable-perl-modules --enable-extra-opts
  make
  make install

  cd /tmp/nrpe-3.2.1/
  ./configure --with-nrpe-user=nagios --with-nrpe-group=nagios --with-nagios-user=nagios --with-nagios-group=nagios  --with-ssl=/usr/bin/openssl --with-ssl-lib=/usr/lib/x86_64-linux-gnu
  make all
  make install-plugin

  #to fix error relate to ip address of container apache2
  echo "ServerName localhost" | tee /etc/apache2/conf-available/fqdn.conf
  ln -s /etc/apache2/conf-available/fqdn.conf /etc/apache2/conf-enabled/fqdn.conf


  a2enmod cgi
  htpasswd -b -c /usr/local/nagios/etc/htpasswd.users nagiosadmin admin
  sed -i 's/#Include.*/Include conf-available\/nagios.conf/' /etc/apache2/sites-enabled/000-default.conf
  sed -i 's/\/usr\/sbin\/sendmail -s/\/usr\/sbin\/sendmail -vt/' /usr/local/nagios/etc/objects/commands.cfg
  rm -rf /tmp/* /var/tmp/*
EOM
chmod +x /sbin/pre-conf ; sync
/bin/bash -c /sbin/pre-conf \
    && rm /sbin/pre-conf


##Copy plguins installed though apt to location
cp /usr/lib/nagios/plugins/check_nrpe /usr/local/nagios/libexec/ ; sync

##scritp that can be running from the outside using docker-bash tool ...
## for example to create backup for database with convitation of VOLUME   dockers-bash container_ID backup_mysql
cat  >  /sbin/backup <<- EOM
#!/bin/bash
#this for reference only to create the backup scrips for each container ... the idea to use the same command for each container
#each container will have their own custum backup scritp for it ...

#Backup important file ... of the configuration ...
cp  /etc/hosts  /var/backups/

#Backup importand files relate to app
EOM
chmod +x /sbin/backup
#VOLUME /var/backups

service apache2 restart
service nagios restart
# to allow access from outside of the container  to the container service
# at that ports need to allow access from firewall if need to access it outside of the server.
# EXPOSE 80 25
