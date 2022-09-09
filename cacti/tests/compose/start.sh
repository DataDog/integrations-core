#!/bin/bash

# set server timezone
echo "$(date +%F_%R) [Note] Setting server timezone settings to '${TZ}'"
echo "date.timezone = ${TZ}" >> /etc/php.ini

# set custom php.ini enviorments to follow Cacti Recommendations requirment
sed -i "s/^\(memory_limit =\).*/\1 ${PHP_MEMORY_LIMIT}/" /etc/php.ini
sed -i "s/^\(max_execution_time =\).*/\1 ${PHP_MAX_EXECUTION_TIME}/" /etc/php.ini

rm /etc/localtime
ln -s /usr/share/zoneinfo/${TZ} /etc/localtime

# remove php-snmp if asked, required for snmpv3 to function correctly. Disabled by default
if [ ${PHP_SNMP} = 0 ]; then
    echo "$(date +%F_%R) [PHP-SNMP] Removing php-snmp since ENV variable 'PHP_SNMP' is set to 0"
    yum remove -y --noautoremove php-snmp
    yum clean all
    else
    echo "$(date +%F_%R) [PHP-SNMP] Insalling php-snmp since ENV variable 'PHP_SNMP' is set to 1"
    yum install -y php-snmp
    yum clean all
fi

