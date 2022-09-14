#!/bin/bash

./opt/install/configurekerberos.sh
./opt/install/configurenginx.sh
./opt/install/setupkeytab.sh
chmod 744 $KRB5_KEYTAB
chown root:nginx $KRB5_KEYTAB
exec nginx -g "daemon off;"
