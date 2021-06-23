from datetime import datetime
from typing import List, Type


class Event:
    createdTime: datetime
    key: int
    fullFormattedMessage: str

class EventFilterSpec:
    class ByTime:
        def __init__(self, beginTime: datetime): ...
    time: EventFilterSpec.ByTime
    type: List[Type[Event]]

class EventManager:
    latestEvent: Event
    def QueryEvents(self, filer: EventFilterSpec) -> List[Event]: ...

    def CreateCollectorForEvents(self, filer: EventFilterSpec) -> EventHistoryCollector: ...

class EventHistoryCollector:
    def ReadNextEvents(self, maxCount: int) -> List[Event]: ...
