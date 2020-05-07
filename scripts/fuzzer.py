#!/usr/bin/env python

# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import argparse
import random
import os
import sys

import arrow

from tt import TimeTracker

FUZZER_PROJECTS = [
    ("apollo11", ["reactor", "module", "wheels", "steering", "brakes"]),
    ("hubble", ["lens", "camera", "transmission"]),
    ("voyager1", ["probe", "generators", "sensors", "antenna"]),
    ("voyager2", ["probe", "orbiter", "sensors", "antenna"]),
]


def get_options():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--path",
        default=".",
        help="The path to put generated frames file (default: current dir)")
    parser.add_argument(
        "--allow-all-tags",
        default=False,
        action="store_true",
        help="Allow to associate all tags to a project frame")
    options = parser.parse_args()
    return options


def fill_tt_randomly(timetracker, project_data, allow_all_tags):
    now = arrow.now()

    for date in arrow.Arrow.range('day', now.shift(months=-1), now):
        if date.weekday() in (5, 6):
            # Weekend \o/
            continue

        start = date.replace(hour=9, minute=random.randint(0, 59)) \
                    .shift(seconds=random.randint(0, 59))

        while start.hour < random.randint(16, 19):
            project, tags = random.choice(project_data)
            max_tags = len(tags) if allow_all_tags else len(tags) - 1
            frame_tags = random.sample(tags, random.randint(0, max_tags))
            frame = timetracker.frames.add(
                project,
                start,
                start.shift(seconds=random.randint(60, 4 * 60 * 60)),
                tags=frame_tags)
            start = frame.stop.shift(seconds=random.randint(0, 1 * 60 * 60))


if __name__ == '__main__':
    options = get_options()
    if not os.path.isdir(options.path):
        sys.exit("Invalid directory argument")
    timetracker = TimeTracker(
        config_dir=options.path, frames=None, current=None)
    fill_tt_randomly(timetracker, FUZZER_PROJECTS, options.allow_all_tags)
    timetracker.save()
