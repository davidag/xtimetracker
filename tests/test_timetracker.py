"""Unit tests for the main 'timetracker' module."""

import json
import os
from io import StringIO

import arrow
import pytest

from tt import TimeTracker, TimeTrackerError
from tt.timetracker import ConfigParser, ConfigurationError

from . import mock_read


@pytest.fixture
def json_mock(mocker):
    return mocker.patch.object(
        json, 'dumps', side_effect=json.dumps, autospec=True
    )


# NOTE: All timestamps need to be > 3600 to avoid breaking the tests on
# Windows.

def test_make_json_writer():
    fp = StringIO()
    writer = TimeTracker._make_json_writer(lambda: {'foo': 42})
    writer(fp)
    assert fp.getvalue() == '{\n "foo": 42\n}'


def test_make_json_writer_with_args():
    fp = StringIO()
    writer = TimeTracker._make_json_writer(lambda x: {'foo': x}, 23)
    writer(fp)
    assert fp.getvalue() == '{\n "foo": 23\n}'


def test_make_json_writer_with_kwargs():
    fp = StringIO()
    writer = TimeTracker._make_json_writer(
        lambda foo=None: {'foo': foo}, foo='bar')
    writer(fp)
    assert fp.getvalue() == '{\n "foo": "bar"\n}'


def test_make_json_writer_with_unicode():
    fp = StringIO()
    writer = TimeTracker._make_json_writer(lambda: {'ùñï©ôð€': 'εvεrywhεrε'})
    writer(fp)
    expected = '{\n "ùñï©ôð€": "εvεrywhεrε"\n}'
    assert fp.getvalue() == expected


# current

def test_current(mocker, timetracker):
    content = json.dumps({'project': 'foo', 'start': 4000, 'tags': ['A', 'B']})

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert timetracker.current['project'] == 'foo'
    assert timetracker.current['start'] == arrow.get(4000)
    assert timetracker.current['tags'] == ['A', 'B']


def test_current_with_empty_file(mocker, timetracker):
    mocker.patch('builtins.open', mocker.mock_open(read_data=""))
    mocker.patch('os.path.getsize', return_value=0)
    assert timetracker.current == {}


def test_current_with_nonexistent_file(mocker, timetracker):
    mocker.patch('builtins.open', side_effect=IOError)
    assert timetracker.current == {}


def test_current_timetracker_non_valid_json(mocker, timetracker):
    content = "{'foo': bar}"

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    mocker.patch('os.path.getsize', return_value=len(content))
    with pytest.raises(TimeTrackerError):
        timetracker.current


def test_current_with_given_state(config_dir, mocker):
    content = json.dumps({'project': 'foo', 'start': 4000})
    timetracker = TimeTracker(current={'project': 'bar', 'start': 4000},
                              config_dir=config_dir)

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert timetracker.current['project'] == 'bar'


def test_current_with_empty_given_state(config_dir, mocker):
    content = json.dumps({'project': 'foo', 'start': 4000})
    timetracker = TimeTracker(current=[], config_dir=config_dir)

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert timetracker.current == {}


# frames

def test_frames(mocker, timetracker):
    content = json.dumps([[4000, 4010, 'foo', None, ['A', 'B', 'C']]])

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert len(timetracker.frames) == 1
    assert timetracker.frames[0].project == 'foo'
    assert timetracker.frames[0].start == arrow.get(4000)
    assert timetracker.frames[0].stop == arrow.get(4010)
    assert timetracker.frames[0].tags == ['A', 'B', 'C']


def test_frames_without_tags(mocker, timetracker):
    content = json.dumps([[4000, 4010, 'foo', None]])

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert len(timetracker.frames) == 1
    assert timetracker.frames[0].project == 'foo'
    assert timetracker.frames[0].start == arrow.get(4000)
    assert timetracker.frames[0].stop == arrow.get(4010)
    assert timetracker.frames[0].tags == []


def test_frames_with_empty_file(mocker, timetracker):
    mocker.patch('builtins.open', mocker.mock_open(read_data=""))
    mocker.patch('os.path.getsize', return_value=0)
    assert len(timetracker.frames) == 0


def test_frames_with_nonexistent_file(mocker, timetracker):
    mocker.patch('builtins.open', side_effect=IOError)
    assert len(timetracker.frames) == 0


