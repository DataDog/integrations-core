FROM ubuntu:18.04

RUN set -x \
 && DEBIAN_FRONTEND=noninteractive apt-get update  \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends\
        curl \
        build-essential \
        pkg-config \
        libtool \
        libz-dev \
        libssl-dev \
        libpcre3-dev \
        libcap-dev \
        flex \
        hwloc \
        lua5.3 \
        libncurses5-dev \
        ca-certificates \
 && mkdir /opt/ats \
 && curl -L https://dlcdn.apache.org/trafficserver/trafficserver-{TRAFFIC_SERVER_VERSION}.tar.bz2 | tar xjv --strip-components 1  \
 && ./configure  --prefix=/opt/ats \
 && make  \
 && make install

