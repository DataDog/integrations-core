#!/bin/bash

# run processes and store pids in array
pids=()
# Do in batches of 10 to avoid too many open clients
for j in {0..20}; do
for i in {0..19}; do
    id=$((j*20+i))
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" postgres <<-EOSQL &
        CREATE DATABASE dogs_${id};
EOSQL
    pids[i]=$!
done
# wait for all pids
for pid in "${pids[@]}"; do
    wait "$pid"
done
pids=()

done


# for i in {0..100}; do
#     echo "Creating database dogs_$i"
#     psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" postgres "CREATE DATABASE dogs_$i;"
# done