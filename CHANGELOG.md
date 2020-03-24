# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2020-MM-DD
- tt is a **fork** of [Watson](https://tailordev.github.io/Watson/) 1.8.0. It also contains many of the unreleased features of it. This first release of tt will be 1.9.0 as it's not expected to break compatibility with the file format, and also to keep the current versioning scheme.

### Added
- Improve Arrow 0.15.0 support after changes in `arrow.get()` behavior (watson#296)
- Watson now suggests correct command if users make small typo (watson#318)

### Fixed
- Stylize prompt to create new project or tag (watson#310).
- Aggregate calculates wrong time if used with `--current` (watson#293)
- The `start` command now correctly checks if project is empty (watson#322)
- The `report` and `aggregate` commands with `--json` option now correctly
encode Arrow objects (watson#329)

[Unreleased]: https://gitlab.com/davidalfonso/tt/compare/v1.8.0...HEAD
