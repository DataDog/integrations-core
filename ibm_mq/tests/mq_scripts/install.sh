DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker cp $DIR/ibm_mq_startup.sh ibm_mq1:/tmp/ibm_mq_startup.sh

docker exec ibm_mq1 bash /tmp/ibm_mq_startup.sh



