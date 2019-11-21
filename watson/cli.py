import datetime
import itertools
import json
import operator
from functools import reduce, wraps

import arrow
import click
from dateutil import tz

import watson as _watson
from .autocompletion import (
    get_frames,
    get_project_or_tag_completion,
    get_projects,
    get_rename_name,
    get_rename_types,
    get_tags,
)
from .frames import Frame
from .utils import (
    adjusted_span,
    apply_weekday_offset,
    build_csv,
    build_json,
    confirm_project,
    confirm_tags,
    create_watson,
    flatten_report_for_csv,
    format_timedelta,
    frames_to_csv,
    frames_to_json,
    get_frame_from_argument,
    get_start_time_for_period,
    options,
    safe_save,
    sorted_groupby,
    style,
    parse_tags,
)


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
            # When we parse a date, we want to parse it in the timezone
            # expected by the user, so that midnight is midnight in the local
            # timezone, not in UTC. Cf issue #16.
            date.tzinfo = tz.tzlocal()
            # Add an offset to match the week beginning specified in the
            # configuration
            if param.name == "week":
                week_start = ctx.obj.config.get(
                    "options", "week_start", "monday")
                date = apply_weekday_offset(
                    start_time=date, week_start=week_start)
            return date

    def _parse_multiformat(self, value):
        date = None
        for fmt in (None, 'HH:mm:ss', 'HH:mm'):
            try:
                if fmt is None:
                    date = arrow.get(value)
                else:
                    date = arrow.get(value, fmt)
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


def catch_watson_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except _watson.WatsonError as e:
            raise click.ClickException(style('error', str(e)))
    return wrapper


@click.group()
@click.version_option(version=_watson.__version__, prog_name='Watson')
@click.pass_context
def cli(ctx):
    """
    Watson is a tool aimed for monitoring your time.
    """

    # This is the main command group, needed by click in order
    # to handle the subcommands
    ctx.obj = create_watson()


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

    click.echo(cmd.get_help(ctx))


@cli.command()
@click.option('-g/-G', '--gap/--no-gap', 'gap', is_flag=True, default=True,
              help=("Leave (or not) gap between end time of previous project "
                    "and start time of the current."))
@click.option('-s/-S', '--stop/--no-stop', 'stop_', default=None,
              help="Stop (or not) an already running project.")
@click.option('-c', '--confirm-new-project', is_flag=True, default=False,
              help="Confirm addition of new project.")
@click.option('-b', '--confirm-new-tag', is_flag=True, default=False,
              help="Confirm creation of new tag.")
@click.argument('args', nargs=-1,
                autocompletion=get_project_or_tag_completion)
@click.pass_obj
@click.pass_context
@catch_watson_error
def start(ctx, watson, gap, stop_, confirm_new_project, confirm_new_tag, args):
    """
    Start monitoring time for the given project.
    You can add tags indicating more specifically what you are working on with
    `+tag`.

    If there is an already running project and the configuration option
    `options.stop_on_start` is true, it will be stopped before the new
    project is started.
    """
    project = ' '.join(
        itertools.takewhile(lambda s: not s.startswith('+'), args)
    )
    if not project:
        raise click.ClickException("No project given.")

    if (watson.config.getboolean('options', 'confirm_new_project') or
            confirm_new_project):
        confirm_project(project, watson.projects())

    tags = parse_tags(args)

    if (watson.config.getboolean('options', 'confirm_new_tag') or
            confirm_new_tag):
        confirm_tags(tags, watson.tags)

    if watson.is_started:
        stop_on_start = stop_ or (
            stop_ is None and
            watson.config.getboolean('options', 'stop_on_start')
        )
        if stop_on_start:
            ctx.invoke(stop)
        else:
            raise click.ClickException(
                style('error', "Project {} is already started.".format(
                    watson.current['project'])
                )
            )

    current = watson.start(project, tags, gap=gap)

    click.echo("Starting project {}{} at {}".format(
        style('project', project),
        (" " if current['tags'] else "") + style('tags', current['tags']),
        style('time', "{:HH:mm}".format(current['start']))
    ))

    watson.save()


@cli.command(context_settings={'ignore_unknown_options': True})
@click.option('--at', 'at_', type=DateTime, default=None,
              help=('Stop frame at this time. Must be in '
                    '(YYYY-MM-DDT)?HH:MM(:SS)? format.'))
