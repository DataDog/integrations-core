## On a slave host:
* For MySQL >= 5.7.0
  * If the SQL and the IO threads are running, returns OK
  * If one of them is down, returns WARNING
  * If both are down, returns CRITICAL
* For MySQL < 5.7.0
  * If both threads are running, returns OK
  * If at least one of them is down, returns CRITICAL
* Else, if none of the condition above was satisfied
  * If the IO and the SQL threads are healthy, returns OK
  * Else, returns CRITICAL

## On a master host:
* If `Slave_Running`, `Slave_IO_Running` and `Slave_SQL_Running` are present, but the IO and the SQL thread is not healthy, returns CRTITICAL
* If binary log is enabled and at least 1 binlog_dump is running, returns OK
* If binary log and `nonblocking` option are enabled, MySQL >= 5.6.0 and one worker thread running, returns OK
* Else, returns WARNING
