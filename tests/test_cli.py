# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import json
import re
from itertools import combinations
from datetime import datetime, timedelta
from dateutil.tz import tzlocal
from freezegun import freeze_time

import arrow
import pytest

import xtimetracker.cli as cli

from . import TEST_FIXTURE_DIR


# Not all ISO-8601 compliant strings are recognized by arrow.get(str)
VALID_DATES_DATA = [
    ("2018", "2018-01-01 00:00:00"),  # years
    ("2018-04", "2018-04-01 00:00:00"),  # calendar dates
    ("2018-04-10", "2018-04-10 00:00:00"),
    ("2018/04/10", "2018-04-10 00:00:00"),
    ("2018.04.10", "2018-04-10 00:00:00"),
    ("2018-4-10", "2018-04-10 00:00:00"),
    ("2018/4/10", "2018-04-10 00:00:00"),
    ("2018.4.10", "2018-04-10 00:00:00"),
    ("20180410", "2018-04-10 00:00:00"),
    ("2018-W08", "2018-02-19 00:00:00"),
    ("2018W08", "2018-02-19 00:00:00"),
    ("2018-W08-2", "2018-02-20 00:00:00"),
    ("2018W082", "2018-02-20 00:00:00"),
    ("2018-123", "2018-05-03 00:00:00"),  # ordinal dates
    ("2018-04-10 12:30:43", "2018-04-10 12:30:43"),
    ("2018-04-10T12:30:43", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43Z", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43.1233", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43+03:00", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30:43-07:00", "2018-04-10 12:30:43"),
    ("2018-04-10T12:30:43-07:00", "2018-04-10 12:30:43"),
    ("2018-04-10 12:30", "2018-04-10 12:30:00"),
    ("2018-04-10T12:30", "2018-04-10 12:30:00"),
    ("2018-04-10 12", "2018-04-10 12:00:00"),
    ("2018-04-10T12", "2018-04-10 12:00:00"),
    (
        "14:05:12",
        arrow.now().replace(hour=14, minute=5, second=12).format("YYYY-MM-DD HH:mm:ss"),
    ),
    (
        "14:05",
        arrow.now().replace(hour=14, minute=5, second=0).format("YYYY-MM-DD HH:mm:ss"),
    ),
]

INVALID_DATES_DATA = [
    (" 2018"),
    ("2018 "),
    ("201804"),
    ("18-04-10"),
    ("180410"),  # truncated representation not allowed
    ("hello 2018"),
    ("yesterday"),
    ("tomorrow"),
    ("14:05:12.000"),  # Times alone are not allowed
    ("140512.000"),
    ("140512"),
    ("14.05"),
    ("2018-04-10T"),
    ("2018-04-10T12:30:43."),
]


VALID_TIMES_DATA = [
    ("14:12"),
    ("14:12:43"),
    ("2019-04-10T14:12"),
    ("2019-04-10T14:12:43"),
]


class OutputParser:
    FRAME_ID_PATTERN = re.compile(r"id: (?P<frame_id>[0-9a-f]+)")

    @staticmethod
    def get_frame_id(output):
        return OutputParser.FRAME_ID_PATTERN.search(output).group("frame_id")

    @staticmethod
    def get_start_date(timetracker, output):
        frame_id = OutputParser.get_frame_id(output)
        return timetracker.frames(frame_id).start.format("YYYY-MM-DD HH:mm:ss")


# start


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_start_doesnt_support_frame_references(runner, timetracker_df):
    result = runner.invoke(cli.start, ["-1"], obj=timetracker_df)
    assert result.exit_code == 2  # -1 option not allowed
    frame = timetracker_df.frames("e935a543")
    result = runner.invoke(cli.start, [str(frame.id)], obj=timetracker_df)
    assert result.exit_code == 0
    assert frame.project not in result.output
    assert "e935a543" in result.output


@pytest.mark.parametrize(
    "stop_cfg,error",
    [
        (True, False),
        (False, True),
    ],
)
def test_start_with_already_started_project(runner, timetracker, stop_cfg, error):
    timetracker.config.set("options", "stop_on_start", str(stop_cfg))
    assert timetracker.config.getboolean("options", "stop_on_start") == stop_cfg
    result = runner.invoke(cli.start, "project-1", obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["project-2"], obj=timetracker)
    if error:
        assert result.exit_code == 1
        assert "Error" in result.output
    else:
        assert result.exit_code == 0
        assert "Error" not in result.output


