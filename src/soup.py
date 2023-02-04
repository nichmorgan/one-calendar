import requests
from bs4 import BeautifulSoup


def get_soup_from_link(url: str, **kwargs) -> BeautifulSoup:
    response = requests.get(url, **kwargs)
    response.raise_for_status()

    return BeautifulSoup(response.text, "lxml")
