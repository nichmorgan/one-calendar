import requests
from typing import Type, Optional
from bs4 import BeautifulSoup, ResultSet
from urllib.parse import urljoin
from datetime import datetime, time
from dateutil.rrule import rrule, MONTHLY
from dataclasses import dataclass


def get_page_from_link(url: str, **kwargs) -> BeautifulSoup:
    response = requests.get(url, **kwargs)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


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
        calendar_page = get_page_from_link(
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
class EventHeader:
    date: datetime
    venue: str
    category: str


@dataclass
class EventBody:
    sponsor: str
    period: str
    start_hour: Optional[time]
    sub_venue: Optional[str]


@dataclass
class Event:
    sponsor: str
    start_date: datetime
    category: str
    period: str
    venue: str
    sub_venue: str

    @classmethod
    def from_components(
        cls: Type["Event"],
        body: EventBody,
        header: EventHeader,
    ) -> "Event":
        start_date = datetime(
            header.date.year,
            header.date.month,
            header.date.day,
            body.start_hour.hour,
            body.start_hour.minute,
        )

        return cls(
            start_date=start_date,
            category=header.category,
            venue=header.venue,
            sponsor=body.sponsor,
            period=body.period,
            sub_venue=body.sub_venue,
        )


class EventScrapper:
    def __get_event_header_date(self) -> datetime:
        #! TODO: Falha em encontrar esta tag!
        date_str = self.__page.find(class_="jubilee-event-date-label").text
        # ? Get the first part from datetime, the hour is trash, ex.: 28/01/2023 00:00
        date_str = date_str.strip().split(maxsplit=1)[0]
        return datetime.strptime(date_str, "%d/%M/%Y")

    def __get_event_header_venue(self) -> str:
        return self.__page.find(id="jubilee-event-venue").text.strip()

    def __get_event_header_category(self) -> str:
        return self.__page.find(id="jubilee-event-category").text.strip()

    def __get_event_header(self) -> EventHeader:
        return EventHeader(
            date=self.__get_event_header_date(),
            venue=self.__get_event_header_venue(),
            category=self.__get_event_header_category(),
        )

    def __get_event_body(self) -> EventBody:
        body_content = self.__page.find(id="jubilee-event-content").text.strip()
        body_dict = {}
        for line in body_content.splitlines():
            key, value = line.split(":")
            body_dict[key] = value.strip() or None

        if body_dict["Hora inicial"]:
            hours, minutes = map(
                int,
                body_dict["Hora inicial"].split(":", maxsplit=2)[:2],
            )
            body_dict["Hora inicial"] = time(hours, minutes)

        return EventBody(
            sponsor=body_dict["Responsável"],
            period=body_dict["Período"],
            start_hour=body_dict["Hora inicial"],
            sub_venue=body_dict["Local 2"],
        )

    def get_event_from_link(self, url: str) -> Event:
        self.__page = get_page_from_link(url)

        body = self.__get_event_body()
        header = self.__get_event_header()
        return Event.from_components(body, header)


EventScrapper().get_event_from_link(
    "https://ipsantoamaro.com.br/eventos/jogupa-koinonia-evangelismo-uppa-e-upa/"
)

# event_links = CalendarScrapper().get_events_links_between_dates(datetime(2023, 12, 31))
