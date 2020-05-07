<!--
SPDX-FileCopyrightText: 2015-2019 Tailordev
SPDX-FileCopyrightText: 2020 The tt Authors

SPDX-License-Identifier: GPL-3.0-or-later
SPDX-License-Identifier: MIT
-->

## Overview

Tt is here to help you monitor your time. You want to know how
much time you are spending on your projects? You want to generate a nice
report for your client? tt is here for you.

Tell tt when you start working on a task with the `start` command.
Then, when you are done, stop the timer with the `stop`
command. This will create what we call a **frame**. That's pretty much
everything you need to know to start using tt.

Each frame consists of the name of a project and some tags. Your tags
can be shared across projects and can be used to generate detailed
reports.

## Installation

Tt is available on any platform supported by Python (Windows, Mac,
Linux, \*BSD…). Currently, tt is in beta development, and the only
available way to use it is to clone this repository and install it
using the existing `setup.py` script.

```bash
$ git clone https://gitlab.com/davidalfonso/tt.git
$ cd tt/
$ pip install -e .
```

### Command line completion

#### Bash

If you use a Bash-compatible shell, you can install the `tt.completion` file from the source distribution as `/etc/bash.completion.d/tt` - or wherever your distribution keeps the Bash completion configuration files. After you restart your shell, you can then just type `tt` on your command line and then hit `TAB` to see all available commands. Depending on your input, it completes `tt` commands, command options, projects, tags and frame IDs.

#### ZSH

If you use zsh, copy the file `tt.zsh-completion` somewhere in your
`fpath` as `_tt`. For example, you can put it in
`/usr/local/share/zsh/site-functions`:

    cp tt.zsh-completion /usr/local/share/zsh/site-functions/_tt

Make sure that your .zshrc enables compinit:

    autoload -Uz compinit && compinit

#### Fish

If you use fish, you can copy or symlink the file `tt.fish` from the source distribution to `~/.config/fish/completions/tt.fish`.

You may need to make the completions directory as it is not created by default.

Once this is done, re-source your fish config:
  `source ~/.config/fish/config.fish`

You will now have command completion for fish, including the completion of known projects, tags, and frames.

## Getting started

Now that `tt` is installed on your system, let's start tracking your activity:

```bash
$ tt start world-domination +cats
```

With this command, you have started a new **frame** for the *world-domination* project with the *cat* tag. Time is running. Now, you need to work on your project. Let's do this. Now.

![Working cat](img/working-cat.gif){: width="400px" }

Welcome back! Now that your world domination plan has been set up, let's stop time tracking via:

```bash
$ tt stop
Project world-domination [cat] started 34 minutes ago (id: 166d1fb)
```

To list all available commands, either [explore the commands documentation](user-guide/commands.md) or use:

```bash
$ tt help
```

We hope you will enjoy tt!
