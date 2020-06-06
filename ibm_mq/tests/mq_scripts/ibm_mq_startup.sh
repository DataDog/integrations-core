# This script makes the necessary setup to be able to compile pymqi on the agent machine

MQ_URL=https://ddintegrations.blob.core.windows.net/ibm-mq/9.1.0.4-IBM-MQC-Redist-LinuxX64.tar.gz

apt-get update
apt-get install gcc -y

mkdir -p /tmp/mqm

# Retry necessary due to flaky download that might trigger:
# curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
for i in 2 4 8 16 32; do
  curl -k -L -o /tmp/mq-client.tar.gz $MQ_URL && break
  sleep $i
done

tar -C /tmp/mqm -xf /tmp/mq-client.tar.gz

cp -r /tmp/mqm/samp /opt/mqm/samp
