# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import collections as co
import csv
import datetime
import itertools
import json
import operator
import os
from dateutil import tz
from functools import wraps
from io import StringIO
from typing import List

import arrow
import click
from click.exceptions import UsageError

from ..timetracker import TimeTrackerError, TimeTracker
from ..config import Config


class DateTimeParamType(click.ParamType):
    name = "datetime"

    def convert(self, value, param, ctx):
        if value:
            date = self._parse_multiformat(value)
            if date is None:
                raise click.UsageError(
                    "Could not match value '{}' to any supported date format".format(
                        value
                    )
                )
            # Add an offset to match the week beginning specified in the
            # configuration
            if param.name == "week":
                week_start = ctx.obj.config.get("options", "week_start", "monday")
                date = apply_weekday_offset(start_time=date, week_start=week_start)
            return date

    def _parse_multiformat(self, value) -> arrow.Arrow:
        date = None
        for fmt in (None, "HH:mm:ss", "HH:mm"):
            try:
                if fmt is None:
                    # -> try to parse value as ISO-8601 string as local tz
                    date = arrow.get(value, tzinfo=tz.tzlocal())
                else:
                    date = arrow.get(value, fmt)
                    # -> arrow.now() returns the current time in local tz, then replace h:m:s
                    date = arrow.now().replace(
                        hour=date.hour, minute=date.minute, second=date.second
                    )
                break
            except (ValueError, TypeError):
                pass
        return date


DateTime = DateTimeParamType()


def catch_timetracker_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TimeTrackerError as e:
            raise click.ClickException(style("error", str(e)))

    return wrapper


def create_timetracker(config: Config) -> TimeTracker:
    return TimeTracker(config=config)


def create_configuration(contents=None, config_dir=None) -> Config:
    if config_dir is None:
        config_dir = os.environ.get(
            "XTIMETRACKER_DIR", click.get_app_dir("xtimetracker")
        )

    c = Config(config_dir=config_dir, interpolation=None)
    c.reload(contents)
    return c


def style(name, element):
    def _style_tags(tags):
        if not tags:
            return ""

        return "[{}]".format(", ".join(style("tag", tag) for tag in tags))

    def _style_short_id(id):
        return style("id", id[:7])

    formats = {
        "project": {"fg": "magenta"},
        "tags": _style_tags,
        "tag": {"fg": "blue"},
        "time": {"fg": "green"},
        "error": {"fg": "red"},
        "date": {"fg": "cyan"},
        "datetime": {"fg": "cyan"},
        "short_id": _style_short_id,
        "id": {"fg": "white"},
    }

    fmt = formats.get(name, {})

    if isinstance(fmt, dict):
        return click.style(element, **fmt)
    else:
        # The fmt might be a function if we need to do some computation
        return fmt(element)


def format_timedelta(delta: datetime.timedelta):
    """
    Return a string roughly representing a timedelta.
    """
    seconds = int(delta.total_seconds())
    neg = seconds < 0
    seconds = abs(seconds)
    total = seconds
    stems = []

    if total >= 3600:
        hours = seconds // 3600
        stems.append("{}h".format(hours))
        seconds -= hours * 3600

    if total >= 60:
        mins = seconds // 60
        stems.append("{:02}m".format(mins))
        seconds -= mins * 60

    stems.append("{:02}s".format(seconds))

    return ("-" if neg else "") + " ".join(stems)


def format_date(date: arrow.Arrow) -> str:
    datetime_format = "YYYY-MM-DD HH:mm:ss"
    return date.format(datetime_format)


def parse_date(date: str) -> arrow.Arrow:
    datetime_format = "YYYY-MM-DD HH:mm:ss"
    return arrow.get(date, datetime_format, tzinfo=tz.tzlocal())


def options(opt_list):
    """
    Wrapper for the `value_proc` field in `click.prompt`, which validates
    that the user response is part of the list of accepted responses.
    """

    def value_proc(user_input):
        if user_input in opt_list:
            return user_input
        else:
            raise UsageError(
                "Response should be one of [{}]".format(
                    ",".join(str(x) for x in opt_list)
                )
            )

    return value_proc


def get_start_time_for_period(period):
    # Using now() from datetime instead of arrow for mocking compatibility.
    now = arrow.Arrow.fromdatetime(datetime.datetime.now())
    date = now.date()

    day = date.day
    month = date.month
    year = date.year

    weekday = now.weekday()

    if period == "day":
        start_time = arrow.Arrow(year, month, day)
    elif period == "week":
        start_time = arrow.Arrow.fromdate(now.shift(days=-weekday).date())
    elif period == "month":
        start_time = arrow.Arrow(year, month, 1)
    elif period == "year":
        start_time = arrow.Arrow(year, 1, 1)
    elif period == "full":
        start_time = arrow.get(0)
    else:
        raise ValueError("Unsupported period value: {}".format(period))

    return start_time


