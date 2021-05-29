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
    style,
)

if TYPE_CHECKING:
    from ..timetracker import TimeTracker


@cli.command(context_settings={'ignore_unknown_options': True})
@click.option('-c', '--cancel', is_flag=True, default=False,
              help="Cancel current project monitoring.")
@click.pass_obj
@catch_timetracker_error
def stop(tt: TimeTracker, cancel):
    """
    Stop or cancel monitoring time for the current project.
    """
    if cancel:
        old = tt.cancel()
        click.echo("Canceling current monitoring for project {}{}".format(
            style('project', old['project']),
            (" " if old['tags'] else "") + style('tags', old['tags'])
        ))
    else:
        frame = tt.stop()
        output_str = "Stopping project {}{}, started {} and stopped {}. (id: {})"
        click.echo(output_str.format(
            style('project', frame.project),
            (" " if frame.tags else "") + style('tags', frame.tags),
            # -> Arrow.humanize() just to output start/stop datetimes...
            style('time', frame.start.humanize()),
            style('time', frame.stop.humanize()),
            style('short_id', frame.id),
        ))
    tt.save()