def test_frames_timetracker(mocker, timetracker):
    content = "{'foo': bar}"

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    mocker.patch('os.path.getsize', return_value=len(content))
    with pytest.raises(TimeTrackerError):
        timetracker.frames


def test_given_frames(config_dir, mocker):
    content = json.dumps([[4000, 4010, 'foo', None, ['A']]])
    timetracker = TimeTracker(frames=[[4000, 4010, 'bar', None, ['A', 'B']]],
                              config_dir=config_dir)

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert len(timetracker.frames) == 1
    assert timetracker.frames[0].project == 'bar'
    assert timetracker.frames[0].tags == ['A', 'B']


def test_frames_with_empty_given_state(config_dir, mocker):
    content = json.dumps([[0, 10, 'foo', None, ['A']]])
    timetracker = TimeTracker(frames=[], config_dir=config_dir)

    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    assert len(timetracker.frames) == 0


# config

def test_empty_config_dir():
    timetracker = TimeTracker()
    assert timetracker._dir == ''


def test_wrong_config(mocker, timetracker):
    content = """
toto
    """
    mocker.patch.object(ConfigParser, 'read', mock_read(content))
    with pytest.raises(ConfigurationError):
        timetracker.config


def test_empty_config(mocker, timetracker):
    mocker.patch.object(ConfigParser, 'read', mock_read(''))
    assert len(timetracker.config.sections()) == 0


# start

def test_start_new_project(timetracker):
    timetracker.start('foo', ['A', 'B'])

    assert timetracker.current != {}
    assert timetracker.is_started is True
    assert timetracker.current.get('project') == 'foo'
    assert isinstance(timetracker.current.get('start'), arrow.Arrow)
    assert timetracker.current.get('tags') == ['A', 'B']


def test_start_new_project_without_tags(timetracker):
    timetracker.start('foo')

    assert timetracker.current != {}
    assert timetracker.is_started is True
    assert timetracker.current.get('project') == 'foo'
    assert isinstance(timetracker.current.get('start'), arrow.Arrow)
    assert timetracker.current.get('tags') == []


def test_start_two_projects(timetracker):
    timetracker.start('foo')

    with pytest.raises(AssertionError):
        timetracker.start('bar')

    assert timetracker.current != {}
    assert timetracker.current['project'] == 'foo'
    assert timetracker.is_started is True


def test_start_default_tags(mocker, timetracker):
    content = """
[default_tags]
my project = A B
    """

    mocker.patch.object(ConfigParser, 'read', mock_read(content))
    timetracker.start('my project')
    assert timetracker.current['tags'] == ['A', 'B']


def test_start_default_tags_with_supplementary_input_tags(mocker, timetracker):
    content = """
[default_tags]
my project = A B
    """

    mocker.patch.object(ConfigParser, 'read', mock_read(content))
    timetracker.start('my project', tags=['C', 'D'])
    assert timetracker.current['tags'] == ['C', 'D', 'A', 'B']


def test_start_nogap(timetracker):

    timetracker.start('foo')
    timetracker.stop()
    timetracker.start('bar', gap=False)

    assert timetracker.frames[-1].stop == timetracker.current['start']


# stop

def test_stop_started_project(timetracker):
    timetracker.start('foo', tags=['A', 'B'])
    timetracker.stop()

    assert timetracker.current == {}
    assert timetracker.is_started is False
    assert len(timetracker.frames) == 1
    assert timetracker.frames[0].project == 'foo'
    assert isinstance(timetracker.frames[0].start, arrow.Arrow)
    assert isinstance(timetracker.frames[0].stop, arrow.Arrow)
    assert timetracker.frames[0].tags == ['A', 'B']


def test_stop_started_project_without_tags(timetracker):
    timetracker.start('foo')
    timetracker.stop()

    assert timetracker.current == {}
    assert timetracker.is_started is False
    assert len(timetracker.frames) == 1
    assert timetracker.frames[0].project == 'foo'
    assert isinstance(timetracker.frames[0].start, arrow.Arrow)
    assert isinstance(timetracker.frames[0].stop, arrow.Arrow)
    assert timetracker.frames[0].tags == []


def test_stop_no_project(timetracker):
    with pytest.raises(TimeTrackerError):
        timetracker.stop()


