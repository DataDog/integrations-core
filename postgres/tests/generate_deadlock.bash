#!/usr/bin/bash

# This is a stand-alone helper script for generating deadlocks
#
# Usage: generate_deadlock.bash [ PSQL_ARGUMENTS ]
#
# Usage examples:
#
#    generate_deadlock.bash
#
#    export PGPASSWORD=... 
#    generate_deadlock.bash -U postgres -h localhost
# 

USAGE='USAGE:
    generate_deadlocks.bash

	OPTIONS:
	-c N         	count of deadlocks. Default is 1.
	-p PSQL_ARGS	any psql arguments 

USAGE EXAMPLES:
	generate_deadlock.bash

	export PGPASSWORD=...
	generate_deadlock.bash -p "-U postgres -h localhost -d datadog_test"

	generate_deadlock.bash -p "-U postgres -h localhost -d datadog_test" -c 1000

KNOWN ISSUES

If deadlocks are not being generated, increase the SLEEP value
'

SLEEP=2
c=1

while getopts ":hc:p:" option; do
    case $option in
	c)
        c=$OPTARG;;
	p)
	    psql_args=$OPTARG;;
    h)
        echo "$USAGE"
        exit;;
	\?)
	    echo "ERROR: Invalid option"
	    echo "$USAGE"
	    exit 1;;
    esac
done

PSQL="psql $psql_args"
$PSQL << EOD > /dev/null
create table t ( id integer, data integer ) ;
insert into t values (1, null);
insert into t values (2, null);
EOD

$PSQL << EOD
select sum(deadlocks) "deadlocks before" from pg_stat_database ;
EOD

for ((i=1; i<= $c; i++))
do
    #$PSQL << EOD &
    $PSQL << EOD > /dev/null 2>&1 &
begin transaction;
update t set data = 1000 where id = 1 ;

-- wait for the other session to update the rows
select pg_sleep($SLEEP);

update t set data = 1000 where id = 2 ;
commit ;
EOD

sleep 1

  #$PSQL << EOD 
  $PSQL << EOD > /dev/null 2>&1 
begin transaction;
update t set data = 1000 where id = 2 ;
update t set data = 1000 where id = 1 ;
commit ;
EOD

done

# wait some time until the deadlock statistic is updated
sleep 3

$PSQL << EOD
select sum(deadlocks) "deadlocks after" from pg_stat_database ;
EOD

$PSQL << EOD > /dev/null
drop table t;
EOD
