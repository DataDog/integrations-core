import snowflake.connector as sf
import json
from datetime import datetime

con = sf.connect(
    user='DATADOG_USER',
    password='DATADOG_PASS',
    account='lc40619.us-east-2.aws'

)

#result = con.cursor().execute('SELECT * FROM table(inforamtion_schema.query_history()')
# result = con.cursor().execute('SELECT * FROM "SNOWFLAKE"."ACCOUNT_USAGE"."QUERY_HISTORY"')
# print("yes")
# print(result.fetchall())

QUERY_HISTORY_QUERY = 'SELECT * FROM "SNOWFLAKE"."ACCOUNT_USAGE"."QUERY_HISTORY"'
ACCESS_HISTORY_QUERY = 'SELECT * FROM "SNOWFLAKE"."ACCOUNT_USAGE"."ACCESS_HISTORY"'
def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def get_query_history():
    result = con.cursor().execute(QUERY_HISTORY_QUERY + "WHERE START_TIME >= '2023-11-18 21:50:53.881 -0800'")
    print(result.description)
    column_headers = [desc[0] for desc in result.description]
    result_list = [dict(zip(column_headers, row)) for row in result.fetchall()]
    result_json = json.dumps(result_list, indent=2, default=serialize_datetime)
    print(result_json)

def get_access_history():
    result = con.cursor().execute(ACCESS_HISTORY_QUERY + "WHERE QUERY_START_TIME >= '2023-11-18 21:50:53.881 -0800'")
    print(result.description)
    column_headers = [desc[0] for desc in result.description]
    result_list = [dict(zip(column_headers, row)) for row in result.fetchall()]
    result_json = json.dumps(result_list, indent=2, default=serialize_datetime)
    print(result_json)

get_access_history()