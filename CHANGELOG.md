<!--
SPDX-FileCopyrightText: 2020 David Alfonso

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

## [Unreleased]

### Changed
- Environment data directory variable set to: `XTIMETRACKER_DIR` (previously `XTT_DIR`)

### Fixed
- README mentioned invalid project/tags, also formatted with mdformat
- Exception when editing current frame

## [0.1.0] - 2020-12-31

- xtimetracker is a **fork** of [Watson](https://tailordev.github.io/Watson/) 1.8.0 and maintains compatibility with its file format
- It contains some unreleased features, as well as many simplifications in commands and options; you can read more in the README.md

### Added
- Add Python 3.8 support
- Add exclude options `-A/-P` to `aggregate` and `log` commands
- Make `status` the default command (`x` is like `x status`) and hide it from help
- New option `restart_on_start` to automatically start a new entry when running the `start` command

### Changed
- Change include/exclude options in `report` and `log` commands to `-p/-P` and `-a/-A`
- Add config option `include_current` unifying both `report_current` and `log_current` into one
- Rename `--all` option to `--full` in `report` and `log` commands
- Add `-r` option to `start` command to start a new task with the same data than the last logged entry
- Add `-s` option to `start` command to stretch the new entry's start time to match the previous entry's stop time; previously named `--no-gap`
- Unify all command datetime inputs (watson#292)
- Merge `cancel` command into `stop`
- Disallow future dates when editing a frame

### Removed
- Remove Python 2 and 3.5 support
- Remove `remove`, `rename`, `frames`, `tags`, `projects` commands
- Remove crick.io support and all code related to it (including the `sync` and `merge` commands and the `last_sync` file)
- Remove `include_partial_frames` and suppose true
- Remove lunar time options
- Remove user confirmation when using new projects or tags in a command
- Remove `--at` option from `start` command

### Fixed
- Handle correctly frames that cross boundaries in reports
- Aggregate calculates wrong time if used with `--current` (watson#293)
- Stylize prompt to create new project or tag (watson#310)
- Watson now suggests correct command if users make small typo (watson#318)
- The `start` command now correctly checks if project is empty (watson#322)
- The `report` and `aggregate` commands with `--json` option now correctly encode Arrow objects (watson#329)
- Fix `aggregate` command with `--json` option (watson#331)
- Make `help` command show correct command information (watson#355)

### Internal
- Use GPLv3 license in new code, while maintaining the MIT license for Watson code; [More info in this blog post](https://davidalfonso.es/posts/switching-licenses-from-mit-to-gnu-gpl)
- Adhere to version 3.0 of the [REUSE specification](https://reuse.software/spec/), validated using [reuse-tool](https://github.com/fsfe/reuse-tool).
- Use `setuptools` as described in PEP517, which adds pyproject.toml and simplifies setup.py
- Add tests to the CLI using `click` testing facilities
- Improve Arrow 0.15.0 support after changes in `arrow.get()` behavior (watson#296)
- Infrastructure and scripts to allow use of fuzzed data in tests (see `scripts/fuzzer.py`)
- Centralize TimeTrackerError exception catching in cli.py and transformation to cli exceptions; remove unneeded click dependency from timetracker.py
- Remove all autocompletion files (some can be generated with `scripts/create-completion-scripts.sh`)
- Remove TravisCI support until deciding what service to use
- Refactor configuration management to be created outside of the TimeTracker object; this helps testing and separates concerns
- Refactor file management functions into new `backend` module
- Add script to print a frames file without any processing for debugging purposes

[Unreleased]: https://github.com/davidag/xtimetracker/releases/tag/v0.1.0
