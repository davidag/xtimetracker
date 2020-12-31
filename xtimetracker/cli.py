# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import datetime
import json
import operator
from functools import reduce, wraps

import arrow
import click
from dateutil import tz

from . import __version__
from .autocompletion import (
    get_frames,
    get_project_or_tag_completion,
    get_projects,
    get_tags,
)
from .config import create_configuration
from .file_utils import safe_save
from .frames import Frame
from .timetracker import TimeTrackerError, TimeTracker
from .cli_utils import (
    adjusted_span,
    apply_weekday_offset,
    build_csv,
    build_json,
    create_timetracker,
    flatten_report_for_csv,
    format_timedelta,
    frames_to_csv,
    frames_to_json,
    get_frame_from_argument,
    get_last_frame_from_project,
    get_start_time_for_period,
    is_current_tracking_data,
    style,
    parse_project,
    parse_tags,
)
from .utils import sorted_groupby


class MutuallyExclusiveOption(click.Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.name in opts:
            if self.mutually_exclusive.intersection(opts):
                self._raise_exclusive_error()
            if self.multiple and len(set(opts[self.name])) > 1:
                self._raise_exclusive_error()
        return super(MutuallyExclusiveOption, self).handle_parse_result(
            ctx, opts, args
        )

    def _raise_exclusive_error(self):
        # Use self.opts[-1] instead of self.name to handle options with a
        # different internal name.
        self.mutually_exclusive.add(self.opts[-1].strip('-'))
        raise click.ClickException(
            style(
                'error',
                'The following options are mutually exclusive: '
                '{options}'.format(options=', '.join(
                    ['`--{}`'.format(_) for _ in self.mutually_exclusive]))))


class DateTimeParamType(click.ParamType):
    name = 'datetime'

    def convert(self, value, param, ctx):
        if value:
            date = self._parse_multiformat(value)
            if date is None:
                raise click.UsageError(
                    "Could not match value '{}' to any supported date format"
                    .format(value)
                )
            # Add an offset to match the week beginning specified in the
            # configuration
            if param.name == "week":
                week_start = ctx.obj.config.get(
                    "options", "week_start", "monday")
                date = apply_weekday_offset(
                    start_time=date, week_start=week_start)
            return date

    def _parse_multiformat(self, value) -> arrow.Arrow:
        date = None
        for fmt in (None, 'HH:mm:ss', 'HH:mm'):
            try:
                if fmt is None:
                    # -> try to parse value as ISO-8601 string as local tz
                    date = arrow.get(value, tzinfo=tz.tzlocal())
                else:
                    date = arrow.get(value, fmt)
                    # -> arrow.now() returns the current time in local tz, then replace h:m:s
                    date = arrow.now().replace(
                        hour=date.hour,
                        minute=date.minute,
                        second=date.second
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
            raise click.ClickException(style('error', str(e)))
    return wrapper


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name='x')
@click.pass_context
def cli(ctx):
    """
    xtimetracker is a tool aimed for monitoring your time.
    """

    # This is the main command group, needed by click in order
    # to handle the subcommands
    ctx.obj = create_timetracker(create_configuration())

    if ctx.invoked_subcommand is None:
        ctx.invoke(status)


@cli.command()
@click.argument('command', required=False)
@click.pass_context
def help(ctx, command):
    """
    Display help information
    """
    if not command:
        click.echo(ctx.parent.get_help())
        return

    cmd = cli.get_command(ctx, command)

    if not cmd:
        raise click.ClickException("No such command: {}".format(command))

    # the passed context is that of the 'help' command, which would
    # show up in the Usage: ... - message. Create the proper context:
    cmd_context = click.Context(cmd, parent=ctx.parent, info_name=cmd.name)
    click.echo(cmd.get_help(cmd_context))


@cli.command()
@click.option('-s', '--stretch', is_flag=True, default=False,
              help=("Stretch start time to continue after last tracked activity."))
@click.option('-r', '--restart', is_flag=True, default=False,
              help="Restart last frame or last project frame if a project "
                   "is provided.")
@click.argument('args', nargs=-1,
                autocompletion=get_project_or_tag_completion)
@click.pass_obj
@click.pass_context
@catch_timetracker_error
def start(ctx, timetracker: TimeTracker, stretch, restart, args):
    """
    Start monitoring time for the given project.
    You can add tags indicating more specifically what you are working on with
    `+tag`.

    If there is an already running project and the configuration option
    `options.stop_on_start` is true, it will be stopped before the new
    project is started.
    """
    stop_flag = timetracker.config.getboolean('options', 'stop_on_start')
    restart_flag = restart or timetracker.config.getboolean('options', 'restart_on_start')
    stretch_flag = stretch or timetracker.config.getboolean('options', 'autostretch_on_start')

    project = parse_project(args)
    tags = parse_tags(args)

    if not project and not restart_flag:
        raise click.ClickException("No project given.")

    if restart_flag and timetracker.is_started:
        tags.extend(timetracker.current['tags'])
        if not project:
            project = timetracker.current['project']

    if restart_flag and not timetracker.is_started:
        if project:
            frame = get_last_frame_from_project(timetracker, project)
        else:
            frame = get_frame_from_argument(timetracker, "-1")
        if frame:
            project = frame.project
            tags.extend(frame.tags)

    if timetracker.is_started:
        if stop_flag and not is_current_tracking_data(timetracker, project, tags):
            ctx.invoke(stop)
        else:
            raise click.ClickException(
                style('error', "Project {} is already started with tags '{}'".format(
                    timetracker.current['project'], ", ".join(timetracker.current["tags"]))
                )
            )

    current = timetracker.start(project, tags, stretch_flag)
    click.echo("Starting project {}{} at {}".format(
        style('project', project),
        (" " if current['tags'] else "") + style('tags', current['tags']),
        style('time', "{:HH:mm}".format(current['start']))
    ))
    timetracker.save()


@cli.command(context_settings={'ignore_unknown_options': True})
@click.option('-c', '--cancel', is_flag=True, default=False,
              help="Cancel current project monitoring.")
@click.pass_obj
@catch_timetracker_error
def stop(timetracker, cancel):
    """
    Stop or cancel monitoring time for the current project.
    """
    if cancel:
        old = timetracker.cancel()
        click.echo("Canceling current monitoring for project {}{}".format(
            style('project', old['project']),
            (" " if old['tags'] else "") + style('tags', old['tags'])
        ))
    else:
        frame = timetracker.stop()
        output_str = "Stopping project {}{}, started {} and stopped {}. (id: {})"
        click.echo(output_str.format(
            style('project', frame.project),
            (" " if frame.tags else "") + style('tags', frame.tags),
            # -> Arrow.humanize() just to output start/stop datetimes...
            style('time', frame.start.humanize()),
            style('time', frame.stop.humanize()),
            style('short_id', frame.id),
        ))
    timetracker.save()


@cli.command(hidden=True)
@click.option('-p', '--project', is_flag=True,
              help="only output project")
@click.option('-t', '--tags', is_flag=True,
              help="only show tags")
@click.option('-e', '--elapsed', is_flag=True,
              help="only show time elapsed")
@click.pass_obj
@catch_timetracker_error
def status(timetracker, project, tags, elapsed):
    """
    Display the currently recorded project.

    The displayed date and time format can be configured with options
    `options.date_format` and `options.time_format`.
    """
    if not timetracker.is_started:
        click.echo("No project started.")
        return

    current = timetracker.current

    if project:
        click.echo("{}".format(
            style('project', current['project']),
        ))
        return

    if tags:
        click.echo("{}".format(
            style('tags', current['tags'])
        ))
        return

    if elapsed:
        click.echo("{}".format(
            style('time', current['start'].humanize())
        ))
        return

    datefmt = timetracker.config.get('options', 'date_format', '%Y.%m.%d')
    timefmt = timetracker.config.get('options', 'time_format', '%H:%M:%S%z')
    click.echo("Project {}{} started {} ({} {})".format(
        style('project', current['project']),
        (" " if current['tags'] else "") + style('tags', current['tags']),
        # -> humanize() start date
        style('time', current['start'].humanize()),
        # -> Arrow.strftime() to output time formatted with user preferences...
        style('date', current['start'].strftime(datefmt)),
        style('time', current['start'].strftime(timefmt))
    ))


@cli.command(context_settings={'ignore_unknown_options': True})
@click.argument('args', nargs=-1,
                autocompletion=get_project_or_tag_completion)
@click.option('-f', '--from', 'from_', required=True, type=DateTime,
              help="Date and time of start of tracked activity")
@click.option('-t', '--to', required=True, type=DateTime,
              help="Date and time of end of tracked activity")
@click.pass_obj
@catch_timetracker_error
def add(timetracker, args, from_, to):
    """
    Add time to a project with tag(s) that was not tracked live.
    """
    project = parse_project(args)
    if not project:
        raise click.ClickException("No project given.")

    # Parse all the tags
    tags = parse_tags(args)

    # add a new frame, call timetracker save to update state files
    frame = timetracker.add(
        project=project, tags=tags, from_date=from_, to_date=to)

    click.echo(
        "Adding project {}{}, started {} and stopped {}. (id: {})".format(
            style('project', frame.project),
            (" " if frame.tags else "") + style('tags', frame.tags),
            style('time', frame.start.humanize()),
            style('time', frame.stop.humanize()),
            style('short_id', frame.id)
        )
    )
    timetracker.save()


_SHORTCUT_OPTIONS = ['full', 'year', 'month', 'week', 'day']
_SHORTCUT_OPTIONS_VALUES = {
    k: get_start_time_for_period(k) for k in _SHORTCUT_OPTIONS
}


@cli.command()
@click.option('-c/-C', '--current/--no-current', 'current', default=None,
              help="(Don't) include currently running frame in report.")
@click.option('-f', '--from', 'from_', cls=MutuallyExclusiveOption,
              type=DateTime, default=arrow.now().shift(days=-7),
              mutually_exclusive=_SHORTCUT_OPTIONS,
              help="Report start date. Default: 7 days ago.")
@click.option('-t', '--to', cls=MutuallyExclusiveOption, type=DateTime,
              default=arrow.now(),
              mutually_exclusive=_SHORTCUT_OPTIONS,
              help="Report stop date (inclusive). Default: tomorrow.")
@click.option('-y', '--year', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['year'],
              mutually_exclusive=['day', 'week', 'month', 'full'],
              help='Report current year.')
@click.option('-m', '--month', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['month'],
              mutually_exclusive=['day', 'week', 'year', 'full'],
              help='Report current month.')
@click.option('-w', '--week', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['week'],
              mutually_exclusive=['day', 'month', 'year', 'full'],
              help='Report current week.')
@click.option('-d', '--day', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['day'],
              mutually_exclusive=['week', 'month', 'year', 'full'],
              help='Report current day.')
@click.option('-u', '--full', 'full', cls=MutuallyExclusiveOption,
              type=DateTime, flag_value=_SHORTCUT_OPTIONS_VALUES['full'],
              mutually_exclusive=['day', 'week', 'month', 'year'],
              help='Report full interval.')
@click.option('-p', '--project', 'projects', autocompletion=get_projects,
              multiple=True,
              help="Include project in the report and exclude all others. "
              "It can be used multiple times.")
@click.option('-P', '--exclude-project', 'exclude_projects', multiple=True,
              help="Exclude project from the report. "
              "It can be used multiple times.")
@click.option('-a', '--tag', 'tags', autocompletion=get_tags, multiple=True,
              help="Include only frames with the given tag. "
              "It can be used multiple times.")
@click.option('-A', '--exclude-tag', 'exclude_tags', multiple=True,
              help="Exclude tag from the report. "
              "It can be used multiple times.")
@click.option('-j', '--json', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='json', mutually_exclusive=['csv'],
              multiple=True,
              help="Output JSON format.")
@click.option('-s', '--csv', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='csv', mutually_exclusive=['json'],
              multiple=True,
              help="Output CSV format.")
@click.option('--plain', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='plain', mutually_exclusive=['json', 'csv'],
              multiple=True, default=True, hidden=True,
              help="Format output in plain text (default)")
@click.option('-g/-G', '--pager/--no-pager', 'pager', default=None,
              help="(Don't) view output through a pager.")
@click.pass_obj
@catch_timetracker_error
def report(timetracker, current, from_, to, projects, exclude_projects, tags,
           exclude_tags, year, month, week, day, full, output_format,
           pager, aggregated=False):
    """
    Display a report of the time spent on each project.

    By default, the time spent the last 7 days is printed.
    """
    # if the report is an aggregate report, add whitespace using this
    # aggregate tab which will be prepended to the project name
    if aggregated:
        tab = '  '
    else:
        tab = ''

    report = timetracker.report(from_, to, current, projects, tags,
                                exclude_projects, exclude_tags,
                                year=year, month=month, week=week, day=day,
                                full=full)

    if 'json' in output_format and not aggregated:
        click.echo(build_json(report))
        return
    elif 'csv' in output_format and not aggregated:
        click.echo(build_csv(flatten_report_for_csv(report)))
        return
    elif 'plain' not in output_format and aggregated:
        return report

    lines = []
    # use the pager, or print directly to the terminal
    if pager or (pager is None and timetracker.config.getboolean('options', 'pager', True)):

        def _print(line):
            lines.append(line)

        def _final_print(lines):
            click.echo_via_pager('\n'.join(lines))
    elif aggregated:

        def _print(line):
            lines.append(line)

        def _final_print(lines):
            pass
    else:

        def _print(line):
            click.echo(line)

        def _final_print(lines):
            pass

    # handle special title formatting for aggregate reports
    if aggregated:
        _print('{} - {}'.format(
            style('date', '{:ddd DD MMMM YYYY}'.format(
                report['timespan']['from']
            )),
            style('time', '{}'.format(format_timedelta(
                datetime.timedelta(seconds=report['time'])
            )))
        ))

    else:
        _print('{} -> {}\n'.format(
            style('date', '{:ddd DD MMMM YYYY}'.format(
                report['timespan']['from']
            )),
            style('date', '{:ddd DD MMMM YYYY}'.format(
                report['timespan']['to']
            ))
        ))

    projects = report['projects']

    for project in projects:
        _print('{tab}{project} - {time}'.format(
            tab=tab,
            time=style('time', format_timedelta(
                datetime.timedelta(seconds=project['time'])
            )),
            project=style('project', project['name'])
        ))

        tags = project['tags']
        if tags:
            longest_tag = max(len(tag) for tag in tags or [''])

            for tag in tags:
                _print('\t[{tag} {time}]'.format(
                    time=style('time', '{:>11}'.format(format_timedelta(
                        datetime.timedelta(seconds=tag['time'])
                    ))),
                    tag=style('tag', '{:<{}}'.format(
                        tag['name'], longest_tag
                    )),
                ))
        _print("")

    # only show total time at the bottom for a project if it is not
    # an aggregate report and there is greater than 1 project
    if len(projects) > 1 and not aggregated:
        _print('Total: {}'.format(
            style('time', '{}'.format(format_timedelta(
                datetime.timedelta(seconds=report['time'])
            )))
        ))

    # if this is a report invoked from `aggregate`
    # return the lines
    if aggregated:
        return lines
    else:
        _final_print(lines)


@cli.command()
@click.option('-c/-C', '--current/--no-current', 'include_current', default=None,
              help="(Don't) include currently running frame in report.")
@click.option('-f', '--from', 'from_', cls=MutuallyExclusiveOption,
              type=DateTime, default=arrow.now().shift(days=-7),
              mutually_exclusive=_SHORTCUT_OPTIONS,
              help="Report start date. Default: 7 days ago.")
@click.option('-t', '--to', cls=MutuallyExclusiveOption, type=DateTime,
              default=arrow.now(),
              mutually_exclusive=_SHORTCUT_OPTIONS,
              help="Report stop date (inclusive). Default: tomorrow.")
@click.option('-p', '--project', 'projects', autocompletion=get_projects,
              multiple=True,
              help="Include project in the report and exclude all others."
              "It can be used multiple times.")
@click.option('-P', '--exclude-project', 'exclude_projects', multiple=True,
              help="Exclude project from the report. "
              "It can be used multiple times.")
@click.option('-a', '--tag', 'tags', autocompletion=get_tags, multiple=True,
              help="Reports activity only for frames containing the given "
              "tag. It can be used multiple times.")
@click.option('-A', '--exclude-tag', 'exclude_tags', multiple=True,
              help="Reports activity for all tags but the given ones. "
              "It can be used multiple times.")
@click.option('-j', '--json', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='json', mutually_exclusive=['csv'],
              multiple=True,
              help="Format output in JSON instead of plain text")
@click.option('-s', '--csv', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='csv', mutually_exclusive=['json'],
              multiple=True,
              help="Format output in CSV instead of plain text")
@click.option('--plain', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='plain', mutually_exclusive=['json', 'csv'],
              multiple=True, default=True, hidden=True,
              help="Format output in plain text (default)")
@click.option('-g/-G', '--pager/--no-pager', 'pager', default=None,
              help="(Don't) view output through a pager.")
@click.pass_obj
@click.pass_context
@catch_timetracker_error
def aggregate(ctx, timetracker, include_current, from_, to, projects, exclude_projects,
              tags, exclude_tags, output_format, pager):
    """
    Display a report of the time spent on each project aggregated by day.

    By default, the time spent the last 7 days is printed.
    """
    from_, to = adjusted_span(timetracker, from_, to, include_current)
    delta = (to.datetime - from_.datetime).days
    lines = []
    for i in range(delta + 1):
        offset = datetime.timedelta(days=i)
        from_offset = from_ + offset
        output = ctx.invoke(report, current=include_current, from_=from_offset,
                            to=from_offset, projects=projects,
                            exclude_projects=exclude_projects,
                            tags=tags,
                            exclude_tags=exclude_tags,
                            output_format=output_format,
                            pager=pager, aggregated=True)

        if 'json' in output_format:
            lines.append(output)
        elif 'csv' in output_format:
            lines.extend(flatten_report_for_csv(output))
        else:
            # if there is no activity for the day, append a newline
            # this ensures even spacing throughout the report
            if (len(output)) == 1:
                output[0] += '\n'

            lines.append('\n'.join(output))

    if 'json' in output_format:
        click.echo(build_json(lines))
    elif 'csv' in output_format:
        click.echo(build_csv(lines))
    elif pager or (pager is None and timetracker.config.getboolean('options', 'pager', True)):
        click.echo_via_pager('\n\n'.join(lines))
    else:
        click.echo('\n\n'.join(lines))


@cli.command()
@click.option('-c/-C', '--current/--no-current', 'current', default=None,
              help="(Don't) include currently running frame in output.")
@click.option('-f', '--from', 'from_', type=DateTime,
              default=arrow.now().shift(days=-7),
              help="Log start date. Default: 7 days ago.")
@click.option('-t', '--to', type=DateTime, default=arrow.now(),
              help="Log stop date (inclusive). Default: tomorrow.")
@click.option('-y', '--year', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['year'],
              mutually_exclusive=['day', 'week', 'month', 'full'],
              help='Report current year.')
@click.option('-m', '--month', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['month'],
              mutually_exclusive=['day', 'week', 'year', 'full'],
              help='Report current month.')
@click.option('-w', '--week', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['week'],
              mutually_exclusive=['day', 'month', 'year', 'full'],
              help='Report current week.')
@click.option('-d', '--day', cls=MutuallyExclusiveOption, type=DateTime,
              flag_value=_SHORTCUT_OPTIONS_VALUES['day'],
              mutually_exclusive=['week', 'month', 'year', 'full'],
              help='Report current day.')
@click.option('-u', '--full', 'full', cls=MutuallyExclusiveOption,
              type=DateTime, flag_value=_SHORTCUT_OPTIONS_VALUES['full'],
              mutually_exclusive=['day', 'week', 'month', 'year'],
              help='Report full interval.')
@click.option('-p', '--project', 'projects', autocompletion=get_projects,
              multiple=True,
              help="Include project in the report and exclude all others. "
              "It can be used multiple times.")
@click.option('-P', '--exclude-project', 'exclude_projects', multiple=True,
              help="Exclude project from the report. "
              "It can be used multiple times.")
@click.option('-A', '--exclude-tag', 'exclude_tags', multiple=True,
              help="Include only frames with the given tag. "
              "It can be used multiple times.")
@click.option('-a', '--tag', 'tags', autocompletion=get_tags, multiple=True,
              help="Exclude tag from the report. "
              "It can be used multiple times.")
@click.option('-j', '--json', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='json', mutually_exclusive=['csv'],
              multiple=True,
              help="Format output in JSON instead of plain text")
@click.option('-s', '--csv', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='csv', mutually_exclusive=['json'],
              multiple=True,
              help="Format output in CSV instead of plain text")
@click.option('--plain', 'output_format', cls=MutuallyExclusiveOption,
              flag_value='plain', mutually_exclusive=['json', 'csv'],
              multiple=True, default=True, hidden=True,
              help="Format output in plain text (default)")
@click.option('-g/-G', '--pager/--no-pager', 'pager', default=None,
              help="(Don't) view output through a pager.")
@click.pass_obj
@catch_timetracker_error
def log(timetracker, current, from_, to, projects, exclude_projects, tags,
        exclude_tags, year, month, week, day, full, output_format,
        pager):
    """
    Display each recorded session during the given timespan.

    By default, the sessions from the last 7 days are printed.
    """
    filtered_frames = timetracker.log(
        from_,
        to,
        current,
        projects,
        tags,
        exclude_projects,
        exclude_tags,
        year,
        month,
        week,
        day,
        full,
    )

    if output_format == 'json':
        click.echo(frames_to_json(filtered_frames))
        return

    if output_format == 'csv':
        click.echo(frames_to_csv(filtered_frames))
        return

    frames_by_day = sorted_groupby(
        filtered_frames,
        lambda frame: frame.start.floor('day'),
        reverse=True
    )

    lines = []
    # use the pager, or print directly to the terminal
    if pager or (pager is None and timetracker.config.getboolean('options', 'pager', True)):

        def _print(line):
            lines.append(line)

        def _final_print(lines):
            click.echo_via_pager('\n'.join(lines))
    else:

        def _print(line):
            click.echo(line)

        def _final_print(lines):
            pass

    for i, (day, frames) in enumerate(frames_by_day):
        if i != 0:
            _print('')

        frames = sorted(frames, key=operator.attrgetter('start'))
        longest_project = max(len(frame.project) for frame in frames)

        daily_total = reduce(
            operator.add,
            (frame.stop - frame.start for frame in frames)
        )

        _print(
            "{date} ({daily_total})".format(
                date=style('date', "{:dddd DD MMMM YYYY}".format(day)),
                daily_total=style('time', format_timedelta(daily_total))
            )
        )

        _print("\n".join(
            "\t{id}  {start} to {stop}  {delta:>11}  {project}{tags}".format(
                delta=format_timedelta(frame.stop - frame.start),
                project=style('project', '{:>{}}'.format(
                    frame.project, longest_project
                )),
                tags=(" "*2 if frame.tags else "") + style('tags', frame.tags),
                start=style('time', '{:HH:mm}'.format(frame.start)),
                stop=style('time', '{:HH:mm}'.format(frame.stop)),
                id=style('short_id', frame.id)
            )
            for frame in frames
        ))

    _final_print(lines)


@cli.command(context_settings={'ignore_unknown_options': True})
@click.argument('id', required=False, autocompletion=get_frames)
@click.pass_obj
@catch_timetracker_error
def edit(timetracker, id):
    """
    Edit frames.

    You can specify the frame to edit by its position or by its frame id.
    For example, to edit the second-to-last frame, pass `-2` as the frame
    index. You can get the id of a frame with the `x log` command.

    If no id or index is given, the frame defaults to the current frame (or the
    last recorded frame, if no project is currently running).

    The editor used is determined by the `VISUAL` or `EDITOR` environment
    variables (in that order) and defaults to `notepad` on Windows systems and
    to `vim`, `nano`, or `vi` (first one found) on all other systems.
    """
    date_format = 'YYYY-MM-DD'
    time_format = 'HH:mm:ss'
    datetime_format = '{} {}'.format(date_format, time_format)
    local_tz = tz.tzlocal()

    if id:
        frame = get_frame_from_argument(timetracker, id)
        id = frame.id
    elif timetracker.is_started:
        frame = Frame(timetracker.current['start'], None,
                      timetracker.current['project'], None,
                      timetracker.current['tags'])
    elif timetracker.frames:
        frame = timetracker.frames[-1]
        id = frame.id
    else:
        raise click.ClickException(
            style('error', "No frames recorded yet. It's time to create your "
                  "first one!"))

    data = {
        # -> Arrow.format() ret string repr of Arrow object
        'start': frame.start.format(datetime_format),
        'project': frame.project,
        'tags': frame.tags,
    }

    if id:
        # -> Arrow.format() ret string repr of Arrow object
        data['stop'] = frame.stop.format(datetime_format)

    text = json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False)

    start = None
    stop = None

    # enter into while loop until succesful and validated
    #  edit has been performed
    while True:
        output = click.edit(text, extension='.json')

        if not output:
            click.echo("No change made.")
            return

        try:
            data = json.loads(output)
            project = data['project']
            tags = data['tags']
            # -> arrow.get() in local tz
            start = arrow.get(data['start'], datetime_format, tzinfo=local_tz)
            stop = arrow.get(data['stop'], datetime_format, tzinfo=local_tz) if id else None
            # if start time of the project is not before end time
            #  raise ValueException
            if not timetracker.is_started and start > stop:
                raise ValueError(
                    "Task cannot end before it starts.")
            if start > arrow.now():
                raise ValueError("Start date can't be in the future")
            if stop and stop > arrow.now():
                raise ValueError("Stop date can't be in the future")
            # break out of while loop and continue execution of
            #  the edit function normally
            break
        except (ValueError, TypeError, RuntimeError) as e:
            click.echo("Error while parsing inputted values: {}".format(e),
                       err=True)
        except KeyError:
            click.echo(
                "The edited frame must contain the project, "
                "start, and stop keys.", err=True)
        # we reach here if exception was thrown, wait for user
        #  to acknowledge the error before looping in while and
        #  showing user the editor again
        click.pause(err=True)
        # use previous entered values to the user in editor
        #  instead of original ones
        text = output

    # we reach this when we break out of the while loop above
    timetracker.edit(id, project, start, stop, tags)
    timetracker.save()

    click.echo(
        "Edited frame for project {project}{tags}, from {start} to {stop} "
        "({delta})".format(
            delta=format_timedelta(stop - start) if stop else '-',
            project=style('project', project),
            tags=(" " if tags else "") + style('tags', tags),
            start=style(
                'time',
                start.to(local_tz).format(time_format)
            ),
            stop=style(
                'time',
                stop.to(local_tz).format(time_format) if stop else '-'
            )
        )
    )