# verify if initial install steps are required, if lock file does not exist run the following   
if [ ! -f /cacti/install.lock ]; then
    echo "$(date +%F_%R) [New Install] Lock file does not exist - new install."

    # THIS WAS IN DOCKER-FILE
    # CACTI BASE INSTALL
    echo "$(date +%F_%R) [New Install] Extracting and installing Cacti files to /cacti."
    tar -xf /cacti_install/cacti-1*.tar.gz -C /tmp
    mv /tmp/cacti-1*/* /cacti/

    # SPINE BASE INSTALL
    echo "$(date +%F_%R) [New Install] Extracting and installing Spine files to /spine."
    tar -xf /cacti_install/cacti-spine-*.tar.gz -C /tmp
    cd /tmp/cacti-spine-* && \
        ./bootstrap && \
       ./configure --prefix=/spine && make && make install && \
       chown root:root /spine/bin/spine && \
       chmod +s /spine/bin/spine

    # BASE CONFIGS
    echo "$(date +%F_%R) [New Install] Copying templated configurations to Spine, Apache, and Cacti."
    cp /template_configs/spine.conf /spine/etc
    cp /template_configs/cacti.conf /etc/httpd/conf.d
    cp /template_configs/config.php /cacti/include

    # update cacti url path config, requested via https://github.com/scline/docker-cacti/issues/73
    echo "$(date +%F_%R) [New Install] Applying cacti URL enviromental variable to /etc/httpd/conf.d/cacti.conf"
    sed -i -e "s/Alias.*/   Alias    \/${CACTI_URL_PATH} \/cacti/" \
           -e "s/RedirectMatch.*/   RedirectMatch    \^\/\$ \/${CACTI_URL_PATH}/" \
        /etc/httpd/conf.d/cacti.conf

    # setup database credential settings
    echo "$(date +%F_%R) [New Install] Applying enviromental variables to configurations."
    sed -i -e "s/%DB_HOST%/${DB_HOST}/" \
           -e "s/%DB_PORT%/${DB_PORT}/" \
           -e "s/%DB_NAME%/${DB_NAME}/" \
           -e "s/%DB_USER%/${DB_USER}/" \
           -e "s/%DB_PASS%/${DB_PASS}/" \
           -e "s/%DB_PORT%/${DB_PORT}/" \
           -e "s/%RDB_HOST%/${RDB_HOST}/" \
           -e "s/%RDB_PORT%/${RDB_PORT}/" \
           -e "s/%RDB_NAME%/${RDB_NAME}/" \
           -e "s/%RDB_USER%/${RDB_USER}/" \
           -e "s/%RDB_PASS%/${RDB_PASS}/" \
           -e "s/%CACTI_URL_PATH%/${CACTI_URL_PATH}/" \
        /cacti/include/config.php \
        /settings/*.sql \
        /spine/etc/spine.conf

    # wait for database to initialize - http://stackoverflow.com/questions/4922943/test-from-shell-script-if-remote-tcp-port-is-open
    echo "$(date +%F_%R) [New Install] Waiting for database to respond, if this hangs please check MySQL connections are allowed and functional."
    while ! timeout 1 bash -c 'cat < /dev/null > /dev/tcp/${DB_HOST}/${DB_PORT}'; do sleep 3; done
    echo "$(date +%F_%R) [New Install] Database is up! - configuring DB located at ${DB_HOST}:${DB_PORT} (this can take a few minutes)."

    # if docker was told to setup the database then perform the following
    if [ ${INITIALIZE_DB} = 1 ]; then
        echo "$(date +%F_%R) [New Install] Container has been instructed to create new Database on remote system."
        # initial database and user setup
        echo "$(date +%F_%R) [New Install] CREATE DATABASE ${DB_NAME} /*\!40100 DEFAULT CHARACTER SET utf8 */;"
        mysql -h ${DB_HOST} --port=${DB_PORT} -uroot -p${DB_ROOT_PASS} -e "CREATE DATABASE ${DB_NAME} /*\!40100 DEFAULT CHARACTER SET utf8 */;"
        # allow cacti user access to new database
        echo "$(date +%F_%R) [New Install] GRANT ALL ON ${DB_NAME}.* TO '${DB_USER}' IDENTIFIED BY '*******';"
        mysql -h ${DB_HOST} --port=${DB_PORT} -uroot -p${DB_ROOT_PASS} -e "GRANT ALL ON ${DB_NAME}.* TO '${DB_USER}' IDENTIFIED BY '${DB_PASS}';"
        # allow cacti user super access to new database (required to merge cacti.sql table)
        echo "$(date +%F_%R) [New Install] GRANT SUPER ON *.* TO '${DB_USER}'@'%';"
        mysql -h ${DB_HOST} --port=${DB_PORT} -uroot -p${DB_ROOT_PASS} -e "GRANT SUPER ON *.* TO '${DB_USER}'@'%';"
        # allow required access to mysql timezone table
        echo "$(date +%F_%R) [New Install] GRANT SELECT ON mysql.time_zone_name TO '${DB_USER}' IDENTIFIED BY '*******';"
        mysql -h ${DB_HOST} --port=${DB_PORT} -uroot -p${DB_ROOT_PASS} -e "GRANT SELECT ON mysql.time_zone_name TO '${DB_USER}' IDENTIFIED BY '${DB_PASS}';"
    fi

    # fresh install db merge
    echo "$(date +%F_%R) [New Install] Merging vanilla cacti.sql file to database."
    mysql -h ${DB_HOST} --port=${DB_PORT} -u${DB_USER} -p${DB_PASS} ${DB_NAME} < /cacti/cacti.sql

    # if this is a remote poller dont do anything with scripts/templates or plugins. This is sourced from the master instance
    if [ ${REMOTE_POLLER} != 1 ]; then
        echo "$(date +%F_%R) [New Install] Installing supporting template files."
        cp -r /templates/resource/* /cacti/resource 
        cp -r /templates/scripts/* /cacti/scripts

        echo "$(date +%F_%R) [New Install] Installing plugins."
        cp -r /cacti_install/plugins/* /cacti/plugins

        # install additional templates
        for filename in /templates/*.xml; do
            echo "$(date +%F_%R) [New Install] Installing template file $filename"
            php -q /cacti/cli/import_template.php --filename=$filename > /dev/null
        done
    fi

    # install additional settings
    for filename in /settings/*.sql; do
        echo "$(date +%F_%R) [New Install] Importing settings file $filename"
        mysql -h ${DB_HOST} --port=${DB_PORT} -u${DB_USER} -p${DB_PASS} ${DB_NAME} < $filename
    done

    # CLEANUP
    echo "$(date +%F_%R) [New Install] Removing temp Cacti and Spine installation files."
    rm -rf /tmp/*

    # create lock file so this is not re-ran on restart
    touch /cacti/install.lock
    echo "$(date +%F_%R) [New Install] Creating lock file, db setup complete."
fi

# copy configuration files in the event /cacti is being shared as a volume
echo "$(date +%F_%R) [Apache] Validating httpd cacti configuration is present."
if [ -f "/etc/httpd/conf.d/cacti.conf" ]; then
    echo "$(date +%F_%R) [Apache] /etc/httpd/conf.d/cacti.conf exist, nothing to do."
else 
    echo "$(date +%F_%R) [Apache] /etc/httpd/conf.d/cacti.conf does not exist, copying a new one over."
    cp /template_configs/cacti.conf /etc/httpd/conf.d/
    # update cacti url path config, requested via https://github.com/scline/docker-cacti/issues/73
    echo "$(date +%F_%R) [Apache] Applying cacti URL enviromental variable to /etc/httpd/conf.d/cacti.conf"
    sed -i -e "s/Alias.*/   Alias    \/${CACTI_URL_PATH} \/cacti/" \
           -e "s/RedirectMatch.*/   RedirectMatch    \^\/\$ \/${CACTI_URL_PATH}/" \
        /etc/httpd/conf.d/cacti.conf
