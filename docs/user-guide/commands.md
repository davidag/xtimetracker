<!-- 
    This document has been automatically generated.
    It should NOT BE EDITED.
    To update this part of the documentation,
    please type the following from the repository root:
    $ make docs-->

# Commands
## `add`

```bash
Usage:  tt add [OPTIONS] [ARGS]...
```

Add time to a project with tag(s) that was not tracked live.

### Options

Flag | Help
-----|-----
`-f, --from DATETIME` | Date and time of start of tracked activity  [required]
`-t, --to DATETIME` | Date and time of end of tracked activity  [required]
`-c, --confirm-new-project` | Confirm addition of new project.
`-b, --confirm-new-tag` | Confirm creation of new tag.
`--help` | Show this message and exit.

## `aggregate`

```bash
Usage:  tt aggregate [OPTIONS]
```

Display a report of the time spent on each project aggregated by day.

By default, the time spent the last 7 days is printed.

### Options

Flag | Help
-----|-----
`-c, --current / -C, --no-current` | (Don't) include currently running frame in report.
`-f, --from DATETIME` | Report start date. Default: 7 days ago.
`-t, --to DATETIME` | Report stop date (inclusive). Default: tomorrow.
`-p, --project TEXT` | Include project in the report and exclude all others.It can be used multiple times.
`-P, --exclude-project TEXT` | Exclude project from the report. It can be used multiple times.
`-a, --tag TEXT` | Reports activity only for frames containing the given tag. It can be used multiple times.
`-A, --exclude-tag TEXT` | Reports activity for all tags but the given ones. It can be used multiple times.
`-j, --json` | Format output in JSON instead of plain text
`-s, --csv` | Format output in CSV instead of plain text
`-g, --pager / -G, --no-pager` | (Don't) view output through a pager.
`--help` | Show this message and exit.

## `cancel`

```bash
Usage:  tt cancel [OPTIONS]
```

Cancel the project being currently recorded.

### Options

Flag | Help
-----|-----
`--help` | Show this message and exit.

## `config`

```bash
Usage:  tt config [OPTIONS] SECTION.OPTION [VALUE]
```

Get and set configuration options.

If `value` is not provided, the content of the `key` is displayed. Else,
the given `value` is set.

You can edit the config file with an editor with the `--edit` option.

Example:


    $ tt config options.include_current true
    $ tt config options.include_current
    true

### Options

Flag | Help
-----|-----
`-e, --edit` | Edit the configuration file with an editor.
`--help` | Show this message and exit.

## `edit`

```bash
Usage:  tt edit [OPTIONS] [ID]
```

Edit a frame.

You can specify the frame to edit by its position or by its frame id.
For example, to edit the second-to-last frame, pass `-2` as the frame
index. You can get the id of a frame with the `tt log` command.

If no id or index is given, the frame defaults to the current frame (or the
last recorded frame, if no project is currently running).

The editor used is determined by the `VISUAL` or `EDITOR` environment
variables (in that order) and defaults to `notepad` on Windows systems and
to `vim`, `nano`, or `vi` (first one found) on all other systems.

### Options

Flag | Help
-----|-----
`-c, --confirm-new-project` | Confirm addition of new project.
`-b, --confirm-new-tag` | Confirm creation of new tag.
`--help` | Show this message and exit.

## `frames`

```bash
Usage:  tt frames [OPTIONS]
```

Display the list of all frame IDs.

### Options

Flag | Help
-----|-----
`--help` | Show this message and exit.

## `help`

```bash
Usage:  tt help [OPTIONS] [COMMAND]
```

Display help information

### Options

Flag | Help
-----|-----
`--help` | Show this message and exit.

## `log`

```bash
Usage:  tt log [OPTIONS]
```

Display each recorded session during the given timespan.

By default, the sessions from the last 7 days are printed.

### Options

Flag | Help
-----|-----
`-c, --current / -C, --no-current` | (Don't) include currently running frame in output.
`-f, --from DATETIME` | Log start date. Default: 7 days ago.
`-t, --to DATETIME` | Log stop date (inclusive). Default: tomorrow.
`-y, --year` | Report current year.
`-m, --month` | Report current month.
`-w, --week` | Report current week.
`-d, --day` | Report current day.
`-u, --full` | Report full interval.
`-p, --project TEXT` | Include project in the report and exclude all others. It can be used multiple times.
`-P, --exclude-project TEXT` | Exclude project from the report. It can be used multiple times.
`-A, --exclude-tag TEXT` | Include only frames with the given tag. It can be used multiple times.
`-a, --tag TEXT` | Exclude tag from the report. It can be used multiple times.
`-j, --json` | Format output in JSON instead of plain text
`-s, --csv` | Format output in CSV instead of plain text
`-g, --pager / -G, --no-pager` | (Don't) view output through a pager.
`--help` | Show this message and exit.

## `merge`

```bash
Usage:  tt merge [OPTIONS] FRAMES_WITH_CONFLICT
```

Perform a merge of the existing frames with a conflicting frames file.

When storing the frames on a file hosting service, there is the
possibility that the frame file goes out-of-sync due to one or
more of the connected clients going offline. This can cause the
frames to diverge.

If the `--force` command is specified, the merge operation
will automatically be performed.

The only argument is a path to the the conflicting `frames` file.

Merge will output statistics about the merge operation.

Example:


    $ tt merge frames-with-conflicts
    120 frames will be left unchanged
    12  frames will be merged
    3   frame conflicts need to be resolved
    
To perform a merge operation, the user will be prompted to
select the frame they would like to keep.

### Options

Flag | Help
-----|-----
`-f, --force` | If specified, then the merge will automatically be performed.
`--help` | Show this message and exit.

## `projects`

```bash
Usage:  tt projects [OPTIONS] [TAGS]...
```

Display the list of all the existing projects, or only those matching all
the provided tag(s).

### Options

Flag | Help
-----|-----
`--help` | Show this message and exit.

## `remove`

```bash
Usage:  tt remove [OPTIONS] ID
```

Remove a frame. You can specify the frame either by id or by position
(ex: `-1` for the last frame).

### Options

Flag | Help
-----|-----
`-f, --force` | Don't ask for confirmation.
`--help` | Show this message and exit.

## `rename`

```bash
Usage:  tt rename [OPTIONS] TYPE OLD_NAME NEW_NAME
```

Rename a project or tag.

### Options

Flag | Help
-----|-----
`--help` | Show this message and exit.

## `report`

```bash
Usage:  tt report [OPTIONS]
```

Display a report of the time spent on each project.

By default, the time spent the last 7 days is printed.

### Options

Flag | Help
-----|-----
`-c, --current / -C, --no-current` | (Don't) include currently running frame in report.
`-f, --from DATETIME` | Report start date. Default: 7 days ago.
`-t, --to DATETIME` | Report stop date (inclusive). Default: tomorrow.
`-y, --year` | Report current year.
`-m, --month` | Report current month.
`-w, --week` | Report current week.
`-d, --day` | Report current day.
`-u, --full` | Report full interval.
`-p, --project TEXT` | Include project in the report and exclude all others. It can be used multiple times.
`-P, --exclude-project TEXT` | Exclude project from the report. It can be used multiple times.
`-a, --tag TEXT` | Include only frames with the given tag. It can be used multiple times.
`-A, --exclude-tag TEXT` | Exclude tag from the report. It can be used multiple times.
`-j, --json` | Output JSON format.
`-s, --csv` | Output CSV format.
`-g, --pager / -G, --no-pager` | (Don't) view output through a pager.
`--help` | Show this message and exit.

## `start`

```bash
Usage:  tt start [OPTIONS] [ARGS]...
```

Start monitoring time for the given project.
You can add tags indicating more specifically what you are working on with
`+tag`.

If there is an already running project and the configuration option
`options.stop_on_start` is true, it will be stopped before the new
project is started.

### Options

Flag | Help
-----|-----
`-g, --gap / -G, --no-gap` | Leave (or not) gap between end time of previous project and start time of the current.
`-s, --stop / -S, --no-stop` | Stop (or not) an already running project.
`-r, --restart` | Restart last frame or last project frame if a project is provided.
`-c, --confirm-new-project` | Confirm addition of new project.
`-b, --confirm-new-tag` | Confirm creation of new tag.
`--help` | Show this message and exit.

## `status`

```bash
Usage:  tt status [OPTIONS]
```

Display the currently recorded project.

The displayed date and time format can be configured with options
`options.date_format` and `options.time_format`.

### Options

Flag | Help
-----|-----
`-p, --project` | only output project
`-t, --tags` | only show tags
`-e, --elapsed` | only show time elapsed
`--help` | Show this message and exit.

## `stop`

```bash
Usage:  tt stop [OPTIONS]
```

Stop monitoring time for the current project.

### Options

Flag | Help
-----|-----
`--at DATETIME` | Stop frame at this time. Must be in (YYYY-MM-DDT)?HH:MM(:SS)? format.
`--help` | Show this message and exit.

## `tags`

```bash
Usage:  tt tags [OPTIONS] [PROJECTS]...
```

Display the list of all the tags, or only those matching all the provided
projects.

### Options

Flag | Help
-----|-----
`--help` | Show this message and exit.

