# This script makes the necessary setup to be able to compile pymqi on the agent machine

set -x  # Show executed commands
set -e  # Stop on first failure

INSTANT_CLIENT_URL="https://ddintegrations.blob.core.windows.net/oracle/instantclient-basiclite-linux.x64-19.3.0.0.0dbru.zip"

mkdir /opt/oracle

# Retry:
# - Retry `apt-get`: we might not be able to fetch deps from debian
# - Retry curl: donwload might fail due to:
#   curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
for i in 2 4 8 16 32; do
  apt-get update
  apt-get install -y unzip
  curl -o /opt/oracle/instantclient.zip $INSTANT_CLIENT_URL && break
  sleep $i
done

# Unzip will fail if the oracle client download failed
unzip /opt/oracle/instantclient.zip -d /opt/oracle
