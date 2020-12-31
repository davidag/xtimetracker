# `xtimetracker`

*Simple time tracking from the command line.*

## Overview

`xtimetracker` helps you manage your projects and track your time. It is a command line tool (`x`) with a simple set of commands and options.

[It was born as a fork](https://davidalfonso.es/posts/why-and-how-to-fork-the-case-of-watson) of the [Watson project](https://github.com/TailorDev/Watson) and it maintains compatibility with its JSON file format. It aspires to be a simple, maintained, and extendable (using plugins) time tracking software.

## Installing

You can install it using `pip` like this:

```console
$ pip install xtimetracker
```

## Usage

Start tracking your activity via:

```console
$ x start research +experiment-a
```

With this command, you have started a new **frame** for the *research* project with the *experiment-a* tag.

Now stop tracking via:

```console
$ x stop
Stopping project research [experiment-a], started 30 minutes ago and stopped just now. (id: 5c57b13)
```

You can view a log of your latest working sessions using the ``log`` command:

```console
$ x log
Tuesday 26 January 2020 (8m 32s)
      ffb2a4c  13:00 to 13:08      08m 32s   world-domination  [cats]
```

Please note that, as the report command, the `log` command comes with projects, tags and dates filtering.

To list all available commands use:

```console
$ x help
```

## License

Copyright (C) 2020 David Alfonso

This work is licensed under multiple licenses.

* All original source code is licensed under GPL-3.0-or-later.
* All code borrowed from `the Watson project <https://github.com/TailorDev/Watson>`_ is licensed under the MIT license.

SPDX-License-Identifier: GPL-3.0-or-later AND MIT

For more accurate information, you can check the individual files.
