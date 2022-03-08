# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


DB_SPACE = {
    "name": "db_space",
    "query": "SELECT t1.DatabaseName,t1.Permspace AS Maxperm,ZEROIFNULL(sum(t2.CurrentPerm)) "
    "AS Currentperm FROM dbc.databases t1 LEFT OUTER JOIN dbc.tablesize t2 "
    "ON (t1.databasename=t2.databasename) WHERE (Maxperm > 0) GROUP BY 1,2 ORDER BY 1;",
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "max_perm", "type": "gauge"},
        {"name": "current_perm", "type": "gauge"},
    ],
}

PCT_SPACE_BY_DB = {
    "name": 'db_space_pct',
    "query": "SELECT Databasename (format 'X(12)'),SUM(maxperm),SUM(currentperm),((cast(SUM(currentperm) "
    "as float))/NULLIFZERO (cast(SUM(maxperm) as float))) (FORMAT 'zz9.99', TITLE 'Percent "
    "// Used')FROM DBC.DiskSpaceV GROUP BY 1;",
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "max_perm.sum", "type": "gauge"},
        {"name": "current_perm.sum", "type": "gauge"},
        {"name": "perm_pct_used", "type": "gauge"},
    ],
}