fi

# only generate certs if none exsist, this way users can provide there own
if [ ! -f /etc/ssl/certs/cacti.key  ] || [ ! -f /etc/ssl/certs/cacti.crt  ]; then
    # generate self-signed certs for basic https functionality. 
    echo "$(date +%F_%R) [Apache] Missing HTTPS certs, generating self-signed one's."
    openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
        -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" \
        -keyout /etc/ssl/certs/cacti.key  -out /etc/ssl/certs/cacti.crt
    else
    echo "$(date +%F_%R) [Apache] /etc/ssl/certs/cacti.key and /etc/ssl/certs/cacti.crt exist, nothing to do."
fi

# correcting file permissions
echo "$(date +%F_%R) [Note] Setting cacti file permissions."
chown -R apache.apache /cacti/resource/
chown -R apache.apache /cacti/cache/
chown -R apache.apache /cacti/log/
chown -R apache.apache /cacti/scripts/
chown -R apache.apache /cacti/rra/

# remote poller tasks
if [ ${REMOTE_POLLER} = 1 ]; then
    echo "$(date +%F_%R) [Remote Poller] This is slated to be a remote poller, updating cacti configs for these settings."
    sed -i -e "s/#\$rdatabase/\$rdatabase/" /cacti/include/config.php
    echo "$(date +%F_%R) [Remote Poller] Updating permissions in cacti directory for remote poller template."
    chown -R apache.apache /cacti

    # fix remote poller install check from https://github.com/Cacti/cacti/issues/3459
    echo "$(date +%F_%R) [Remote Poller] Manual hack to fix https://github.com/Cacti/cacti/issues/3459"
    sed -i -e "s/print json_encode/return json_encode/g" /cacti/install/functions.php
fi

# backup cron tasks
if [ ${BACKUP_TIME} -gt 0 ]; then
    sed -i -e "s/%DB_HOST%/${DB_HOST}/" /var/spool/cron/apache
fi

# start cron service
echo "$(date +%F_%R) [Note] Starting crond service."
/usr/sbin/crond -n &

# start snmp servics
echo "$(date +%F_%R) [Note] Starting snmpd service."
snmpd -Lf /var/log/snmpd.log &

# start php-fpm
echo "$(date +%F_%R) [Note] Starting php-fpm service."
# make sure socket and pid files are all cleaned before starting
mkdir /run/php-fpm
rm -rf /run/php-fpm/*
# change settings in php-fpm file due to https://github.com/scline/docker-cacti/issues/64
sed -i -e "s/;listen.owner = nobody/listen.owner = apache/g" \
       -e "s/;listen.group = nobody/listen.group = apache/g" \
       -e "s/listen.acl_users = apache,nginx/;listen.acl_users = apache,nginx/g" \
    /etc/php-fpm.d/www.conf
php-fpm

# start web service
echo "$(date +%F_%R) [Note] Starting httpd service."
rm -rf /run/httpd/httpd.pid
httpd -DFOREGROUND
