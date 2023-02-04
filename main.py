from datetime import datetime
from antidote import inject, world, instanceOf
from src.interface import CalendarScrapper


@inject
def run(scrapper: CalendarScrapper = world[instanceOf(CalendarScrapper).single()]):
    start_date = datetime.today()
    end_date = datetime(2023, 12, 31)
    event_gen = scrapper.get_events_between_dates(start_date, end_date)
    for i, event in enumerate(event_gen):
        print(event)
        if i == 10:
            break


if __name__ == "__main__":
    run()
