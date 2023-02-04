import re
import json
from bs4 import ResultSet
from datetime import datetime
from antidote import implements
from urllib.parse import urljoin
from dataclasses import dataclass
from .soup import get_soup_from_link
from dateutil.rrule import rrule, MONTHLY
from typing import Optional, Type, Iterable
from .interface import CalendarScrapper, Event as BaseEvent


@dataclass
class Event(BaseEvent):
    @staticmethod
    def datetime_from_str(value: str) -> datetime:
        if "T" in value:
            return datetime.fromisoformat(value)
        else:
            return datetime.strptime(value, "%Y-%m-%d")

    @staticmethod
    def period_from_datetime(value: datetime) -> str:
        if value.hour < 12:
            return "Manhã"
        elif value.hour < 18:
            return "Tarde"
        elif value.hour < 24:
            return "Noite"
        else:
            return "Indefinido"

    @staticmethod
    def sponsor_from_description(description: str) -> Optional[str]:
        search = re.search(
            "(?<=Responsável:) *(?P<sponsor>.*?) *(?=Período:)",
            description,
        )
        if search:
            return search.groupdict()["sponsor"]
        return None

    @staticmethod
    def subvenue_from_description(description: str) -> Optional[str]:
        sub_venue_details_search = re.search(
            "((?<=Detalhes do local:)|(?<=Local 2:)) *(?P<sub_venue>.*?) *$",
            description,
        )
        if sub_venue_details_search:
            return sub_venue_details_search.groupdict().get("sub_venue", None)

        return None

    @classmethod
    def from_head_script_content(cls: Type["Event"], content: dict) -> "Event":
        description = content["description"].replace("\xa0", "")

        name = content["name"]
        category = content["@type"]
        start_date = cls.datetime_from_str(content["startDate"])
        if content["endDate"]:
            end_date = cls.datetime_from_str(content["endDate"])
        else:
            end_date = None
        period = cls.period_from_datetime(start_date)
        venue = content["location"]["name"]

        sponsor = cls.sponsor_from_description(description)

        subvenue_from_description = cls.subvenue_from_description(description)
        if subvenue_from_description:
            sub_venue = subvenue_from_description
        else:
            sub_venue = content["location"]["address"]["streetAddress"]

        event = cls(
            name=name,
            category=category,
            start_date=start_date,
            end_date=end_date,
            period=period,
            sponsor=sponsor,
            venue=venue,
            sub_venue=sub_venue,
        )
        return event


@implements(CalendarScrapper).as_default
class WebIpsaCalendarScrapper(CalendarScrapper):
    __base_url = "https://ipsantoamaro.com.br"

    def get_events_between_dates(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Iterable[Event]:
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        for date in rrule(MONTHLY, dtstart=start_date, until=end_date):
            month_events_elements = self.__get_month(date)
            for link in self.__get_events_links(month_events_elements):
                yield self.__get_event_from_link(link)

    def __get_event_from_link(self, url: str) -> Event:
        page = get_soup_from_link(url)
        script_content = json.loads(
            page.head.find_all("script", attrs={"type": "application/ld+json"})
            .pop()
            .text
        )

        return self.__from_head_script_content(script_content)

    @staticmethod
    def __get_events_links(events_elements: list) -> list[str]:
        return [elem.attrs["href"].strip() for elem in events_elements]

    def __get_month(self, date: datetime) -> ResultSet:
        url = urljoin(self.__base_url, "/calendario")
        calendar_page = get_soup_from_link(
            url, params={"month": date.strftime("%Y-%m")}
        )
        return calendar_page.find_all(self.__event_filter)

    def __event_filter(self, element) -> bool:
        url = urljoin(self.__base_url, "/eventos")
        is_link = element.name == "a"
        has_data_event_id = "data-event-id" in element.attrs
        is_event_link = element.attrs.get("href", "").strip().startswith(url)

        return is_link and has_data_event_id and is_event_link

    @staticmethod
    def __datetime_from_str(value: str) -> datetime:
        if "T" in value:
            return datetime.fromisoformat(value)
        else:
            return datetime.strptime(value, "%Y-%m-%d")

    @staticmethod
    def __period_from_datetime(value: datetime) -> str:
        if value.hour < 12:
            return "Manhã"
        elif value.hour < 18:
            return "Tarde"
        elif value.hour < 24:
            return "Noite"
        else:
            return "Indefinido"

    @staticmethod
    def __sponsor_from_description(description: str) -> Optional[str]:
        search = re.search(
            "(?<=Responsável:) *(?P<sponsor>.*?) *(?=Período:)",
            description,
        )
        if search:
            return search.groupdict()["sponsor"]
        return None

    @staticmethod
    def __subvenue_from_description(description: str) -> Optional[str]:
        sub_venue_details_search = re.search(
            "((?<=Detalhes do local:)|(?<=Local 2:)) *(?P<sub_venue>.*?) *$",
            description,
        )
        if sub_venue_details_search:
            return sub_venue_details_search.groupdict().get("sub_venue", None)

        return None

    def __from_head_script_content(self, content: dict) -> Event:
        description = content["description"].replace("\xa0", "")

        name = content["name"]
        category = content["@type"]
        start_date = self.__datetime_from_str(content["startDate"])
        if content["endDate"]:
            end_date = self.__datetime_from_str(content["endDate"])
        else:
            end_date = None
        period = self.__period_from_datetime(start_date)
        venue = content["location"]["name"]

        sponsor = self.__sponsor_from_description(description)

        subvenue_from_description = self.__subvenue_from_description(description)
        if subvenue_from_description:
            sub_venue = subvenue_from_description
        else:
            sub_venue = content["location"]["address"]["streetAddress"]

        return Event(
            name=name,
            category=category,
            start_date=start_date,
            end_date=end_date,
            period=period,
            sponsor=sponsor,
            venue=venue,
            sub_venue=sub_venue,
        )
