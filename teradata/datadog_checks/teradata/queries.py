# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


DB_SPACE = {
    "name": "db_space",
    "query": "Select t1.DatabaseName,t1.Permspace AS Maxperm,ZEROIFNULL(sum(t2.CurrentPerm)) "
    "AS Currentperm FROM dbc.databases t1 LEFT OUTER JOIN dbc.tablesize t2 "
    "ON (t1.databasename=t2.databasename) WHERE (Maxperm > 0) GROUP BY 1,2 ORDER BY 1;",
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "max_perm", "type": "gauge"},
        {"name": "current_perm", "type": "gauge"},
    ],
}
