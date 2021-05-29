# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Unit tests for the 'cli_utils' module."""

import arrow
import collections as co
import csv
import functools
import json
import datetime
import os
import pytest
from io import StringIO
from dateutil.tz import tzutc

from xtimetracker.cli.utils import (
    apply_weekday_offset,
    build_csv,
    flatten_report_for_csv,
    frames_to_csv,
    frames_to_json,
    get_start_time_for_period,
    parse_project,
    parse_tags,
    json_encoder,
)

from . import mock_datetime


_dt = functools.partial(datetime.datetime, tzinfo=tzutc())


@pytest.mark.parametrize(
    "now, mode, start_time",
    [
        (_dt(2016, 6, 2), "year", _dt(2016, 1, 1)),
        (_dt(2016, 6, 2), "month", _dt(2016, 6, 1)),
        (_dt(2016, 6, 2), "week", _dt(2016, 5, 30)),
        (_dt(2016, 6, 2), "day", _dt(2016, 6, 2)),
        (_dt(2016, 6, 2), "full", _dt(1970, 1, 1)),
        (_dt(2012, 2, 24), "year", _dt(2012, 1, 1)),
        (_dt(2012, 2, 24), "month", _dt(2012, 2, 1)),
        (_dt(2012, 2, 24), "week", _dt(2012, 2, 20)),
        (_dt(2012, 2, 24), "day", _dt(2012, 2, 24)),
        (_dt(2012, 2, 24), "full", _dt(1970, 1, 1)),
    ],
)
def test_get_start_time_for_period(now, mode, start_time):
    with mock_datetime(now, datetime):
        assert get_start_time_for_period(mode).datetime == start_time


@pytest.mark.parametrize(
    "monday_start, week_start, new_start",
    [
        ("2018 12 3", "monday", "2018 12 3"),
        ("2018 12 3", "tuesday", "2018 12 4"),
        ("2018 12 3", "wednesday", "2018 12 5"),
        ("2018 12 3", "thursday", "2018 12 6"),
        ("2018 12 3", "friday", "2018 11 30"),
        ("2018 12 3", "saturday", "2018 12 1"),
        ("2018 12 3", "sunday", "2018 12 2"),
        ("2018 12 3", "typo", "2018 12 3"),
    ],
)
def test_apply_weekday_offset(monday_start, week_start, new_start):
    with mock_datetime(_dt(2018, 12, 6), datetime):
        original_start = arrow.get(monday_start, "YYYY MM D")
        result = arrow.get(new_start, "YYYY MM D")
        assert apply_weekday_offset(original_start, week_start) == result


# parse_project


@pytest.mark.parametrize(
    "args, parsed_project",
    [
        (["+ham", "+n", "+eggs"], ""),
        (["ham", "n", "+eggs"], "ham n"),
        (["ham", "+n", "eggs"], "ham"),
        (["ham", "jelly", "eggs", "+food"], "ham jelly eggs"),
    ],
)
def test_parse_project(args, parsed_project):
    project = parse_project(args)
    assert project == parsed_project


# parse_tags


@pytest.mark.parametrize(
    "args, parsed_tags",
    [
        (["+ham", "+n", "+eggs"], ["ham", "n", "eggs"]),
        (["+ham", "n", "+eggs"], ["ham n", "eggs"]),
        (["ham", "n", "+eggs"], ["eggs"]),
        (["ham", "+n", "eggs"], ["n eggs"]),
        (["+ham", "n", "eggs"], ["ham n eggs"]),
    ],
)
def test_parse_tags(args, parsed_tags):
    tags = parse_tags(args)
    assert tags == parsed_tags


# build_csv


def test_build_csv_empty_data():
    assert build_csv([]) == ""


def test_build_csv_one_col():
    lt = os.linesep
    data = [{"col": "value"}, {"col": "another value"}]
    result = lt.join(["col", "value", "another value"]) + lt
    assert build_csv(data) == result


def test_build_csv_multiple_cols():
    lt = os.linesep
    dm = csv.get_dialect("excel").delimiter
    data = [
        co.OrderedDict(
            [("col1", "value"), ("col2", "another value"), ("col3", "more")]
        ),
        co.OrderedDict(
            [("col1", "one value"), ("col2", "two value"), ("col3", "three")]
        ),
    ]
    result = (
        lt.join(
            [
                dm.join(["col1", "col2", "col3"]),
                dm.join(["value", "another value", "more"]),
                dm.join(["one value", "two value", "three"]),
            ]
        )
        + lt
    )
    assert build_csv(data) == result


# frames_to_csv


def test_frames_to_csv_empty_data(timetracker):
    assert frames_to_csv(timetracker.frames) == ""


def test_frames_to_csv(timetracker):
    timetracker.start("foo", tags=["A", "B"])
    timetracker.stop()

    result = frames_to_csv(timetracker.frames)

    read_csv = list(csv.reader(StringIO(result)))
    header = ["id", "start", "stop", "project", "tags"]
    assert len(read_csv) == 2
    assert read_csv[0] == header
    assert read_csv[1][3] == "foo"
    assert read_csv[1][4] == "A, B"


# frames_to_json


def test_frames_to_json_empty_data(timetracker):
    assert frames_to_json(timetracker.frames) == "[]"


def test_frames_to_json(timetracker):
    timetracker.start("foo", tags=["A", "B"])
    timetracker.stop()

    result = json.loads(frames_to_json(timetracker.frames))

    keys = {"id", "start", "stop", "project", "tags"}
    assert len(result) == 1
    assert set(result[0].keys()) == keys
    assert result[0]["project"] == "foo"
    assert result[0]["tags"] == ["A", "B"]


# flatten_report_for_csv


def test_flatten_report_for_csv(timetracker):
    now = arrow.utcnow().ceil("hour")
    timetracker.add("foo", now.shift(hours=-4), now, ["A", "B"])
    timetracker.add("foo", now.shift(hours=-5), now.shift(hours=-4), ["A"])
    timetracker.add("foo", now.shift(hours=-7), now.shift(hours=-5), ["B"])

    start = now.shift(days=-1)
    stop = now
    result = flatten_report_for_csv(timetracker.report(start, stop))

    assert len(result) == 3

    assert result[0]["from"] == start.format("YYYY-MM-DD 00:00:00")
    assert result[0]["to"] == stop.format("YYYY-MM-DD 23:59:59")
    assert result[0]["project"] == "foo"
    assert result[0]["tag"] == ""
    assert result[0]["time"] == (4 + 1 + 2) * 3600

    assert result[1]["from"] == start.format("YYYY-MM-DD 00:00:00")
    assert result[1]["to"] == stop.format("YYYY-MM-DD 23:59:59")
    assert result[1]["project"] == "foo"
    assert result[1]["tag"] == "A"
    assert result[1]["time"] == (4 + 1) * 3600

    assert result[2]["from"] == start.format("YYYY-MM-DD 00:00:00")
    assert result[2]["to"] == stop.format("YYYY-MM-DD 23:59:59")
    assert result[2]["project"] == "foo"
    assert result[2]["tag"] == "B"
    assert result[2]["time"] == (4 + 2) * 3600


# json_encoder


def test_json_encoder():
    with pytest.raises(TypeError):
        json_encoder(0)

    with pytest.raises(TypeError):
        json_encoder("foo")

    with pytest.raises(TypeError):
        json_encoder(None)

    now = arrow.utcnow()
    assert json_encoder(now) == now.for_json()
