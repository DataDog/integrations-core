-- Only configure the channel here; the final server starts it on boot. Starting it in the
-- entrypoint's temporary server lets the shutdown that follows cut the receiver off
-- mid-transaction, and MySQL 9.7.2 then segfaults applying the relay log on the next start.
CHANGE REPLICATION SOURCE TO SOURCE_HOST='mysql-master',SOURCE_USER='replica_user',SOURCE_PASSWORD='replica_password',GET_SOURCE_PUBLIC_KEY=1;
