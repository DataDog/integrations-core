# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
PROCESS = 'SELECT PROGRAM, {} FROM GV$PROCESS'
SYSTEM = 'SELECT METRIC_NAME, VALUE, BEGIN_TIME FROM GV$SYSMETRIC ORDER BY BEGIN_TIME'
TABLESPACE = """\
select
  m.tablespace_name,
  m.used_space * t.block_size as used_bytes,
  m.tablespace_size * t.block_size as max_bytes,
  m.used_percent
from
  dba_tablespace_usage_metrics m
  join dba_tablespaces t on m.tablespace_name = t.tablespace_name;
"""
