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


@cli.command()
@click.pass_obj
@catch_timetracker_error
def stop(tt: TimeTracker):
    """
    Stop tracking current activity.
    """
    frame = tt.stop()
    output_str = "Stopped tracking: {}{}, started {} and stopped {}. (id: {})"
    click.echo(
        output_str.format(
            style("project", frame.project),
            (" " if frame.tags else "") + style("tags", frame.tags),
            # -> Arrow.humanize() just to output start/stop datetimes...
            style("time", frame.start.humanize()),
            style("time", frame.stop.humanize()),
            style("short_id", frame.id),
        )
    )
    tt.save()
