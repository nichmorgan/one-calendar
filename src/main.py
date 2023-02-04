import requests
from typing import Type, Optional
from bs4 import BeautifulSoup, ResultSet
from urllib.parse import urljoin
from datetime import datetime, time
from dateutil.rrule import rrule, MONTHLY
from dataclasses import dataclass
import re
import json


def get_soup_from_link(url: str, **kwargs) -> BeautifulSoup:
    response = requests.get(url, **kwargs)
    response.raise_for_status()

    return BeautifulSoup(response.text, "lxml")


class CalendarScrapper:
    __base_url = "https://ipsantoamaro.com.br"

    def get_events_links_between_dates(
        self,
        end_date: datetime,
        start_date: datetime = datetime.today(),
    ) -> list[str]:
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        event_links = []
        for date in rrule(MONTHLY, dtstart=start_date, until=end_date):
            month_events_elements = self.__get_month(date)
            event_links.extend(self.__get_events_links(month_events_elements))

        return event_links

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
            "((?<=Detalhes do local:)|(?<=Local 2:)) *(\\xa0)?(?P<sub_venue>.*?) *$",
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


class EventScrapper:
    def get_event_from_link(self, url: str) -> Event:
        self.__page = get_soup_from_link(url)
        script_content = json.loads(
            self.__page.head.find_all("script", attrs={"type": "application/ld+json"})
            .pop()
            .text
        )

        return Event.from_head_script_content(script_content)


event_links = CalendarScrapper().get_events_links_between_dates(datetime(2023, 12, 31))[
    :10
]
scrapper = EventScrapper()
events_list = []
for link in event_links:
    event = scrapper.get_event_from_link(link)
    events_list.append(event)
print(events_list)
