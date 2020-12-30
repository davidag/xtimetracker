#!/usr/bin/env python

# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
from datetime import datetime
import json
import pathlib
import sys


def get_options():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--format",
        default="csv",
        help="The format to print the frames (default: csv)"
    )
    parser.add_argument(
        "-p",
        "--processing",
        default="raw",
        help="The level of data processing before printing (default: raw)"
    )
    parser.add_argument(
        "file",
        action="store",
        help="The frames file to parse")
    options = parser.parse_args()
    return options


def load_json(filepath):
    f = pathlib.Path(filepath)
    if not f.is_file():
        sys.exit(f"Invalid file: {f}")

    with f.open('r') as handle:
        return json.load(handle)


def print_data(data, fmt, proc):
    for f in data:
        start = datetime.fromtimestamp(int(f[0]))
        stop = datetime.fromtimestamp(int(f[1]))
        project = f[2].replace(" ", "_")
        id = f[3]
        tags = ",".join(t.replace(" ", "_") for t in f[4]) if len(f) >= 5 else ""
        updated_at = datetime.fromtimestamp(int(f[5])) if len(f) >= 6 else ""
        print(f"{start} {stop} {project} {id} {tags} {updated_at}")


if __name__ == '__main__':
    options = get_options()

    data = load_json(options.file)

    print_data(data, options.format, options.processing)