def test_stop_started_project_at(timetracker):
    timetracker.start('foo')
    now = arrow.now()

    with pytest.raises(TimeTrackerError):
        time_str = '1970-01-01T00:00'
        time_obj = arrow.get(time_str)
        timetracker.stop(stop_at=time_obj)

    with pytest.raises(ValueError):
        time_str = '2999-31-12T23:59'
        time_obj = arrow.get(time_str)
        timetracker.stop(stop_at=time_obj)

    timetracker.stop(stop_at=now)
    assert timetracker.frames[-1].stop == now


# cancel

def test_cancel_started_project(timetracker):
    timetracker.start('foo')
    timetracker.cancel()

    assert timetracker.current == {}
    assert len(timetracker.frames) == 0


def test_cancel_no_project(timetracker):
    with pytest.raises(TimeTrackerError):
        timetracker.cancel()


# save

def test_save_without_changes(mocker, timetracker, json_mock):
    mocker.patch('builtins.open', mocker.mock_open())
    timetracker.save()

    assert not json_mock.called


def test_save_current(mocker, timetracker, json_mock):
    timetracker.start('foo', ['A', 'B'])

    mocker.patch('builtins.open', mocker.mock_open())
    timetracker.save()

    assert json_mock.call_count == 1
    result = json_mock.call_args[0][0]
    assert result['project'] == 'foo'
    assert isinstance(result['start'], (int, float))
    assert result['tags'] == ['A', 'B']


def test_save_current_without_tags(mocker, timetracker, json_mock):
    timetracker.start('foo')

    mocker.patch('builtins.open', mocker.mock_open())
    timetracker.save()

    assert json_mock.call_count == 1
    result = json_mock.call_args[0][0]
    assert result['project'] == 'foo'
    assert isinstance(result['start'], (int, float))
    assert result['tags'] == []

    dump_args = json_mock.call_args[1]
    assert dump_args['ensure_ascii'] is False


def test_save_empty_current(config_dir, mocker, json_mock):
    timetracker = TimeTracker(current={}, config_dir=config_dir)

    mocker.patch('builtins.open', mocker.mock_open())

    timetracker.current = {'project': 'foo', 'start': 4000}
    timetracker.save()

    assert json_mock.call_count == 1
    result = json_mock.call_args[0][0]
    assert result == {'project': 'foo', 'start': 4000, 'tags': []}

    timetracker.current = {}
    timetracker.save()

    assert json_mock.call_count == 2
    result = json_mock.call_args[0][0]
    assert result == {}


def test_save_frames_no_change(config_dir, mocker, json_mock):
    timetracker = TimeTracker(frames=[[4000, 4010, 'foo', None]],
                              config_dir=config_dir)

    mocker.patch('builtins.open', mocker.mock_open())
    timetracker.save()

    assert not json_mock.called


def test_save_added_frame(config_dir, mocker, json_mock):
    timetracker = TimeTracker(
        frames=[[4000, 4010, 'foo', None]], config_dir=config_dir)
    timetracker.frames.add('bar', 4010, 4020, ['A'])

    mocker.patch('builtins.open', mocker.mock_open())
    timetracker.save()

    assert json_mock.call_count == 1
    result = json_mock.call_args[0][0]
    assert len(result) == 2
    assert result[0][2] == 'foo'
    assert result[0][4] == []
    assert result[1][2] == 'bar'
    assert result[1][4] == ['A']


def test_save_changed_frame(config_dir, mocker, json_mock):
    timetracker = TimeTracker(frames=[[4000, 4010, 'foo', None, ['A']]],
                              config_dir=config_dir)
    timetracker.frames[0] = ('bar', 4000, 4010, ['A', 'B'])

    mocker.patch('builtins.open', mocker.mock_open())
    timetracker.save()

    assert json_mock.call_count == 1
    result = json_mock.call_args[0][0]
    assert len(result) == 1
    assert result[0][2] == 'bar'
    assert result[0][4] == ['A', 'B']

    dump_args = json_mock.call_args[1]
    assert dump_args['ensure_ascii'] is False


def test_save_config_no_changes(mocker, timetracker):
    mocker.patch('builtins.open', mocker.mock_open())
    write_mock = mocker.patch.object(ConfigParser, 'write')
    timetracker.save()

    assert not write_mock.called


def test_save_config(mocker, timetracker):
    mocker.patch('builtins.open', mocker.mock_open())
    write_mock = mocker.patch.object(ConfigParser, 'write')
    timetracker.config = ConfigParser()
    timetracker.save()

    assert write_mock.call_count == 1


