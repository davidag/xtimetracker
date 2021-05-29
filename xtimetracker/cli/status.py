# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020-2021 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

from __future__ import annotations

import click
from typing import TYPE_CHECKING

from .cli import cli
from .utils import (
    catch_timetracker_error,
    format_date,
    style,
)

if TYPE_CHECKING:
    from ..timetracker import TimeTracker


@cli.command(hidden=True)
@click.option("-p", "--project", is_flag=True, help="only output project")
@click.option("-t", "--tags", is_flag=True, help="only show tags")
@click.option("-e", "--elapsed", is_flag=True, help="only show time elapsed")
@click.pass_obj
@catch_timetracker_error
def status(tt: TimeTracker, project, tags, elapsed):
    """
    Display the currently recorded project.

    The displayed date and time format can be configured with options
    `options.date_format` and `options.time_format`.
    """
    if not tt.is_started:
        click.echo("No project started.")
        return

    current = tt.current

    if project:
        click.echo(
            "{}".format(
                style("project", current["project"]),
            )
        )

    if tags:
        click.echo("{}".format(style("tags", current["tags"])))

    if elapsed:
        click.echo("{}".format(style("time", current["start"].humanize())))

    if project or tags or elapsed:
        return

    click.echo(
        "Project {}{} started {} ({})".format(
            style("project", current["project"]),
            (" " if current["tags"] else "") + style("tags", current["tags"]),
            style("time", current["start"].humanize()),
            style("datetime", format_date(current["start"])),
        )
    )