@pytest.mark.parametrize(
    "stretch_opt,stretch_cfg",
    [
        ("-s", True),
        ("-s", False),
        ("", True),
        ("", False),
    ],
)
def test_start_stretching_start_date(
    runner, timetracker, mocker, stretch_opt, stretch_cfg
):
    timetracker.config.set("options", "autostretch_on_start", str(stretch_cfg))
    # Fix start datetime from previous activity
    mocker.patch("arrow.arrow.datetime", wraps=datetime)
    arrow.arrow.datetime.now.return_value = datetime(
        2019, 4, 1, 14, 0, 0, tzinfo=tzlocal()
    )
    # Start and stop previous activity (with a duration of 30 minutes))
    result = runner.invoke(cli.start, ["project-1", "+tag1"], obj=timetracker)
    assert result.exit_code == 0
    arrow.arrow.datetime.now.return_value = datetime(
        2019, 4, 1, 14, 30, 0, tzinfo=tzlocal()
    )
    result = runner.invoke(cli.stop, obj=timetracker)
    assert result.exit_code == 0
    # Start a new activity half hour later
    arrow.arrow.datetime.now.return_value = datetime(
        2019, 4, 1, 15, 0, 0, tzinfo=tzlocal()
    )
    result = runner.invoke(
        cli.start, [stretch_opt, "project-2", "+tag2"], obj=timetracker
    )
    assert result.exit_code == 0
    if stretch_opt or stretch_cfg:
        assert timetracker.current["start"].datetime == datetime(
            2019, 4, 1, 14, 30, 0, tzinfo=tzlocal()
        )
    else:
        assert timetracker.current["start"].datetime == datetime(
            2019, 4, 1, 15, 0, 0, tzinfo=tzlocal()
        )


@pytest.mark.parametrize(
    "elapsed_secs,stretched",
    [
        (120, True),
        (7200, True),
        (28799, True),
        (28800, False),
        (53100, False),
        (153100, False),
    ],
)
def test_start_stretching_previous_day(
    runner, timetracker, mocker, elapsed_secs, stretched
):
    timetracker.config.set("options", "autostretch_on_start", "true")
    # Fix start datetime from previous activity
    mocker.patch("arrow.arrow.datetime", wraps=datetime)
    fixed_dt = datetime(2019, 4, 1, 14, 0, 0, tzinfo=tzlocal())
    arrow.arrow.datetime.now.return_value = fixed_dt
    # Start and stop previous activity (with a duration of 30 minutes))
    result = runner.invoke(cli.start, ["project-1", "+tag1"], obj=timetracker)
    assert result.exit_code == 0
    arrow.arrow.datetime.now.return_value += timedelta(minutes=30)
    result = runner.invoke(cli.stop, obj=timetracker)
    assert result.exit_code == 0
    # Start a new activity on a different day
    arrow.arrow.datetime.now.return_value += timedelta(seconds=elapsed_secs)
    result = runner.invoke(cli.start, ["project-2", "+tag2"], obj=timetracker)
    assert result.exit_code == 0
    if stretched:
        assert timetracker.current["start"].datetime == fixed_dt + timedelta(
            seconds=30 * 60
        )
    else:
        assert timetracker.current["start"].datetime == fixed_dt + timedelta(
            seconds=30 * 60 + elapsed_secs
        )


