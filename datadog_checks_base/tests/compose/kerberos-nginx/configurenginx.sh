#!/bin/bash
echo " --- configuring nginx..."

cat > /etc/nginx/conf.d/default.conf << EOF
server {
  server_name $HOSTNAME.$DOMAIN;
  #server_name localhost;

  listen 80 default_server;

  # location / {
  #     root   /usr/share/nginx/html;
  #     index  index.html index.htm;
  # }
  location / {
    stub_status on;
    allow all;

    auth_gss on;
    auth_gss_keytab $KRB5_KEYTAB;
    auth_gss_service_name ${KRB5_SVC}/$HOSTNAME.$DOMAIN;
    auth_gss_realm $KRB5_REALM;
    auth_gss_allow_basic_fallback off;
  }
}
EOF
echo "nginx configured as:"
cat /etc/nginx/conf.d/default.conf

