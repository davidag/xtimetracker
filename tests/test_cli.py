import re
import arrow
from itertools import combinations
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

from click.testing import CliRunner
import pytest

from watson import cli, frames


class TestCliCmd:

    cli_runner = CliRunner()

    # Not all ISO-8601 compliant strings are recognized by arrow.get(str)
    valid_dates_data = [
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

    invalid_dates_data = [
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

    @staticmethod
    def _run(watson, cmd, args):
        return TestCliCmd.cli_runner.invoke(cmd, args, obj=watson)

    @staticmethod
    def _run_cmd_from_to(watson, cmd, from_dt, to_dt, *extra_args):
        args = []
        if from_dt:
            args += ['--from', from_dt]
        if to_dt:
            args += ['--to', to_dt]
        for arg in extra_args:
            args.append(arg)
        return TestCliCmd._run(
            watson,
            cmd,
            args
        )


class TestCliAddCmd(TestCliCmd):

    frame_id_pattern = re.compile(r'id: (?P<frame_id>[0-9a-f]+)')
    @pytest.mark.parametrize('test_dt,expected', TestCliCmd.valid_dates_data)
    def test_valid_date(self, watson, test_dt, expected):
        result = self._run_add(watson, test_dt, test_dt)
        assert result.exit_code == 0
        assert self._get_start_date(watson, result.output) == expected

    @pytest.mark.parametrize('test_dt', TestCliCmd.invalid_dates_data)
    def test_invalid_date(self, watson, test_dt):
        result = self._run_add(watson, test_dt, test_dt)
        assert result.exit_code != 0

    def _run_add(self, watson, from_dt, to_dt):
        return TestCliCmd._run(
            watson,
            cli.add,
            ['--from', from_dt, '--to', to_dt, 'project-name']
        )

    def _get_frame_id(self, output):
        return self.frame_id_pattern.search(output).group('frame_id')

    def _get_start_date(self, watson, output):
        frame_id = self._get_frame_id(output)
        return watson.frames[frame_id].start.format('YYYY-MM-DD HH:mm:ss')


class TestCliAggregateCmd(TestCliCmd):

    @pytest.mark.parametrize('test_dt,expected', TestCliCmd.valid_dates_data)
    def test_valid_date(self, watson, test_dt, expected):
        # This is super fast, because no internal 'report' invocations are made
        result = TestCliCmd._run_cmd_from_to(
            watson, cli.aggregate, test_dt, test_dt
        )
        assert result.exit_code == 0

    @pytest.mark.parametrize('test_dt', TestCliCmd.invalid_dates_data)
    def test_invalid_date(self, watson, test_dt):
        # This is super fast, because no internal 'report' invocations are made
        result = TestCliCmd._run_cmd_from_to(
            watson, cli.aggregate, test_dt, test_dt
        )
        assert result.exit_code != 0

    def test_empty_json_output(self, mocker, watson):
        result = TestCliCmd._run_cmd_from_to(
            watson, cli.aggregate, None, None, '--json'
        )
        assert result.exit_code == 0


class TestCliLogCmd(TestCliCmd):

    def test_incompatible_options(self, watson):
        name_interval_options = ['--' + s for s in cli._SHORTCUT_OPTIONS]
        for opt1, opt2 in combinations(name_interval_options, 2):
            result = self._run(watson, cli.log, [opt1, opt2])
            assert result.exit_code != 0

    @pytest.mark.parametrize('test_dt,expected', TestCliCmd.valid_dates_data)
    def test_valid_date(self, watson, test_dt, expected):
        result = TestCliCmd._run_cmd_from_to(watson, cli.log, test_dt, test_dt)
        assert result.exit_code == 0

    @pytest.mark.parametrize('test_dt', TestCliCmd.invalid_dates_data)
    def test_invalid_date(self, watson, test_dt):
        result = TestCliCmd._run_cmd_from_to(watson, cli.log, test_dt, test_dt)
        assert result.exit_code != 0


class TestCliReportCmd(TestCliCmd):

    def test_incompatible_options(self, watson):
        name_interval_options = ['--' + s for s in cli._SHORTCUT_OPTIONS]
        for opt1, opt2 in combinations(name_interval_options, 2):
            result = TestCliCmd._run(watson, cli.log, [opt1, opt2])
            assert result.exit_code != 0

    @pytest.mark.parametrize('test_dt,expected', TestCliCmd.valid_dates_data)
    def test_valid_date(self, watson, test_dt, expected):
        result = TestCliCmd._run_cmd_from_to(
            watson, cli.report, test_dt, test_dt
        )
        assert result.exit_code == 0

    @pytest.mark.parametrize('test_dt', TestCliCmd.invalid_dates_data)
    def test_invalid_date(self, watson, test_dt):
        result = TestCliCmd._run_cmd_from_to(
            watson, cli.report, test_dt, test_dt
        )
        assert result.exit_code != 0

    def test_empty_json_output(self, mocker, watson):
        result = TestCliCmd._run_cmd_from_to(
            watson, cli.report, None, None, '--json'
        )
        assert result.exit_code == 0


class TestCliStopCmd(TestCliCmd):

    valid_times_data = [
        ('14:12'),
        ('14:12:43'),
        ('2019-04-10T14:12'),
        ('2019-04-10T14:12:43'),
    ]
    start_dt = datetime(2019, 4, 10, 14, 0, 0, tzinfo=tzlocal())

    @pytest.mark.parametrize('at_dt', valid_times_data)
    def test_valid_time(self, mocker, watson, at_dt):
        mocker.patch('arrow.arrow.datetime', wraps=datetime)
        result = self._run_start(watson)
        assert result.exit_code == 0
        result = self._run_stop(watson, at_dt)
        assert result.exit_code == 0

    def _run_start(self, watson):
        arrow.arrow.datetime.now.return_value = self.start_dt
        return TestCliCmd._run(watson, cli.start, ['project-name'])

    def _run_stop(self, watson, at_dt):
        # Simulate one hour has elapsed, so that 'at_dt' is older than now()
        # but newer than the start date.
        arrow.arrow.datetime.now.return_value = (
            self.start_dt + timedelta(hours=1)
        )
        # The --at parameter is the only option that uses 'TimeParamType'
        return TestCliCmd._run(watson, cli.stop, ['--at', at_dt])
