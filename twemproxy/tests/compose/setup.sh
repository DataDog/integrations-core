#!/bin/sh

curl -L -X PUT http://etcd0:2379/v2/keys/services/redis/01 -d value="redis1:6101"
curl -L -X PUT http://etcd0:2379/v2/keys/services/redis/02 -d value="redis2:6102"
curl -L -X PUT http://etcd0:2379/v2/keys/services/twemproxy/port -d value="6100"
curl -L -X PUT http://etcd0:2379/v2/keys/services/twemproxy/host -d value="localhost"

bash /run.sh
