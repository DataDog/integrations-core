DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# docker-compose  -f ibm_mq/tests/compose/docker-compose-v9-cluster.yml up

docker cp $DIR/ibm_mq_startup.sh ibm_mq1:/tmp/ibm_mq_startup.sh

docker exec ibm_mq1 bash /tmp/ibm_mq_startup.sh

echo abc | docker exec ibm_mq1 /opt/mqm/samp/bin/amqsput APP.QUEUE.1

docker exec ibm_mq1 /opt/mqm/samp/bin/amqsevt -m QM1 -q SYSTEM.ADMIN.STATISTICS.QUEUE | grep 'Event Type'
