# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2021 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

from __future__ import annotations

import click
from typing import TYPE_CHECKING

from .autocompletion import get_project_or_tag_completion
from .cli import cli, stop
from .utils import (
    catch_timetracker_error,
    get_frame_from_argument,
    get_start_time_for_period,
    is_current_tracking_data,
    style,
    parse_project,
    parse_tags,
)

if TYPE_CHECKING:
    from ..timetracker import TimeTracker


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
    Start tracking an activity associated to a project.

    You can add tags to categorize more specifically what you are working on with
    tags adding any number of `+tag`.

    If there is an already running activity and the configuration option
    `options.stop_on_start` is true, it will be stopped before the new
    activity is started.
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
            frame = timetracker.get_latest_frame(project)
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


