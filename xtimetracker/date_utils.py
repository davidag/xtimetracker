# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dateutil.parser import parse
from datetime import datetime


def parse_datetime(date_str: str) -> datetime:
    return parse(date_str)