def test_start_restart_running_frame(runner, timetracker):
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["project-1", "+mytag"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.count() == 0
    result = runner.invoke(cli.start, ["-r"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.count() == 1
    assert timetracker.current["project"] == "project-1"
    assert {"mytag"} == set(timetracker.current["tags"])


def test_start_restart_running_frame_plus_tags(runner, timetracker):
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["project-1", "+tag1"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.count() == 0
    result = runner.invoke(cli.start, ["-r", "+tag2", "+a tag"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert timetracker.count() == 1
    assert set(["tag1", "tag2", "a tag"]) == set(timetracker.current["tags"])


def test_start_restart_latest_frame(runner, timetracker):
    timetracker.config.set("options", "stop_on_start", "false")
    result = runner.invoke(cli.start, "project-1", obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.stop, obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["-r"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert timetracker.count() == 1


def test_start_restart_last_frame_plus_tags(runner, timetracker):
    timetracker.config.set("options", "stop_on_start", "false")
    result = runner.invoke(cli.start, ["project-2", "+tag2"], obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.stop, obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["-r", "+tag3"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.count() == 1
    assert timetracker.current["project"] == "project-2"
    assert set(["tag2", "tag3"]) == set(timetracker.current["tags"])


def test_start_restart_last_project_frame(runner, timetracker):
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(
        cli.add, ["-f 10:00", "-t 11:00", "project-1", "+mytag1"], obj=timetracker
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli.add, ["-f 08:00", "-t 09:00", "project-1", "+mytag2"], obj=timetracker
    )
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["-r", "project-1"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert {"mytag1"} == set(timetracker.current["tags"])


def test_start_restart_last_project_frame_plus_tags(runner, timetracker):
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(
        cli.add, ["-f 10:00", "-t 11:00", "project-1", "+mytag1"], obj=timetracker
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli.add, ["-f 08:00", "-t 09:00", "project-1", "+mytag2"], obj=timetracker
    )
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["-r", "project-1", "+tagA"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert {"tagA", "mytag1"} == set(timetracker.current["tags"])


def test_start_restart_new_project_does_not_fail(runner, timetracker):
    timetracker.config.set("options", "restart_on_start", "true")
    runner.invoke(cli.start, ["project-1"], obj=timetracker)
    assert timetracker.current["project"] == "project-1"


def test_start_restart_config_current_project_explicit_new_tags(runner, timetracker):
    timetracker.config.set("options", "restart_on_start", "true")
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["project-1", "+tag1"], obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["project-1", "+tag2"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert set(["tag1", "tag2"]) == set(timetracker.current["tags"])


def test_start_restart_config_current_project_explicit(runner, timetracker):
    timetracker.config.set("options", "restart_on_start", "true")
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["project-1", "+tag1", "+tag2"], obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["project-1"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert set(["tag1", "tag2"]) == set(timetracker.current["tags"])


def test_start_restart_config_current_project_and_tags_implicit(runner, timetracker):
    timetracker.config.set("options", "restart_on_start", "true")
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["project-1", "+tag1"], obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, [], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert ["tag1"] == timetracker.current["tags"]


def test_start_restart_config_current_project_implicit_same_tags(runner, timetracker):
    timetracker.config.set("options", "restart_on_start", "true")
    timetracker.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["project-1", "+tag1"], obj=timetracker)
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["+tag1"], obj=timetracker)
    assert result.exit_code == 0
    assert timetracker.current["project"] == "project-1"
    assert ["tag1"] == timetracker.current["tags"]


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_start_restart_latest_frame_with_stop_on_start(runner, timetracker_df):
    timetracker_df.config.set("options", "stop_on_start", "true")
    result = runner.invoke(cli.start, ["hubble", "-r"], obj=timetracker_df)
    assert result.exit_code == 0
    assert timetracker_df.current["project"] == "hubble"
    assert {"transmission", "camera"} == set(timetracker_df.current["tags"])


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_start_restart_latest_frame_from_non_running_project(runner, timetracker_df):
    timetracker_df.config.set("options", "stop_on_start", "true")
    result = runner.invoke(
        cli.start, ["voyager1", "+lens", "+reactor"], obj=timetracker_df
    )
    assert result.exit_code == 0
    result = runner.invoke(cli.start, ["hubble", "-r"], obj=timetracker_df)
    assert result.exit_code == 0
    assert timetracker_df.current["project"] == "hubble"
    assert {"transmission", "camera"} == set(timetracker_df.current["tags"])


# cancel


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_cancel(runner, timetracker_df):
    with freeze_time("12:00:00"):
        runner.invoke(cli.start, ["hubble"], obj=timetracker_df)
    with freeze_time("12:15:00"):
        result = runner.invoke(cli.cancel, obj=timetracker_df)
        assert result.output == "Canceled tracking: hubble, started 15 minutes ago\n"


# add


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_add_valid_date(runner, timetracker, test_dt, expected):
    result = runner.invoke(
        cli.add, ["-f", test_dt, "-t", test_dt, "project-name"], obj=timetracker
    )
    assert result.exit_code == 0
    assert OutputParser.get_start_date(timetracker, result.output) == expected


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_add_invalid_date(runner, timetracker, test_dt):
    result = runner.invoke(
        cli.add, ["-f", test_dt, "-t", test_dt, "project-name"], obj=timetracker
    )
    assert result.exit_code != 0


# aggregate


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_aggregate_valid_date(runner, timetracker, test_dt, expected):
    # This is super fast, because no internal 'report' invocations are made
    result = runner.invoke(
        cli.aggregate, ["-f", test_dt, "-t", test_dt], obj=timetracker
    )
    assert result.exit_code == 0


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_aggregate_invalid_date(runner, timetracker, test_dt):
    # This is super fast, because no internal 'report' invocations are made
    result = runner.invoke(
        cli.aggregate, ["-f", test_dt, "-t", test_dt], obj=timetracker
    )
    assert result.exit_code != 0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_exclude_project(runner, timetracker_df):
    result = runner.invoke(cli.aggregate, ["-f", "2019"], obj=timetracker_df)
    assert result.exit_code == 0 and "hubble" in result.output
    result = runner.invoke(
        cli.aggregate, ["-f", "2019", "-P", "hubble"], obj=timetracker_df
    )
    assert result.exit_code == 0 and "hubble" not in result.output


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_exclude_tag(runner, timetracker_df):
    result = runner.invoke(cli.aggregate, ["-f", "2019"], obj=timetracker_df)
    assert result.exit_code == 0 and "reactor" in result.output
    result = runner.invoke(
        cli.aggregate, ["-f", "2019", "-A", "reactor"], obj=timetracker_df
    )
    assert result.exit_code == 0 and "reactor" not in result.output


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_one_day(runner, timetracker_df):
    result = runner.invoke(
        cli.aggregate,
        ["--json", "-f", "2019-10-31", "-t", "2019-11-01"],
        obj=timetracker_df,
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    total_time = sum(r["time"] for r in report)
    assert total_time == 20001.0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_include_current(runner, timetracker_df, mocker):
    # Warning: mocking this forces to use arrow.datetime when substracting
    # dates, because Arrow.__sub__() uses isinstance(other, datetime)
    # and after this patch, datetime is no longer a valid type.
    mocker.patch("arrow.arrow.datetime", wraps=datetime)
    start_dt = datetime(2019, 11, 1, 0, 0, 0, tzinfo=tzlocal())
    arrow.arrow.datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ["a-project"], obj=timetracker_df)
    assert result.exit_code == 0
    # Simulate one hour has elapsed so that the current frame lasts exactly
    # one hour.
    arrow.arrow.datetime.now.return_value = start_dt + timedelta(hours=1)
    result = runner.invoke(
        cli.aggregate,
        ["-c", "--json", "-f", "2019-10-31", "-t", "2019-11-01"],
        obj=timetracker_df,
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    total_time = sum(r["time"] for r in report)
    assert total_time == 20001.0 + (60 * 60)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_dont_include_current(runner, timetracker_df, mocker):
    mocker.patch("arrow.arrow.datetime", wraps=datetime)
    start_dt = datetime(2019, 11, 1, 0, 0, 0, tzinfo=tzlocal())
    arrow.arrow.datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ["a-project"], obj=timetracker_df)
    assert result.exit_code == 0
    # Simulate one hour has elapsed so that the current frame lasts exactly
    # one hour.
    arrow.arrow.datetime.now.return_value = start_dt + timedelta(hours=1)
    result = runner.invoke(
        cli.aggregate,
        ["--json", "-f", "2019-10-31", "-t", "2019-11-01"],
        obj=timetracker_df,
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    total_time = sum(r["time"] for r in report)
    assert total_time == 20001.0


@pytest.mark.parametrize("cmd", [cli.aggregate, cli.log, cli.report])
def test_incompatible_options(runner, timetracker, cmd):
    name_interval_options = ["--" + s for s in cli.SHORTCUT_OPTIONS]
    for opt1, opt2 in combinations(name_interval_options, 2):
        result = runner.invoke(cmd, [opt1, opt2], obj=timetracker)
        assert result.exit_code != 0


# log


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_log_valid_date(runner, timetracker, test_dt, expected):
    result = runner.invoke(cli.log, ["-f", test_dt, "-t", test_dt], obj=timetracker)
    assert result.exit_code == 0


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_log_invalid_date(runner, timetracker, test_dt):
    result = runner.invoke(cli.log, ["-f", test_dt, "-t", test_dt], obj=timetracker)
    assert result.exit_code != 0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_log_one_day(runner, timetracker_df):
    result = runner.invoke(
        cli.log,
        ["--no-pager", "-f", "2019-10-31", "-t", "2019-11-01"],
        obj=timetracker_df,
    )
    assert result.exit_code == 0
    expected_output = [
        "Thursday 31 October 2019 (5h 33m 21s)",
        "\tb19b583  09:13 to 11:20   2h 07m 13s    hubble  [camera]",
        "\tdf5d596  12:03 to 13:38   1h 35m 11s  voyager1  [generators, antenna]",
        "\tecbfea2  14:25 to 15:01      36m 29s    hubble  [transmission, camera]",
        "\t3b3a6b6  15:15 to 16:30   1h 14m 28s  voyager1",
    ]
    assert result.output.splitlines() == expected_output


# report


@pytest.mark.parametrize("test_dt,expected", VALID_DATES_DATA)
def test_report_valid_date(runner, timetracker, test_dt, expected):
    result = runner.invoke(cli.report, ["-f", test_dt, "-t", test_dt], obj=timetracker)
    assert result.exit_code == 0


@pytest.mark.parametrize("test_dt", INVALID_DATES_DATA)
def test_report_invalid_date(runner, timetracker, test_dt):
    result = runner.invoke(cli.report, ["-f", test_dt, "-t", test_dt], obj=timetracker)
    assert result.exit_code != 0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_report_one_day(runner, timetracker_df):
    result = runner.invoke(
        cli.report,
        ["--json", "-f", "2019-10-31", "-t", "2019-11-01"],
        obj=timetracker_df,
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report["time"] == 20001.0
