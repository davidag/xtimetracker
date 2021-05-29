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
from .utils import (
    DateTime,
    catch_timetracker_error,
    style,
    parse_project,
    parse_tags,
)

if TYPE_CHECKING:
    from ..timetracker import TimeTracker


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, shell_complete=get_project_or_tag_completion)
@click.option(
    "-f",
    "--from",
    "from_",
    required=True,
    type=DateTime,
    help="Date and time of start of tracked activity",
)
@click.option(
    "-t",
    "--to",
    required=True,
    type=DateTime,
    help="Date and time of end of tracked activity",
)
@click.pass_obj
@catch_timetracker_error
def add(tt: TimeTracker, args, from_, to):
    """
    Add time to a project with tag(s) that was not tracked live.
    """
    project = parse_project(args)
    if not project:
        raise click.ClickException("No project given.")

    # Parse all the tags
    tags = parse_tags(args)

    # add a new frame, call timetracker save to update state files
    frame = tt.add(project=project, tags=tags, from_date=from_, to_date=to)

    click.echo(
        "Adding project {}{}, started {} and stopped {}. (id: {})".format(
            style("project", frame.project),
            (" " if frame.tags else "") + style("tags", frame.tags),
            style("time", frame.start.humanize()),
            style("time", frame.stop.humanize()),
            style("short_id", frame.id),
        )
    )
    tt.save()
