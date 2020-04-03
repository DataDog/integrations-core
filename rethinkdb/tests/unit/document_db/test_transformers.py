import datetime as dt

import pytz

from datadog_checks.rethinkdb.document_db import transformers


def test_to_time_elapsed():
    # type: () -> None
    one_day_seconds = 3600 * 24
    transformers.to_time_elapsed(dt.datetime.now(pytz.utc) - dt.timedelta(days=1)) == one_day_seconds
