#!/bin/bash

echo never > /sys/kernel/mm/transparent_hugepage/enabled || true

mongod --bind_ip 0.0.0.0 --port 37017
