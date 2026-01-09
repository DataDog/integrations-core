from datetime import datetime, timezone


class MockDatetime:
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 1, 20, 15, 2, 0, tzinfo=tz or timezone.utc)

    @classmethod
    def fromisoformat(cls, iso_string):
        return datetime.fromisoformat(iso_string)