def test_timetracker_save_calls_safe_save(mocker, config_dir, timetracker):
    frames_file = os.path.join(config_dir, 'frames')
    timetracker.start('foo', tags=['A', 'B'])
    timetracker.stop()

    save_mock = mocker.patch('tt.timetracker.safe_save')
    timetracker.save()

    assert timetracker._frames.changed
    assert save_mock.call_count == 1
    assert len(save_mock.call_args[0]) == 2
    assert save_mock.call_args[0][0] == frames_file


# projects

def test_projects(timetracker):
    for name in ('foo', 'bar', 'bar', 'bar', 'foo', 'lol'):
        timetracker.frames.add(name, 4000, 4000)

    assert timetracker.projects() == ['bar', 'foo', 'lol']


def test_projects_no_frames(timetracker):
    assert timetracker.projects() == []


# tags

def test_tags(timetracker):
    samples = (
        ('foo', ('A', 'D')),
        ('bar', ('A', 'C')),
        ('foo', ('B', 'C')),
        ('lol', ()),
        ('bar', ('C'))
    )

    for name, tags in samples:
        timetracker.frames.add(name, 4000, 4000, tags)

    assert timetracker.tags() == ['A', 'B', 'C', 'D']


def test_tags_no_frames(timetracker):
    assert timetracker.tags() == []


# report

def test_report(timetracker):
    timetracker.start('foo', tags=['A', 'B'])
    timetracker.stop()

    report = timetracker.report(arrow.now(), arrow.now())
    assert 'time' in report
    assert 'timespan' in report
    assert 'from' in report['timespan']
    assert 'to' in report['timespan']
    assert len(report['projects']) == 1
    assert report['projects'][0]['name'] == 'foo'
    assert len(report['projects'][0]['tags']) == 2
    assert report['projects'][0]['tags'][0]['name'] == 'A'
    assert 'time' in report['projects'][0]['tags'][0]
    assert report['projects'][0]['tags'][1]['name'] == 'B'
    assert 'time' in report['projects'][0]['tags'][1]

    timetracker.start('bar', tags=['C'])
    timetracker.stop()

    report = timetracker.report(arrow.now(), arrow.now())
    assert len(report['projects']) == 2
    assert report['projects'][0]['name'] == 'bar'
    assert report['projects'][1]['name'] == 'foo'
    assert len(report['projects'][0]['tags']) == 1
    assert report['projects'][0]['tags'][0]['name'] == 'C'

    report = timetracker.report(
        arrow.now(), arrow.now(), projects=['foo'], tags=['B']
    )
    assert len(report['projects']) == 1
    assert report['projects'][0]['name'] == 'foo'
    assert len(report['projects'][0]['tags']) == 1
    assert report['projects'][0]['tags'][0]['name'] == 'B'

    timetracker.start('baz', tags=['D'])
    timetracker.stop()

    report = timetracker.report(arrow.now(), arrow.now(), projects=["foo"])
    assert len(report['projects']) == 1

    report = timetracker.report(
        arrow.now(), arrow.now(), ignore_projects=["bar"])
    assert len(report['projects']) == 2

    report = timetracker.report(arrow.now(), arrow.now(), tags=["A"])
    assert len(report['projects']) == 1

    report = timetracker.report(arrow.now(), arrow.now(), ignore_tags=["D"])
    assert len(report['projects']) == 2

    with pytest.raises(TimeTrackerError):
        timetracker.report(
            arrow.now(), arrow.now(), projects=["foo"], ignore_projects=["foo"]
        )

    with pytest.raises(TimeTrackerError):
        timetracker.report(
            arrow.now(), arrow.now(), tags=["A"], ignore_tags=["A"])


@pytest.mark.parametrize(
    "date_as_unixtime,sum_", (
        (3600 * 24, 7200.0),
        (3600 * 48, 3600.0),
    )
)
def test_report_include_partial_frames(mocker, timetracker, date_as_unixtime,
                                       sum_):
    """Test report building with frames that cross report boundaries

    1 event is added that has 2 hours in one day and 1 in the next.
    """
    content = json.dumps([[
        3600 * 46,
        3600 * 49,
        "programming",
        "3e76c820909840f89cabaf106ab7d12a",
        ["cli"],
        1548797432
    ]])
    mocker.patch('builtins.open', mocker.mock_open(read_data=content))
    date = arrow.get(date_as_unixtime)
    report = timetracker.report(
        from_=date, to=date
    )
    assert report["time"] == pytest.approx(sum_, abs=1e-3)


