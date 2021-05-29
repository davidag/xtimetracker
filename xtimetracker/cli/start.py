# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020-2021 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

from __future__ import annotations

import click
from typing import TYPE_CHECKING

from .autocompletion import get_project_or_tag_completion
from .cli import cli
from .stop import stop
from .utils import (
    catch_timetracker_error,
    get_frame_from_argument,
    style,
    parse_project,
    parse_tags,
)

if TYPE_CHECKING:
    from ..timetracker import TimeTracker


@cli.command()
@click.option(
    "-s",
    "--stretch",
    is_flag=True,
    default=False,
    help=("Stretch start time to continue after last tracked activity."),
)
@click.option(
    "-r",
    "--restart",
    is_flag=True,
    default=False,
    help="Restart last frame or last project frame if a project " "is provided.",
)
@click.argument("args", nargs=-1, autocompletion=get_project_or_tag_completion)
@click.pass_obj
@click.pass_context
@catch_timetracker_error
def start(ctx, tt: TimeTracker, stretch, restart, args):
    """
    Start tracking an activity associated to a project.

    You can add tags to categorize more specifically what you are working on with
    tags adding any number of `+tag`.

    If there is an already running activity and the configuration option
    `options.stop_on_start` is true, it will be stopped before the new
    activity is started.
    """
    stop_flag = tt.config.getboolean("options", "stop_on_start")
    restart_flag = restart or tt.config.getboolean("options", "restart_on_start")
    stretch_flag = stretch or tt.config.getboolean("options", "autostretch_on_start")

    project = parse_project(args)
    tags = parse_tags(args)

    # check that we can obtain a project to start
    if not project and not restart_flag:
        raise click.ClickException("No project given.")

    # check that we can stop the activity in progress (if any)
    if tt.is_started and not stop_flag:
        raise click.ClickException(
            style(
                "error",
                "Project {} is already started with tags '{}'".format(
                    tt.current["project"], ", ".join(tt.current["tags"])
                ),
            )
        )

    # project is provided and restart is true
    if project and restart_flag:
        # obtain the tags from the last frame logged to the project
        if tt.is_started and tt.current["project"] == project:
            tags += tt.current["tags"]
        else:
            frame = tt.get_latest_frame(project)
            tags += frame["tags"] if frame else []

    # no project provided but we want to restart the latest active frame
    if not project and restart_flag:
        if tt.is_started:
            project = tt.current["project"]
            tags += tt.current["tags"]
        else:
            frame = get_frame_from_argument(tt, "-1")
            if frame:
                project = frame["project"]
                tags += frame["tags"]
            else:
                raise click.ClickException("No project to restart.")

    if tt.is_started:
        ctx.invoke(stop)

    current = tt.start(project, tags, stretch_flag)

    click.echo(
        "Starting project {}{} at {}".format(
            style("project", project),
            (" " if current["tags"] else "") + style("tags", current["tags"]),
            style("time", "{:HH:mm}".format(current["start"])),
        )
    )

    tt.save()
