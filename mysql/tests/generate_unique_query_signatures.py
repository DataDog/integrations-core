# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import common
import pymysql

conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root', password=None)
cursor = conn.cursor()
for i in range(10000):
    cursor.execute("SELECT 1 qxxx{} from performance_schema.threads limit 1".format(str(i)))
conn.close()
