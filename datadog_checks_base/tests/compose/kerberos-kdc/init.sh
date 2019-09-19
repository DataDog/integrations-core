#!/bin/sh

KDC_CONFIG_DIR=/var/kerberos/krb5kdc

KDC_DATABASE=/dev/shm/kerberos/db

[ -z ${KRB5_KDC} ] && echo "*** KRB5_KDC variable not set, KDC host missing, using 'localhost' as default." && KRB5_KDC=localhost

[ -z ${RUN_MODE} ] && echo "*** RUN_MODE not specified, options are 'kdc', and 'kadmin'. Default is 'kdc'" && RUN_MODE=kdc

[ -z ${KRB5_REALM} ] && echo "*** Default realm not set (KRB5_REALM), using EXAMPLE.COM as default" && KRB5_REALM="EXAMPLE.COM"

function generate_config()
{
  # create a kdc principal if one doesn't exist
  if [ ! -f "${KDC_DATABASE}/principal" ]; then

    mkdir -p ${KDC_DATABASE}

    if [ -z ${KRB5_PASS} ]; then

      KRB5_PASS=$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c${1:-32};echo;)
      echo "*** Your KDC password is ${KRB5_PASS}"

    fi

    ACL_FILE="${KDC_CONFIG_DIR}.d/kadm5-${KRB5_REALM}.acl"

    cat <<EOF > /etc/krb5.conf.d/$KRB5_REALM.conf

[realms]
${KRB5_REALM} = {
   kdc = ${KRB5_KDC}
   admin_server = ${KRB5_KDC}
   kpasswd_server = ${KRB5_KDC}
}
EOF

    # Create a realm configuration
    cat <<EOF > ${KDC_CONFIG_DIR}.d/$KRB5_REALM.conf

[realms]

${KRB5_REALM} = {
  kpasswd_port = 8464
  kadmind_port = 8749
  acl_file = ${ACL_FILE}
  max_life = 12h 0m 0s
  max_renewable_life = 7d 0h 0m 0s
  master_key_type = aes256-cts
  supported_enctypes = aes256-cts:normal aes128-cts:normal
  default_principal_flags = +preauth
}

[dbmodules]
 ${KRB5_REALM} = {
   database_name = ${KDC_DATABASE}/principal
}
EOF

    echo "*/admin@${KRB5_REALM} *" > ${ACL_FILE}
    echo "*/service@${KRB5_REALM} aci" >> ${ACL_FILE}

    cat <<EOF > /tmp/krb5_pass
${KRB5_PASS}
${KRB5_PASS}
EOF

    # Create a KDC database for the realm 
    kdb5_util create -r ${KRB5_REALM} < /tmp/krb5_pass
    rm /tmp/krb5_pass

    ## Creates a <user>/<instance>@<realm>
    ## admin/admin for remote kadmin
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -pw ${KRB5_PASS} admin/admin@${KRB5_REALM}"
    ## HTTP/hostname.fqdn@realm
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -requires_preauth -pw ${KRB5_PASS} ${KRB5_SVC}/web.example.com@${KRB5_REALM}"
    ## Additional users
    # kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -requires_preauth -pw ${KRB5_PASS} ${KRB5_USER}@${KRB5_REALM}"

    ## Creates and adds principals to a keytab file
    ## HTTP/hostname.fqdn@realm
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "ktadd -k /tmp/shared/http.keytab ${KRB5_SVC}/web.example.com@${KRB5_REALM}"
    ## Additional users
    # kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "ktadd -k /tmp/shared/http.keytab ${KRB5_USER}@${KRB5_REALM}"

    ## Lists all principals in realm
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "listprincs"

  fi
}

function share_config()
{
   mkdir -p /dev/shm/krb5/etc
   cp -rp /var/kerberos/* /dev/shm/krb5/
   cp /etc/krb5.conf /dev/shm/krb5/etc/
   cp -rp /etc/krb5.conf.d /dev/shm/krb5/etc/

}

function copy_shared_config()
{
  counter=0
  while [[ ! -d /dev/shm/krb5/etc ]]
  do
    echo "*** Waiting for krb5 configuration"
    sleep 2

    counter=$((counter+1))
    [[ $counter -gt 10 ]] && echo "*** Configuration took too long" && exit 1

  done

  cp -r /dev/shm/krb5/krb5* /var/kerberos/
  cp /dev/shm/krb5/etc/krb5.conf /etc/
  cp -r /dev/shm/krb5/etc/krb5.conf.d/* /etc/krb5.conf.d/

}


function run_kdc()
{

  generate_config

  share_config

  /usr/sbin/krb5kdc -n -r ${KRB5_REALM}

}

function run_kadmin()
{
  copy_shared_config

  /usr/sbin/kadmind -nofork -r ${KRB5_REALM} 

}

case $RUN_MODE in
  kdc)
    run_kdc
    ;;

  kadmin)
    run_kadmin
    ;;

  *)
    echo "*** Unrecognised RUN_MODE=$RUN_MODE. Supported options are 'kdc' and 'kadmin'"
    exit 1
esac