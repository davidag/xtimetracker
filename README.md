# `xtimetracker`

*Simple time tracking from the command line. Built for simplicity and usability first.*

## Overview

`xtimetracker` helps you manage your projects and track your time. It is a command line tool (`x`) with a simple set of commands and options.

[It was born as a fork](https://davidalfonso.es/posts/why-and-how-to-fork-the-case-of-watson) of the [Watson project](https://github.com/TailorDev/Watson) and it maintains compatibility with its JSON file format. It aspires to be a simple, maintained, and extendable (using plugins) time tracking software.

## Features

- Simple command-line interface with a reduced number of powerful commands
- Auto-completion for Bash and Zsh
- Multiple report formats

## Installing

You can install it using `pip` like this:
```console
$ pip install xtimetracker
```

## Quick tutorial

Start tracking your activity via:
```console
$ x start research +experiment +coding
```
With this command, you have started a new **frame** for the *research* project with the *experiment* and *coding* tags.

When you finish working on the task, stop tracking via:
```console
$ x stop
Stopping project research [experiment, coding], started 30 minutes ago and stopped just now. (id: 5c57b13)
```

You can view a log of your last week using the `log` command:

```console
$ x log
Tuesday 26 January 2020 (8m 32s)
      ffb2a4c  13:00 to 13:08      08m 32s   research [experiment, coding]
```

To list all available commands use:
```console
$ x --help
```

## Commands

You can find detailed information for each command using `-h/--help` after a command (e.g. `x start -h`).

You can find a list of available commands with `x -h` or `x --help`.

### `x`

`x` shows the status of the time tracker, i.e. tracked activity, tags and elapsed time.

### `x start`

This command starts tracking a new activity associated to a project and a set of tags. The project and/or tags can sometimes be omitted depending on the configuration and options used.

If there is an already running activity and the configuration optioni `stop_on_start` is true, the activity will be automatically stopped.

Options:

- `--stretch, -s`: Stretch start time to continue just after last tracked activity.

- `--restart, -r`: If a project is provided, the last tags used with it will be automatically added. If no project is provided, the last tracked project and tags will be used.

### `x stop`

This command stops the tracking in progress, if there is any.

### `x cancel`

This command cancels the tracking in progress, if there is any.

## License

Copyright (C) 2021 David Alfonso

This work is licensed under multiple licenses.

- All original source code is licensed under GPL-3.0-or-later.
- All code borrowed from `the Watson project <https://github.com/TailorDev/Watson>`\_ is licensed under the MIT license.

SPDX-License-Identifier: GPL-3.0-or-later AND MIT

For more accurate information, you can check the individual files.
