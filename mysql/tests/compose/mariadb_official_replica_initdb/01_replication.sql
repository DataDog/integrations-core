-- Point the replica at the primary and start replication. MariaDB uses the classic
-- CHANGE MASTER / START SLAVE syntax with GTID (slave_pos).
CHANGE MASTER TO
  MASTER_HOST='mysql-master',
  MASTER_USER='replica_user',
  MASTER_PASSWORD='replica_password',
  MASTER_USE_GTID=slave_pos;
START SLAVE;
