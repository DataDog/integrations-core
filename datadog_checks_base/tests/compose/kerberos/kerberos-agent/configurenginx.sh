#!/bin/bash
echo "configuring nginx check ..."
cat > /etc/datadog-agent/conf.d/nginx.d/nginx.yaml << EOF
init_config: {}
instances:
- auth_type: kerberos
  kerberos_auth: required
  kerberos_cache: DIR:$KRB5_CCNAME
  kerberos_keytab: $KRB5_KEYTAB
  kerberos_force_initiate: 'true'
  kerberos_hostname: web.example.com
  kerberos_principal: user/inkeytab@EXAMPLE.COM
  nginx_status_url: http://web:8080/nginx_status
  url: http://web:8080
EOF
echo "nginx configured as: "
cat /etc/datadog-agent/conf.d/nginx.d/nginx.yaml
