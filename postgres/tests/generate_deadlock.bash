#!/usr/bin/bash

# This is a stand-alone helper script that generates a deadlock
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

PSQL_ARGS=$*

export PATH=/usr/local/bin:$PATH

PSQL="psql $PSQL_ARGS"
psql $PSQL << EOD > /dev/null
create table t ( id integer, data integer ) ;
insert into t values (1, null);
insert into t values (2, null);
EOD

psql $PSQL << EOD
select sum(deadlocks) "deadlocks before" from pg_stat_database ;
EOD

psql $PSQL << EOD > /dev/null 2>&1 &
begin transaction;
update t set data = 1000 where id = 1 ;

-- wait for the other session to update the rows
select pg_sleep(1);

update t set data = 1000 where id = 2 ;
commit ;
EOD

psql $PSQL << EOD > /dev/null 2>&1
begin transaction;
update t set data = 1000 where id = 2 ;
update t set data = 1000 where id = 1 ;
commit ;
EOD

# wait some time until the deadlock statistic is updated
sleep 2

psql $PSQL << EOD
select sum(deadlocks) "deadlocks after" from pg_stat_database ;
EOD

psql $PSQL << EOD > /dev/null
drop table t;
EOD