# rename

def test_rename_project_with_time(timetracker):
    """
    Renaming a project should update the "last_updated" time on any frame that
    contains that project.
    """
    timetracker.frames.add(
        'foo', 4001, 4002, ['some_tag'],
        id='c76d1ad0282c429595cc566d7098c165', updated_at=4005
    )
    timetracker.frames.add(
        'bar', 4010, 4015, ['other_tag'],
        id='eed598ff363d42658a095ae6c3ae1088', updated_at=4035
    )

    timetracker.rename_project("foo", "baz")

    assert len(timetracker.frames) == 2

    assert timetracker.frames[0].id == 'c76d1ad0282c429595cc566d7098c165'
    assert timetracker.frames[0].project == 'baz'
    assert timetracker.frames[0].start.timestamp == 4001
    assert timetracker.frames[0].stop.timestamp == 4002
    assert timetracker.frames[0].tags == ['some_tag']
    # assert timetracker.frames[0].updated_at.timestamp == 9000
    assert timetracker.frames[0].updated_at.timestamp > 4005

    assert timetracker.frames[1].id == 'eed598ff363d42658a095ae6c3ae1088'
    assert timetracker.frames[1].project == 'bar'
    assert timetracker.frames[1].start.timestamp == 4010
    assert timetracker.frames[1].stop.timestamp == 4015
    assert timetracker.frames[1].tags == ['other_tag']
    assert timetracker.frames[1].updated_at.timestamp == 4035


def test_rename_tag_with_time(timetracker):
    """
    Renaming a tag should update the "last_updated" time on any frame that
    contains that tag.
    """
    timetracker.frames.add(
        'foo', 4001, 4002, ['some_tag'],
        id='c76d1ad0282c429595cc566d7098c165', updated_at=4005
    )
    timetracker.frames.add(
        'bar', 4010, 4015, ['other_tag'],
        id='eed598ff363d42658a095ae6c3ae1088', updated_at=4035
    )

    timetracker.rename_tag("other_tag", "baz")

    assert len(timetracker.frames) == 2

    assert timetracker.frames[0].id == 'c76d1ad0282c429595cc566d7098c165'
    assert timetracker.frames[0].project == 'foo'
    assert timetracker.frames[0].start.timestamp == 4001
    assert timetracker.frames[0].stop.timestamp == 4002
    assert timetracker.frames[0].tags == ['some_tag']
    assert timetracker.frames[0].updated_at.timestamp == 4005

    assert timetracker.frames[1].id == 'eed598ff363d42658a095ae6c3ae1088'
    assert timetracker.frames[1].project == 'bar'
    assert timetracker.frames[1].start.timestamp == 4010
    assert timetracker.frames[1].stop.timestamp == 4015
    assert timetracker.frames[1].tags == ['baz']
    # assert timetracker.frames[1].updated_at.timestamp == 9000
    assert timetracker.frames[1].updated_at.timestamp > 4035


# add

def test_add_success(timetracker):
    """
    Adding a new frame outside of live tracking successfully
    """
    timetracker.add(project="test_project", tags=['fuu', 'bar'],
                    from_date=6000, to_date=7000)

    assert len(timetracker.frames) == 1
    assert timetracker.frames[0].project == "test_project"
    assert 'fuu' in timetracker.frames[0].tags


def test_add_failure(timetracker):
    """
    Adding a new frame outside of live tracking fails when
    to date is before from date
    """
    with pytest.raises(TimeTrackerError):
        timetracker.add(project="test_project", tags=['fuu', 'bar'],
                        from_date=7000, to_date=6000)


def test_validate_inclusion_options(timetracker):
    assert timetracker._validate_inclusion_options(["project_foo"], None)
    assert timetracker._validate_inclusion_options(None, ["project_foo"])
    assert not timetracker._validate_inclusion_options(["project_foo"],
                                                       ["project_foo"])
    assert timetracker._validate_inclusion_options(["project_foo"],
                                                   ["project_bar"])
    assert not timetracker._validate_inclusion_options(
        ["project_foo", "project_bar"],
        ["project_foo"])
    assert not timetracker._validate_inclusion_options(
        ["project_foo", "project_bar"],
        ["project_foo", "project_bar"])
    assert timetracker._validate_inclusion_options(None, None)
