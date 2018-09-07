#!/bin/bash

echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled || true
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag || true

mongod --bind_ip 0.0.0.0 --port 37017
