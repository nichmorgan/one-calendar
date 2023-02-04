import abc
from datetime import datetime
from dataclasses import dataclass
from typing import Iterable, Optional
from antidote import interface, injectable


@dataclass
class Event:
    name: str
    sponsor: str
    start_date: datetime
    end_date: Optional[datetime]
    category: str
    period: str
    venue: str
    sub_venue: str


@interface
@injectable
class CalendarScrapper:
    @abc.abstractmethod
    def get_events_between_dates(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Iterable[Event]:
        ...
