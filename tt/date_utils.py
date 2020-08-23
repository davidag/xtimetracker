from dateutil.parser import parse
from datetime import datetime


def parse_datetime(date_str: str) -> datetime:
    return parse(date_str)
