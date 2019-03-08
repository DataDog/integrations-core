#!/bin/bash

if [ $1 = "coordinator" ]
then
  echo coordinator=true >> etc/config.properties
  echo discovery-server.enabled=true >> etc/config.properties
  echo node-scheduler.include-coordinator=false >> etc/config.properties
fi

if [ $1 = "worker" ]
then
  echo coordinator=false >> etc/config.properties
fi