#!/bin/bash
set -e

for bar in /home/aceuser/bars/*.bar
do
  mqsibar -a $bar -w /home/aceuser/ace-server -c
done
