# IBM i

!!! note
    This section is meant for developers that want to understand the working of the IBM i integration.

## Overview

The IBM i integration uses [ODBC][1] to connect to IBM i hosts and 
query system data through an SQL interface. To do so, it uses the [*ODBC Driver for IBM i Access Client Solutions*][2], an IBM propietary [ODBC driver][3] that manages connections to IBM i hosts.

Limitations in the IBM i ODBC driver make it necessary to structure the check in a more complex way than would be expected, to avoid the check from hanging or leaking threads.

### IBM i ODBC driver limitations

ODBC drivers can optionally support custom configuration through *connection attributes*, which help configure how a connection works.
One fundamental connection attribute is `SQL_ATTR_QUERY_TIMEOUT` (and related `_TIMEOUT` attributes), which set the timeout for SQL queries done through the driver (or the timeout for other connection steps for other `_TIMEOUT` attributes).
If this connection attribute is not set there is no timeout, which means the driver gets stuck waiting for a reply when a network issue happens.

As of the writing of this document, the IBM i ODBC driver behavior when setting the `SQL_ATTR_QUERY_TIMEOUT` connection attribute is similar to the one described in [ODBC Query Timeout Property][4]. For the IBM i DB2 driver: the driver estimates the running time of a query and preemptively aborts the query if the estimate is above the specified threshold, but it does not take into account the actual running time of the query (and thus, it's not useful for avoiding network issues).

### IBM i check workaround

To deal with the OBDC driver limitations, the IBM i check needs to have an alternative way to abort a query once a given timeout has passed.
To do so, the IBM i check runs queries in a subprocess which it kills and restarts when timeouts pass. This subprocess runs [`query_script.py`][5] using the embedded Python interpreter.

It is essential that the connection is kept across queries. For a given connection, `ELAPSED_` columns on IBM i views report statistics since the last time the table was queried on that connection, thus if using different connections these values are always zero.

To communicate with the main Agent process, the subprocess and the IBM i check exchange JSON-encoded messages through pipes until the special `ENDOFQUERY` message is received. Special care is needed to avoid blocking on reads and writes of the pipes.

For adding/modifying the queries, the check uses the standard `QueryManager` class used for SQL-based checks, except that each query needs to include a timeout value (since, empirically, some queries take much longer to complete on IBM i hosts).

[1]: https://en.wikipedia.org/wiki/Open_Database_Connectivity
[2]: https://www.ibm.com/support/pages/odbc-driver-ibm-i-access-client-solutions
[3]: https://en.wikipedia.org/wiki/Open_Database_Connectivity#Drivers
[4]: https://www.ibm.com/support/pages/odbc-query-timeout-property-sql0666-estimated-query-processing-time-exceeds-limit
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_i/datadog_checks/ibm_i/query_script.py