def apply_weekday_offset(start_time: arrow.Arrow, week_start: str) -> arrow.Arrow:
    """
    Apply the offset required to move the start date `start_time` of a week
    starting on Monday to that of a week starting on `week_start`.
    """
    weekdays = dict(
        zip(
            [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ],
            range(0, 7),
        )
    )

    new_start = week_start.lower()
    if new_start not in weekdays:
        return start_time
    now = datetime.datetime.now()
    offset = weekdays[new_start] - 7 * (weekdays[new_start] > now.weekday())
    # -> Array.shift(days=)
    return start_time.shift(days=offset)


def parse_project(values_list: List[str]) -> str:
    """
    Return a string with the project name.

    Concatenate all values until one is a tag (ie. starts with '+').
    """
    return " ".join(itertools.takewhile(lambda s: not s.startswith("+"), values_list))


def parse_tags(values_list: List[str]) -> List[str]:
    """
    Return a list of tags parsed from the input values list.

    Find all the tags starting by a '+', even if there are spaces in them,
    then strip each tag and filter out the empty ones
    """
    return list(
        filter(
            None,
            map(
                operator.methodcaller("strip"),
                (
                    # We concatenate the word with the '+' to the following words
                    # not starting with a '+'
                    w[1:]
                    + " "
                    + " ".join(
                        itertools.takewhile(
                            lambda s: not s.startswith("+"), values_list[i + 1 :]
                        )
                    )
                    for i, w in enumerate(values_list)
                    if w.startswith("+")
                ),
            ),
        )
    )  # pile of pancakes !


def frames_to_json(frames):
    """
    Transform a sequence of frames into a JSON-formatted string.

    Each frame object has an equivalent pair name/value in the JSON string,
    except for 'updated_at', which is not included.

    .. seealso:: :class:`Frame`
    """
    log = [
        co.OrderedDict(
            [
                ("id", frame.id),
                ("start", frame.start.isoformat()),
                ("stop", frame.stop.isoformat()),
                ("project", frame.project),
                ("tags", frame.tags),
            ]
        )
        for frame in frames
    ]
    return json.dumps(log, indent=4, sort_keys=True)


def frames_to_csv(frames):
    """
    Transform a sequence of frames into a CSV-formatted string.

    Each frame object has an equivalent pair name/value in the CSV string,
    except for 'updated_at', which is not included.

    .. seealso:: :class:`Frame`
    """
    entries = [
        co.OrderedDict(
            [
                ("id", frame.id[:7]),
                ("start", frame.start.format("YYYY-MM-DD HH:mm:ss")),
                ("stop", frame.stop.format("YYYY-MM-DD HH:mm:ss")),
                ("project", frame.project),
                ("tags", ", ".join(frame.tags)),
            ]
        )
        for frame in frames
    ]
    return build_csv(entries)


def build_csv(entries):
    """
    Creates a CSV string from a list of dict objects.

    The dictionary keys of the first item in the list are used as the header
    row for the built CSV. All item's keys are supposed to be identical.
    """
    if entries:
        header = entries[0].keys()
    else:
        return ""
    memfile = StringIO()
    writer = csv.DictWriter(memfile, header, lineterminator=os.linesep)
    writer.writeheader()
    writer.writerows(entries)
    output = memfile.getvalue()
    memfile.close()
    return output


def flatten_report_for_csv(report):
    """
    Flattens the data structure returned by `timetracker.report()` for a csv
    export.

    Dates are formatted in a way that Excel (default csv module dialect) can
    handle them (i.e. YYYY-MM-DD HH:mm:ss).

    The result is a list of dictionaries where each element can contain two
    different things:

    1. The total `time` spent in a project during the report interval. In this
       case, the `tag` value will be empty.
    2. The partial `time` spent in a tag and project during the report
       interval. In this case, the `tag` value will contain a tag associated
       with the project.

    The sum of all elements where `tag` is empty corresponds to the total time
    of the report.
    """
    result = []
    # -> Arrow.format()
    datetime_from = report["timespan"]["from"].format("YYYY-MM-DD HH:mm:ss")
    datetime_to = report["timespan"]["to"].format("YYYY-MM-DD HH:mm:ss")
    for project in report["projects"]:
        result.append(
            {
                "from": datetime_from,
                "to": datetime_to,
                "project": project["name"],
                "tag": "",
                "time": project["time"],
            }
        )
        for tag in project["tags"]:
            result.append(
                {
                    "from": datetime_from,
                    "to": datetime_to,
                    "project": project["name"],
                    "tag": tag["name"],
                    "time": tag["time"],
                }
            )
    return result


def build_json(entries):
    """
    Creates a JSON string from a list of dict objects.
    """
    return json.dumps(entries, indent=4, sort_keys=True, default=json_encoder)


def json_encoder(obj):
    """
    Encodes objects for JSON output.

    :param obj: Object to encode
    :return: JSON representation of object
    """
    if isinstance(obj, arrow.Arrow):
        return obj.for_json()

    raise TypeError("Object {} is not JSON serializable".format(obj))


def adjusted_span(
    timetracker: TimeTracker, from_: arrow.Arrow, to: arrow.Arrow, include_current: bool
):
    """
    Returns the number of days in interval adjusted to existing frame interval
    """
    span = timetracker.full_span(include_current)
    if from_ < span.start:
        from_ = span.start
    if to > span.stop:
        to = span.stop
    return from_, to
