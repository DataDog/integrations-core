# This script makes the necessary setup to be able to compile pymqi on the agent machine

MQ_URL=https://ddintegrations.blob.core.windows.net/ibm-mq/9.1.0.4-IBM-MQC-Redist-LinuxX64.tar.gz

apt-get update
apt-get install gcc -y

mkdir /opt/mqm

# Retry necessary due to flaky download that might trigger:
# curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
for i in 2 4 8 16 32; do
  curl -L -o /opt/mqm/mq-client.tar.gz $MQ_URL && break
  sleep $i
done

tar -C /opt/mqm -xf /opt/mqm/mq-client.tar.gz

# TODO: Remove when new version of pymqi is released
export LD_LIBRARY_PATH=/opt/mqm/lib64:/opt/mqm/lib
/opt/datadog-agent/embedded/bin/python -m pip install --upgrade --force-reinstall 'https://github.com/dsuch/pymqi/tarball/master#egg=pymqi&subdirectory=code'
