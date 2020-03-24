from datetime import datetime
from typing import List

class Event:
    createdTime: datetime

class EventFilterSpec:
    time: ByTime
    class ByTime:
        def __init__(self, beginTime: datetime): ...

class EventManager:
    latestEvent: Event
    def QueryEvents(self, filer: EventFilterSpec) -> List[Event]:
        pass
