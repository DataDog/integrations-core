#!/bin/bash

HAPROXY_VERSION='1.5.11'

docker create -p 3835:3835 --name haproxy haproxy:$HAPROXY_VERSION
docker create -p 3836:3836 --name haproxy-open haproxy:$HAPROXY_VERSION

docker cp haproxy/ci/haproxy.cfg haproxy:/usr/local/etc/haproxy/haproxy.cfg
docker cp haproxy/ci/haproxy-open.cfg haproxy-open:/usr/local/etc/haproxy/haproxy.cfg

docker start haproxy
docker start haproxy-open
