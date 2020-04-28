# This script makes the necessary setup to be able to compile pymqi on the agent machine

INSTANT_CLIENT_URL="https://ddintegrations.blob.core.windows.net/oracle/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip"

mkdir /opt/oracle
apt-get update
apt-get install libaio1 unzip

# Retry necessary due to flaky download that might trigger:
# curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
for i in 2 4 8 16 32; do
  curl -o /opt/oracle/instantclient.zip $INSTANT_CLIENT_URL && break
  sleep $i
done

unzip /opt/oracle/instantclient.zip -d /opt/oracle
