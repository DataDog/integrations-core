#!/bin/bash
echo "configuring kerberos..."
kdc=$KRB5_KDC
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
        kdc            = $kdc.$DOMAIN:8888
        admin_server   = $kdc.$DOMAIN:8749
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
