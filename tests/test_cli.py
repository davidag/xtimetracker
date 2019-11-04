import json
import re
from itertools import combinations
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

import arrow
import pytest

from watson import cli

from . import TEST_FIXTURE_DIR


# Not all ISO-8601 compliant strings are recognized by arrow.get(str)
VALID_DATES_DATA = [
    ('2018', '2018-01-01 00:00:00'),  # years
    ('2018-04', '2018-04-01 00:00:00'),  # calendar dates
    ('2018-04-10', '2018-04-10 00:00:00'),
    ('2018/04/10', '2018-04-10 00:00:00'),
    ('2018.04.10', '2018-04-10 00:00:00'),
    ('2018-4-10', '2018-04-10 00:00:00'),
    ('2018/4/10', '2018-04-10 00:00:00'),
    ('2018.4.10', '2018-04-10 00:00:00'),
    ('20180410', '2018-04-10 00:00:00'),
    ('2018-123', '2018-05-03 00:00:00'),  # ordinal dates
    ('2018-04-10 12:30:43', '2018-04-10 12:30:43'),
    ('2018-04-10T12:30:43', '2018-04-10 12:30:43'),
    ('2018-04-10 12:30:43Z', '2018-04-10 12:30:43'),
    ('2018-04-10 12:30:43.1233', '2018-04-10 12:30:43'),
    ('2018-04-10 12:30:43+03:00', '2018-04-10 12:30:43'),
    ('2018-04-10 12:30:43-07:00', '2018-04-10 12:30:43'),
    ('2018-04-10T12:30:43-07:00', '2018-04-10 12:30:43'),
    ('2018-04-10 12:30', '2018-04-10 12:30:00'),
    ('2018-04-10T12:30', '2018-04-10 12:30:00'),
    ('2018-04-10 12', '2018-04-10 12:00:00'),
    ('2018-04-10T12', '2018-04-10 12:00:00'),
    (
        '14:05:12',
        arrow.now()
        .replace(hour=14, minute=5, second=12)
        .format('YYYY-MM-DD HH:mm:ss')
    ),
    (
        '14:05',
        arrow.now()
        .replace(hour=14, minute=5, second=0)
        .format('YYYY-MM-DD HH:mm:ss')
    ),
]

INVALID_DATES_DATA = [
    (' 2018'),
    ('2018 '),
    ('201804'),
    ('18-04-10'),
    ('180410'),  # truncated representation not allowed
    ('2018-W08'),  # despite week dates being part of ISO-8601
    ('2018W08'),
    ('2018-W08-2'),
    ('2018W082'),
    ('hello 2018'),
    ('yesterday'),
    ('tomorrow'),
    ('14:05:12.000'),  # Times alone are not allowed
    ('140512.000'),
    ('140512'),
    ('14.05'),
    ('2018-04-10T'),
    ('2018-04-10T12:30:43.'),
]


VALID_TIMES_DATA = [
        ('14:12'),
        ('14:12:43'),
        ('2019-04-10T14:12'),
        ('2019-04-10T14:12:43'),
    ]


class OutputParser:
    FRAME_ID_PATTERN = re.compile(r'id: (?P<frame_id>[0-9a-f]+)')

    @staticmethod
    def _get_frame_id(output):
        return OutputParser.FRAME_ID_PATTERN.search(output).group('frame_id')

    @staticmethod
    def _get_start_date(watson, output):
        frame_id = OutputParser._get_frame_id(output)
        return watson.frames[frame_id].start.format('YYYY-MM-DD HH:mm:ss')


@pytest.mark.parametrize('test_dt,expected', VALID_DATES_DATA)
def test_add_valid_date(runner, watson, test_dt, expected):
    result = runner.invoke(
        cli.add,
        ['-f', test_dt, '-t', test_dt, 'project-name'],
        obj=watson)
    assert result.exit_code == 0
    assert OutputParser._get_start_date(watson, result.output) == expected


@pytest.mark.parametrize('test_dt', INVALID_DATES_DATA)
def test_add_invalid_date(runner, watson, test_dt):
    result = runner.invoke(cli.add,
                           ['-f', test_dt, '-t', test_dt, 'project-name'],
                           obj=watson)
    assert result.exit_code != 0