@click.pass_obj
@catch_watson_error
def stop(watson, at_):
    """
    Stop monitoring time for the current project.
    """
    frame = watson.stop(stop_at=at_)
    output_str = "Stopping project {}{}, started {} and stopped {}. (id: {})"
    click.echo(output_str.format(
        style('project', frame.project),
        (" " if frame.tags else "") + style('tags', frame.tags),
        style('time', frame.start.humanize()),
        style('time', frame.stop.humanize()),
        style('short_id', frame.id),
    ))
    watson.save()


@cli.command()
@click.pass_obj
@catch_watson_error
def cancel(watson):
    """
    Cancel the project being currently recorded.
    """
    old = watson.cancel()
    click.echo("Canceling the timer for project {}{}".format(
        style('project', old['project']),
        (" " if old['tags'] else "") + style('tags', old['tags'])
    ))
    watson.save()


@cli.command()
@click.option('-p', '--project', is_flag=True,
              help="only output project")
@click.option('-t', '--tags', is_flag=True,
              help="only show tags")
@click.option('-e', '--elapsed', is_flag=True,
              help="only show time elapsed")
@click.pass_obj
@catch_watson_error
def status(watson, project, tags, elapsed):
    """
    Display the currently recorded project.

    The displayed date and time format can be configured with options
    `options.date_format` and `options.time_format`.
    """
    if not watson.is_started:
        click.echo("No project started.")
        return

    current = watson.current

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

    datefmt = watson.config.get('options', 'date_format', '%Y.%m.%d')
    timefmt = watson.config.get('options', 'time_format', '%H:%M:%S%z')
    click.echo("Project {}{} started {} ({} {})".format(
        style('project', current['project']),
        (" " if current['tags'] else "") + style('tags', current['tags']),
        style('time', current['start'].humanize()),
        style('date', current['start'].strftime(datefmt)),
        style('time', current['start'].strftime(timefmt))
    ))


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
@catch_watson_error
def report(watson, current, from_, to, projects, exclude_projects, tags,
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

    report = watson.report(from_, to, current, projects, tags,
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
    if pager or (pager is None and
                 watson.config.getboolean('options', 'pager', True)):

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
@catch_watson_error
def aggregate(ctx, watson, current, from_, to, projects, exclude_projects,
              tags, exclude_tags, output_format, pager):
    """
    Display a report of the time spent on each project aggregated by day.

    By default, the time spent the last 7 days is printed.
    """
    from_, to = adjusted_span(watson, from_, to, current)
    delta = (to.datetime - from_.datetime).days
    lines = []
    for i in range(delta + 1):
        offset = datetime.timedelta(days=i)
        from_offset = from_ + offset
        output = ctx.invoke(report, current=current, from_=from_offset,
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
    elif pager or (pager is None and
                   watson.config.getboolean('options', 'pager', True)):
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
@catch_watson_error
def log(watson, current, from_, to, projects, exclude_projects, tags,
        exclude_tags, year, month, week, day, full, output_format,
        pager):
    """
    Display each recorded session during the given timespan.

    By default, the sessions from the last 7 days are printed.
    """  # noqa
    filtered_frames = watson.log(
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

    if 'json' in output_format:
        click.echo(frames_to_json(filtered_frames))
        return

    if 'csv' in output_format:
        click.echo(frames_to_csv(filtered_frames))
        return

    frames_by_day = sorted_groupby(
        filtered_frames,
        operator.attrgetter('day'), reverse=True
    )

    lines = []
    # use the pager, or print directly to the terminal
    if pager or (pager is None and
                 watson.config.getboolean('options', 'pager', True)):

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
                pad=longest_project,
                tags=(" "*2 if frame.tags else "") + style('tags', frame.tags),
                start=style('time', '{:HH:mm}'.format(frame.start)),
                stop=style('time', '{:HH:mm}'.format(frame.stop)),
                id=style('short_id', frame.id)
            )
            for frame in frames
        ))

    _final_print(lines)


@cli.command()
@click.argument('tags', nargs=-1,
                autocompletion=get_tags)
@click.pass_obj
@catch_watson_error
def projects(watson, tags):
    """
    Display the list of all the existing projects, or only those matching all
    the provided tag(s).
    """
    for project in watson.projects(tags):
        click.echo(style('project', project))


@cli.command()
@click.argument('projects', nargs=-1,
                autocompletion=get_projects)
@click.pass_obj
@catch_watson_error
def tags(watson, projects):
    """
    Display the list of all the tags, or only those matching all the provided
    projects.
    """
    for tag in watson.tags(projects):
        click.echo(style('tag', tag))


@cli.command()
@click.pass_obj
@catch_watson_error
def frames(watson):
    """
    Display the list of all frame IDs.
    """
    for frame in watson.frames:
        click.echo(style('short_id', frame.id))


@cli.command(context_settings={'ignore_unknown_options': True})
@click.argument('args', nargs=-1,
                autocompletion=get_project_or_tag_completion)
@click.option('-f', '--from', 'from_', required=True, type=DateTime,
              help="Date and time of start of tracked activity")
@click.option('-t', '--to', required=True, type=DateTime,
              help="Date and time of end of tracked activity")
@click.option('-c', '--confirm-new-project', is_flag=True, default=False,
              help="Confirm addition of new project.")
@click.option('-b', '--confirm-new-tag', is_flag=True, default=False,
              help="Confirm creation of new tag.")
@click.pass_obj
@catch_watson_error
def add(watson, args, from_, to, confirm_new_project, confirm_new_tag):
    """
    Add time to a project with tag(s) that was not tracked live.
    """
    # parse project name from args
    project = ' '.join(
        itertools.takewhile(lambda s: not s.startswith('+'), args)
    )
    if not project:
        raise click.ClickException("No project given.")

    # Confirm creation of new project if that option is set
    if (watson.config.getboolean('options', 'confirm_new_project') or
            confirm_new_project):
        confirm_project(project, watson.projects())

    # Parse all the tags
    tags = parse_tags(args)

    # Confirm creation of new tag(s) if that option is set
    if (watson.config.getboolean('options', 'confirm_new_tag') or
            confirm_new_tag):
        confirm_tags(tags, watson.tags)

    # add a new frame, call watson save to update state files
    frame = watson.add(project=project, tags=tags, from_date=from_, to_date=to)
    click.echo(
        "Adding project {}{}, started {} and stopped {}. (id: {})".format(
            style('project', frame.project),
            (" " if frame.tags else "") + style('tags', frame.tags),
            style('time', frame.start.humanize()),
            style('time', frame.stop.humanize()),
            style('short_id', frame.id)
        )
    )
    watson.save()


@cli.command(context_settings={'ignore_unknown_options': True})
@click.option('-c', '--confirm-new-project', is_flag=True, default=False,
              help="Confirm addition of new project.")
@click.option('-b', '--confirm-new-tag', is_flag=True, default=False,
              help="Confirm creation of new tag.")
@click.argument('id', required=False, autocompletion=get_frames)
@click.pass_obj
@catch_watson_error
def edit(watson, confirm_new_project, confirm_new_tag, id):
    """
    Edit a frame.

    You can specify the frame to edit by its position or by its frame id.
    For example, to edit the second-to-last frame, pass `-2` as the frame
    index. You can get the id of a frame with the `watson log` command.

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
        frame = get_frame_from_argument(watson, id)
        id = frame.id
    elif watson.is_started:
        frame = Frame(watson.current['start'], None, watson.current['project'],
                      None, watson.current['tags'])
    elif watson.frames:
        frame = watson.frames[-1]
        id = frame.id
    else:
        raise click.ClickException(
            style('error', "No frames recorded yet. It's time to create your "
                           "first one!"))

    data = {
        'start': frame.start.format(datetime_format),
        'project': frame.project,
        'tags': frame.tags,
    }

    if id:
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
            # Confirm creation of new project if that option is set
            if (watson.config.getboolean('options', 'confirm_new_project') or
                    confirm_new_project):
                confirm_project(project, watson.projects())
            tags = data['tags']
            # Confirm creation of new tag(s) if that option is set
            if (watson.config.getboolean('options', 'confirm_new_tag') or
                    confirm_new_tag):
                confirm_tags(tags, watson.tags)
            start = arrow.get(data['start'], datetime_format).replace(
                tzinfo=local_tz).to('utc')
            stop = arrow.get(data['stop'], datetime_format).replace(
                tzinfo=local_tz).to('utc') if id else None
            # if start time of the project is not before end time
            #  raise ValueException
            if not watson.is_started and start > stop:
                raise ValueError(
                    "Task cannot end before it starts.")
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
    if id:
        watson.frames[id] = (project, start, stop, tags)
    else:
        watson.current = dict(start=start, project=project, tags=tags)

    watson.save()
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


@cli.command(context_settings={'ignore_unknown_options': True})
@click.argument('id', autocompletion=get_frames)
@click.option('-f', '--force', is_flag=True,
              help="Don't ask for confirmation.")
@click.pass_obj
@catch_watson_error
def remove(watson, id, force):
    """
    Remove a frame. You can specify the frame either by id or by position
    (ex: `-1` for the last frame).
    """
    frame = get_frame_from_argument(watson, id)
    id = frame.id

    if not force:
        click.confirm(
            "You are about to remove frame "
            "{project}{tags} from {start} to {stop}, continue?".format(
                project=style('project', frame.project),
                tags=(" " if frame.tags else "") + style('tags', frame.tags),
                start=style('time', '{:HH:mm}'.format(frame.start)),
                stop=style('time', '{:HH:mm}'.format(frame.stop))
            ),
            abort=True
        )

    del watson.frames[id]

    watson.save()
    click.echo("Frame removed.")


@cli.command()
@click.argument('key', required=False, metavar='SECTION.OPTION')
@click.argument('value', required=False)
@click.option('-e', '--edit', is_flag=True,
              help="Edit the configuration file with an editor.")
@click.pass_context
@catch_watson_error
def config(context, key, value, edit):
    """
    Get and set configuration options.

    If `value` is not provided, the content of the `key` is displayed. Else,
    the given `value` is set.

    You can edit the config file with an editor with the `--edit` option.

    Example:

    \b
    $ watson config options.include_current true
    $ watson config options.include_current
    true
    """
    watson = context.obj
    wconfig = watson.config

    if edit:
        try:
            with open(watson.config_file) as fp:
                rawconfig = fp.read()
        except (IOError, OSError):
            rawconfig = ''

        newconfig = click.edit(text=rawconfig, extension='.ini')

        if newconfig:
            safe_save(watson.config_file, newconfig)

        try:
            watson.config = None
            watson.config  # triggers reloading config from file
        except _watson.ConfigurationError as exc:
            watson.config = wconfig
            watson.save()
            raise click.ClickException(style('error', str(exc)))
        return

    if not key:
        click.echo(context.get_help())
        return

    try:
        section, option = key.split('.')
    except ValueError:
        raise click.ClickException(
            "The key must have the format 'section.option'"
        )

    if value is None:
        if not wconfig.has_section(section):
            raise click.ClickException("No such section {}".format(section))

        if not wconfig.has_option(section, option):
            raise click.ClickException(
                "No such option {} in {}".format(option, section)
            )

        click.echo(wconfig.get(section, option))
    else:
        if not wconfig.has_section(section):
            wconfig.add_section(section)

        wconfig.set(section, option, value)
        watson.config = wconfig
        watson.save()


@cli.command()
@click.argument('frames_with_conflict', type=click.Path(exists=True))
@click.option('-f', '--force', 'force', is_flag=True,
              help="If specified, then the merge will automatically "
              "be performed.")
@click.pass_obj
@catch_watson_error
def merge(watson, frames_with_conflict, force):
    """
    Perform a merge of the existing frames with a conflicting frames file.

    When storing the frames on a file hosting service, there is the
    possibility that the frame file goes out-of-sync due to one or
    more of the connected clients going offline. This can cause the
    frames to diverge.

    If the `--force` command is specified, the merge operation
    will automatically be performed.

    The only argument is a path to the the conflicting `frames` file.

    Merge will output statistics about the merge operation.

    Example:

    \b
    $ watson merge frames-with-conflicts
    120 frames will be left unchanged
    12  frames will be merged
    3   frame conflicts need to be resolved

    To perform a merge operation, the user will be prompted to
    select the frame they would like to keep.
    """
    original_frames = watson.frames
    conflicting, merging = watson.merge_report(frames_with_conflict)

    # find the length of the largest returned list, then get the number of
    # digits of this length
    dig = len(str(max(len(original_frames), len(merging), len(conflicting))))

    click.echo("{:<{width}} frames will be left unchanged".format(
        len(original_frames) - len(conflicting), width=dig))
    click.echo("{:<{width}} frames will be merged".format(
        len(merging), width=dig))
    click.echo("{:<{width}} frames will need to be resolved".format(
        len(conflicting), width=dig))

    # No frames to resolve or merge.
    if not conflicting and not merging:
        return

    # Confirm user would like to merge
    if not force and not click.confirm("Do you want to continue?"):
        return

    if conflicting:
        click.echo("Will resolve conflicts:")

    date_format = 'YYYY-MM-DD HH:mm:ss'

    for conflict_frame in conflicting:
        original_frame = original_frames[conflict_frame.id]

        # Print original frame
        original_frame_data = {
            'project': original_frame.project,
            'start': original_frame.start.format(date_format),
            'stop': original_frame.stop.format(date_format),
            'tags': original_frame.tags
        }
        click.echo("frame {}:".format(style('short_id', original_frame.id)))
        click.echo("{}".format('\n'.join('<' + line for line in json.dumps(
            original_frame_data, indent=4, ensure_ascii=False).splitlines())))
        click.echo("---")

        # make a copy of the namedtuple
        conflict_frame_copy = conflict_frame._replace()

        # highlight conflicts
        if conflict_frame.project != original_frame.project:
            project = '**' + str(conflict_frame.project) + '**'
            conflict_frame_copy = conflict_frame_copy._replace(project=project)

        if conflict_frame.start != original_frame.start:
            start = '**' + str(conflict_frame.start.format(date_format)) + '**'
            conflict_frame_copy = conflict_frame_copy._replace(start=start)

        if conflict_frame.stop != original_frame.stop:
            stop = '**' + str(conflict_frame.stop.format(date_format)) + '**'
            conflict_frame_copy = conflict_frame_copy._replace(stop=stop)

        for idx, tag in enumerate(conflict_frame.tags):
            if tag not in original_frame.tags:
                conflict_frame_copy.tags[idx] = '**' + str(tag) + '**'

        # Print conflicting frame
        conflict_frame_data = {
            'project': conflict_frame_copy.project,
            'start': conflict_frame_copy.start.format(date_format),
            'stop': conflict_frame_copy.stop.format(date_format),
            'tags': conflict_frame_copy.tags
        }
        click.echo("{}".format('\n'.join('>' + line for line in json.dumps(
            conflict_frame_data, indent=4, ensure_ascii=False).splitlines())))
        resp = click.prompt(
            "Select the frame you want to keep: left or right? (L/r)",
            value_proc=options(['L', 'r']))

        if resp == 'r':
            # replace original frame with conflicting frame
            original_frames[conflict_frame.id] = conflict_frame

    # merge in any non-conflicting frames
    for frame in merging:
        start, stop, project, id, tags, updated_at = frame.dump()
        original_frames.add(project, start, stop, tags=tags, id=id,
                            updated_at=updated_at)

    watson.frames = original_frames
    watson.frames.changed = True
    watson.save()


@cli.command()
@click.argument('rename_type', required=True, metavar='TYPE',
                autocompletion=get_rename_types)
@click.argument('old_name', required=True, autocompletion=get_rename_name)
@click.argument('new_name', required=True, autocompletion=get_rename_name)
@click.pass_obj
@catch_watson_error
def rename(watson, rename_type, old_name, new_name):
    """
    Rename a project or tag.
    """
    if rename_type == 'tag':
        watson.rename_tag(old_name, new_name)
        click.echo('Renamed tag "{}" to "{}"'.format(
                        style('tag', old_name),
                        style('tag', new_name)
                   ))
    elif rename_type == 'project':
        watson.rename_project(old_name, new_name)
        click.echo('Renamed project "{}" to "{}"'.format(
                        style('project', old_name),
                        style('project', new_name)
                   ))
    else:
        raise click.ClickException(style(
            'error',
            'You have to call rename with type "project" or "tag"; '
            'you supplied "%s"' % rename_type
        ))
