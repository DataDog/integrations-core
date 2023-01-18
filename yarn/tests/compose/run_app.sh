#!/bin/bash

# https://github.com/sequenceiq/hadoop-docker#testing
# Run demo application every 5 minutes

cd $HADOOP_PREFIX

while :
  do
    bin/hadoop jar share/hadoop/mapreduce/hadoop-mapreduce-examples-2.7.1.jar grep input output 'dfs[a-z.]+'
    sleep 300
  done