@pytest.mark.parametrize('test_dt,expected', VALID_DATES_DATA)
def test_aggregate_valid_date(runner, watson, test_dt, expected):
    # This is super fast, because no internal 'report' invocations are made
    result = runner.invoke(cli.aggregate,
                           ['-f', test_dt, '-t', test_dt],
                           obj=watson)
    assert result.exit_code == 0


@pytest.mark.parametrize('test_dt', INVALID_DATES_DATA)
def test_aggregate_invalid_date(runner, watson, test_dt):
    # This is super fast, because no internal 'report' invocations are made
    result = runner.invoke(cli.aggregate,
                           ['-f', test_dt, '-t', test_dt],
                           obj=watson)
    assert result.exit_code != 0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_one_day(runner, watson_df):
    result = runner.invoke(cli.aggregate,
                           ['--json', '-f', '2019-10-31', '-t', '2019-11-01'],
                           obj=watson_df)
    assert result.exit_code == 0
    report = json.loads(result.output)
    total_time = sum(r['time'] for r in report)
    assert total_time == 20001.0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_include_current(runner, watson_df, mocker):
    # Warning: mocking this forces to use arrow.datetime when substracting
    # dates, because Arrow.__sub__() uses isinstance(other, datetime)
    # and after this patch, datetime is no longer a valid type.
    mocker.patch('arrow.arrow.datetime', wraps=datetime)
    start_dt = datetime(2019, 11, 1, 0, 0, 0, tzinfo=tzlocal())
    arrow.arrow.datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ['a-project'], obj=watson_df)
    assert result.exit_code == 0
    # Simulate one hour has elapsed so that the current frame lasts exactly
    # one hour.
    arrow.arrow.datetime.now.return_value = (start_dt + timedelta(hours=1))
    result = runner.invoke(
        cli.aggregate,
        ['-c', '--json', '-f', '2019-10-31', '-t', '2019-11-01'],
        obj=watson_df
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    total_time = sum(r['time'] for r in report)
    assert total_time == 20001.0 + (60 * 60)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_aggregate_dont_include_current(runner, watson_df, mocker):
    mocker.patch('arrow.arrow.datetime', wraps=datetime)
    start_dt = datetime(2019, 11, 1, 0, 0, 0, tzinfo=tzlocal())
    arrow.arrow.datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ['a-project'], obj=watson_df)
    assert result.exit_code == 0
    # Simulate one hour has elapsed so that the current frame lasts exactly
    # one hour.
    arrow.arrow.datetime.now.return_value = (start_dt + timedelta(hours=1))
    result = runner.invoke(
        cli.aggregate,
        ['--json', '-f', '2019-10-31', '-t', '2019-11-01'],
        obj=watson_df
    )
    assert result.exit_code == 0
    report = json.loads(result.output)
    total_time = sum(r['time'] for r in report)
    assert total_time == 20001.0


@pytest.mark.parametrize('cmd', [cli.aggregate, cli.log, cli.report])
def test_incompatible_options(runner, watson, cmd):
    name_interval_options = ['--' + s for s in cli._SHORTCUT_OPTIONS]
    for opt1, opt2 in combinations(name_interval_options, 2):
        result = runner.invoke(cmd, [opt1, opt2], obj=watson)
        assert result.exit_code != 0


@pytest.mark.parametrize('test_dt,expected', VALID_DATES_DATA)
def test_log_valid_date(runner, watson, test_dt, expected):
    result = runner.invoke(cli.log, ['-f', test_dt, '-t', test_dt], obj=watson)
    assert result.exit_code == 0


@pytest.mark.parametrize('test_dt', INVALID_DATES_DATA)
def test_log_invalid_date(runner, watson, test_dt):
    result = runner.invoke(cli.log, ['-f', test_dt, '-t', test_dt], obj=watson)
    assert result.exit_code != 0


@pytest.mark.parametrize('test_dt,expected', VALID_DATES_DATA)
def test_report_valid_date(runner, watson, test_dt, expected):
    result = runner.invoke(cli.report,
                           ['-f', test_dt, '-t', test_dt],
                           obj=watson)
    assert result.exit_code == 0


@pytest.mark.parametrize('test_dt', INVALID_DATES_DATA)
def test_report_invalid_date(runner, watson, test_dt):
    result = runner.invoke(cli.report,
                           ['-f', test_dt, '-t', test_dt],
                           obj=watson)
    assert result.exit_code != 0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
