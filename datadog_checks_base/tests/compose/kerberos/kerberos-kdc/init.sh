#!/bin/sh

KDC_CONFIG_DIR=/var/kerberos/krb5kdc

KDC_DATABASE=/dev/shm/kerberos/db

[ -z ${KRB5_KDC} ] && echo "*** KRB5_KDC variable not set, KDC host missing, using 'localhost' as default." && KRB5_KDC=localhost

[ -z ${RUN_MODE} ] && echo "*** RUN_MODE not specified, options are 'kdc', 'kadmin', or 'kdckadmin'. Default is 'kdc'" && RUN_MODE=kdc

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
  kdc = ${KRB5_KDC}.${DOMAIN}:8888
  admin_server = ${KRB5_KDC}.${DOMAIN}:8749
  kpasswd_server = ${KRB5_KDC}
  default_domain = $DOMAIN 
  kpasswd_port = 8464
}
EOF

echo "configuring kerberos..."

cat > /etc/krb5.conf << EOF
[libdefaults]
    default_tkt_enctypes = aes256-cts arcfour-hmac-md5 des-cbc-crc des-cbc-md5
    default_tgs_enctypes = aes256-cts arcfour-hmac-md5 des-cbc-crc des-cbc-md5
    default_keytab_name  = FILE:$KRB5_KEYTAB
    default_realm        = $KRB5_REALM 
    ticket_lifetime      = 24h
    kdc_timesync         = 1
    ccache_type          = 4
    forwardable          = false
    proxiable            = false

[realms]
    $KRB5_REALM = {
        kdc            = $HOSTNAME.$DOMAIN:8888
        admin_server   = $HOSTNAME.$DOMAIN:8749
        kpasswd_server = $HOSTNAME.$DOMAIN
        default_domain = $DOMAIN 
        kpasswd_port = 8464
    }

[domain_realm]
    .kerberos.server = $KRB5_REALM 
    .fabric.local    = $KRB5_REALM 
    .$DOMAIN = $KRB5_REALM 
EOF
echo "kerberos configured as: "
cat /etc/krb5.conf
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
    rm ${KRB5_KEYTAB}

    ## Creates a <user>/<instance>@<realm>
    ## admin/admin for remote kadmin
    # kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -pw ${KRB5_PASS} ${KRB5_USER}@${KRB5_REALM}"
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -pw ${KRB5_PASS} ${KRB5_USER}@${KRB5_REALM}"
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -pw ${KRB5_PASS} user/inkeytab@${KRB5_REALM}"
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -pw ${KRB5_PASS} user/nokeytab@${KRB5_REALM}"

    # ## HTTP/hostname.fqdn@realm
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -requires_preauth -randkey ${KRB5_SVC}/${WEBHOST}@${KRB5_REALM}"
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -requires_preauth -randkey ${KRB5_SVC}/localhost@${KRB5_REALM}"

    ## Creates and adds principals to a keytab file
    ## HTTP/hostname.fqdn@realm
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "ktadd -k ${KRB5_KEYTAB} ${KRB5_SVC}/${WEBHOST}@${KRB5_REALM}"
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "ktadd -k ${KRB5_KEYTAB} ${KRB5_SVC}/localhost@${KRB5_REALM}"

    # Add for supporting Agent-based verification
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "addprinc -requires_preauth -randkey ${KRB5_SVC}/compose_web_1.compose_kdc-net@${KRB5_REALM}"
    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "ktadd -k ${KRB5_KEYTAB} ${KRB5_SVC}/compose_web_1.compose_kdc-net@${KRB5_REALM}"

    kadmin.local -r ${KRB5_REALM} -p "K/M@KRV.SVC" -q "ktadd -k ${KRB5_KEYTAB} user/inkeytab@${KRB5_REALM}"

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


function run_kdc_kadmin()
{

  generate_config

  share_config

  /usr/sbin/krb5kdc -n -r ${KRB5_REALM} &
  /usr/sbin/kadmind -nofork -r ${KRB5_REALM} 

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

  kdckadmin)
    run_kdc_kadmin
    ;;

  *)
    echo "*** Unrecognised RUN_MODE=$RUN_MODE. Supported options are 'kdc' and 'kadmin'"
    exit 1
esac
