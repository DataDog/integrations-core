CHANGE REPLICATION SOURCE TO SOURCE_HOST='mysql-master',SOURCE_USER='replica_user',SOURCE_PASSWORD='replica_password',GET_SOURCE_PUBLIC_KEY=1;
-- TEMP (do not merge): fixture warmup starts replication after the final TCP server is ready.
