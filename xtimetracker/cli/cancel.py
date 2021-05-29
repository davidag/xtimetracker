# SPDX-FileCopyrightText: 2020-2021 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
def cancel(tt: TimeTracker):
    """
    Cancel current activity tracking.
    """
    old = tt.cancel()
    click.echo(
        "Canceled tracking: {}{}, started {}".format(
            style("project", old["project"]),
            (" " if old["tags"] else "") + style("tags", old["tags"]),
            style("time", old["start"].humanize()),
        )
    )
    tt.save()