def test_report_one_day(runner, watson_df):
    result = runner.invoke(cli.report,
                           ['--json', '-f', '2019-10-31', '-t', '2019-11-01'],
                           obj=watson_df)
    assert result.exit_code == 0
    report = json.loads(result.output)
    assert report['time'] == 20001.0


@pytest.mark.parametrize('at_dt', VALID_TIMES_DATA)
def test_stop_valid_time(runner, watson, mocker, at_dt):
    mocker.patch('arrow.arrow.datetime', wraps=datetime)
    start_dt = datetime(2019, 4, 10, 14, 0, 0, tzinfo=tzlocal())
    arrow.arrow.datetime.now.return_value = start_dt
    result = runner.invoke(cli.start, ['a-project'], obj=watson)
    assert result.exit_code == 0
    # Simulate one hour has elapsed, so that 'at_dt' is older than now()
    # but newer than the start date.
    arrow.arrow.datetime.now.return_value = (start_dt + timedelta(hours=1))
    result = runner.invoke(cli.stop, ['--at', at_dt], obj=watson)
    assert result.exit_code == 0


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
@pytest.mark.parametrize('all_projects', [
    (['apollo11', 'hubble', 'voyager1', 'voyager2'])])
def test_projects_no_filtering(runner, watson_df, all_projects):
    result = runner.invoke(cli.projects, [], obj=watson_df)
    assert result.exit_code == 0
    assert set(result.output.splitlines()) == set(all_projects)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
@pytest.mark.parametrize('tag, projects', [
    ('antenna', ['voyager1', 'voyager2']),
    ('reactor', ['apollo11']),
    ('lens', ['hubble']),
    ])
def test_projects_filter_by_tag(runner, watson_df, tag, projects):
    result = runner.invoke(cli.projects, [tag], obj=watson_df)
    assert result.exit_code == 0
    assert set(result.output.splitlines()) == set(projects)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
@pytest.mark.parametrize('tags, projects', [
    (['probe', 'sensors', 'antenna'], ['voyager1', 'voyager2']),
    (['probe', 'orbiter', 'sensors', 'antenna'], ['voyager2']),
    (['reactor', 'brakes'], ['apollo11']),
    (['lens', 'reactor'], []),
    ])
def test_projects_filter_by_multiple_tags(runner, watson_df, tags, projects):
    result = runner.invoke(cli.projects, tags, obj=watson_df)
    assert result.exit_code == 0
    assert set(result.output.splitlines()) == set(projects)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
@pytest.mark.parametrize('all_tags', [
    (['reactor', 'module', 'wheels', 'steering', 'brakes', 'lens',
      'camera', 'transmission', 'probe', 'generators', 'sensors',
      'antenna', 'orbiter']),
    ])
def test_tags_no_filtering(runner, watson_df, all_tags):
    result = runner.invoke(cli.tags, [], obj=watson_df)
    assert result.exit_code == 0
    assert set(result.output.splitlines()) == set(all_tags)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
@pytest.mark.parametrize('project, tags', [
    ('', ['reactor', 'module', 'wheels', 'steering', 'brakes', 'lens',
          'camera', 'transmission', 'probe', 'generators', 'sensors',
          'antenna', 'orbiter']),
    ('voyager1', ['probe', 'generators', 'sensors', 'antenna']),
    ('voyager2', ['probe', 'orbiter', 'sensors', 'antenna']),
    ])
def test_tags_filter_by_project(runner, watson_df, project, tags):
    result = runner.invoke(cli.tags, project, obj=watson_df)
    assert result.exit_code == 0
    assert set(result.output.splitlines()) == set(tags)


@pytest.mark.datafiles(TEST_FIXTURE_DIR / "sample_data")
@pytest.mark.parametrize('projects, tags', [
    (['voyager1', 'voyager2'], ['probe', 'sensors', 'antenna']),
    (['hubble', 'apollo11'], []),
    (['voyager1', 'apollo11'], []),
    ])
def test_tags_filter_by_multiple_projects(runner, watson_df, projects, tags):
    result = runner.invoke(cli.tags, projects, obj=watson_df)
    assert result.exit_code == 0
    assert set(result.output.splitlines()) == set(tags)
