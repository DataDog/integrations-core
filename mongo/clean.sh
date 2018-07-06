#!/bin/bash

docker rm -f `docker ps -aq` || true
docker volume prune -f || true
