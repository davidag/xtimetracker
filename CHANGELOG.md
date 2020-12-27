<!--
SPDX-FileCopyrightText: 2020 David Alfonso

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2020-MM-DD
- xtimetracker is a **fork** of [Watson](https://tailordev.github.io/Watson/) 1.8.0 and maintains compatibility with its file format. It also contains many of the unreleased features of it.

### Added
- Improve Arrow 0.15.0 support after changes in `arrow.get()` behavior (watson#296)
- Watson now suggests correct command if users make small typo (watson#318)

### Fixed
- Stylize prompt to create new project or tag (watson#310).
- Aggregate calculates wrong time if used with `--current` (watson#293)
- The `start` command now correctly checks if project is empty (watson#322)
- The `report` and `aggregate` commands with `--json` option now correctly
encode Arrow objects (watson#329)

[Unreleased]: https://github.com/davidag/xtimetracker/releases/tag/v0.1.0
