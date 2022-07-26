#!/bin/bash

IPV4="127.0.0.1 $HOSTNAME"
IPV6="::1 $HOSTNAME"

sudo -- sh -c -e "echo '$IPV4' >> /etc/hosts";
sudo -- sh -c -e "echo '$IPV6' >> /etc/hosts";
