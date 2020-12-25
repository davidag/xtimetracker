# tt

## Overview

tt is here to help you manage your time. You want to know how
much time you are spending on your projects? You want to generate a nice
report for your clients? tt is here for you.

## Installing

TODO

## Usage

Start tracking your activity via:

```console
$ tt start world-domination +cats
```

With this command, you have started a new **frame** for the *world-domination* project with the *cats* tag. That's it.

Now stop tracking you world domination plan via:

```console
$ tt stop
Project world-domination [cats] started 8 minutes ago (2016.01.27 13:00:28+0100)
```

You can log your latest working sessions (aka **frames**) thanks to the ``log`` command:

```console
$ tt log
Tuesday 26 January 2016 (8m 32s)
      ffb2a4c  13:00 to 13:08      08m 32s   world-domination  [cats]
```

Please note that, as the report command, the `log` command comes with projects, tags and dates filtering.

To list all available commands use:

```console
$ tt help
```

## License

Copyright (C) 2020 David Alfonso

This work is licensed under multiple licenses.

* All original source code is licensed under GPL-3.0-or-later.
* All code borrowed from `the Watson project <https://github.com/TailorDev/Watson>`_ is licensed under the MIT license.

SPDX-License-Identifier: GPL-3.0-or-later AND MIT

For more accurate information, you can check the individual files.
