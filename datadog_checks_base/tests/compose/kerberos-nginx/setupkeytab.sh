#!/bin/bash
set -e

echo "domain: ${DOMAIN}"
echo "realm: ${KRB5_REALM}"

# usernameplusdomain="${KRB5_USER}@${DOMAIN}"
# echo "User name: $usernameplusdomain"

set -x

## Load principals into cache
kinit -kt ${KRB5_KEYTAB} ${SERVICE_NAME}@${KRB5_REALM} -V
echo ${KRB5_PASS} | kinit user/nokeytab@${KRB5_REALM} -c ${KRB5_CCNAME}/tkt_nokeytab -V

## List principals in cache
echo "Principals in keytab..."
echo "----------------------"
klist -ket ${KRB5_KEYTAB}
echo "======================"
echo "Principals in cache..."
echo "----------------------"
klist
echo "======================"
echo "Copying Kerberos cache file..."
echo "----------------------"
cp /tmp/krb5cc_* ${KRB5_CCNAME}/tkt_web
echo "tkt" > ${KRB5_CCNAME}/primary
chmod a+r ${KRB5_CCNAME}/*
echo "======================"

echo "ReadyToConnect"
set +x