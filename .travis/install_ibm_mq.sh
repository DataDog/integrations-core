#!/bin/bash

set -ex

TMP_DIR=/tmp/mq
MQ_URL=http://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqadv/mqadv_dev90_linux_x86-64.tar.gz
MQ_PACKAGES="MQSeriesRuntime-*.rpm MQSeriesServer-*.rpm MQSeriesMsg*.rpm MQSeriesJava*.rpm MQSeriesJRE*.rpm MQSeriesGSKit*.rpm"

if [ "$CHECK" != "ibm_mq" -a -n `ddev test --list` =~ "ibm_mq" ]; then
  exit 0
fi

if [ -e /opt/mqm/inc/cmqc.h ]; then
  echo "cmqc.h already exists, exiting"
  set +ex
  exit 0
fi

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  bash \
  bc \
  coreutils \
  curl \
  debianutils \
  findutils \
  gawk \
  grep \
  libc-bin \
  mount \
  passwd \
  procps \
  rpm \
  sed \
  tar \
  util-linux

mkdir -p $TMP_DIR
pushd $TMP_DIR
  curl -LO $MQ_URL
  tar -zxvf ./*.tar.gz
  pushd MQServer
    sudo ./mqlicense.sh -text_only -accept
    sudo rpm -ivh --force-debian *.rpm
    sudo /opt/mqm/bin/setmqinst -p /opt/mqm -i
  popd
popd

ls /opt/mqm
ls /opt/mqm/inc/

set +ex