@cli.command()
@click.argument('key', required=False, metavar='SECTION.OPTION')
@click.argument('value', required=False)
@click.option('-e', '--edit', is_flag=True,
              help="Edit the configuration file with an editor.")
@click.pass_obj
@click.pass_context
@catch_timetracker_error
def config(ctx, timetracker, key, value, edit):
    """
    Get and set configuration options.

    If `value` is not provided, the content of the `key` is displayed. Else,
    the given `value` is set.

    You can edit the config file with an editor with the `--edit` option.

    Example:

    \b
    $ x config options.include_current true
    $ x config options.include_current
    true
    """
    config = timetracker.config

    if edit:
        try:
            with open(config.config_file) as fp:
                rawconfig = fp.read()
        except (IOError, OSError):
            rawconfig = ''

        newconfig = click.edit(text=rawconfig, extension='.ini')
        if newconfig:
            config.reload(newconfig)
            safe_save(config.config_file, config.write)
    else:
        if not key:
            click.echo(ctx.get_help())
            return

        try:
            section, option = key.split('.')
        except ValueError:
            raise click.ClickException(
                "The key must have the format 'section.option'"
            )

        if value is None:
            if not config.has_section(section):
                raise click.ClickException("No such section {}".format(section))

            if not config.has_option(section, option):
                raise click.ClickException(
                    "No such option {} in {}".format(option, section)
                )

            click.echo(config.get(section, option))
        else:
            if not config.has_section(section):
                config.add_section(section)

            config.set(section, option, value)
            safe_save(config.config_file, config.write)
