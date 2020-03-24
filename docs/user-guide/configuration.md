# Configuration

## The configuration file

Tt configuration and data are stored inside your user's application folder. Depending on your system, the default path is likely:

* **MacOSX**: `~/Library/Application Support/tt/config`
* **Windows**: `%appdata%\tt\config`, which usually expands to `C:\Users\<user>\AppData\Roaming\tt\config`
* **Linux**: `~/.config/tt/config`

The configuration file is a typical [python configuration (INI) file](https://docs.python.org/3.7/library/configparser.html#supported-ini-file-structure), that looks like:

```ini
[Simple Values]
key=value
spaces in keys=allowed
spaces in values=allowed as well
spaces around the delimiter = obviously
you can also use : to delimit keys from values

[All Values Are Strings]
values like this: 1000000
or this: 3.14159265359
are they treated as numbers? : no
integers, floats and booleans are held as: strings
can use the API to get converted values directly: true

[Multiline Values]
chorus: I'm a lumberjack, and I'm okay
    I sleep all night and I work all day


[No Values]
key_without_value
empty string value here =

[You can use comments]
# like this
; or this

# By default only in an empty line.
# Inline comments can be harmful because they prevent users
# from using the delimiting characters as parts of values.
# That being said, this can be customized.

    [Sections Can Be Indented]
        can_values_be_as_well = True
        does_that_mean_anything_special = False
        purpose = formatting for readability
        multiline_values = are
            handled just fine as
            long as they are indented
            deeper than the first line
            of a value
        # Did I mention we can indent comments, too?
```

_This example configuration file has been taken from the [official python documentation](https://docs.python.org/3.7/library/configparser.html#supported-ini-file-structure)._


## Editing

If you want to edit your configuration, the best is to use the [`config`](./commands/#config) command.

You can edit your configuration on the fly with:

```bash
$ tt config SECTION.KEY VALUE
```

Example:

```bash
$ tt config backend.token 7e329263e329  # set configuration
$ tt config backend.token  # display configuration
7e329263e329
```

Or open an editor with:

```bash
$ tt config -e
```

## Available settings

### Options

#### `options.confirm_new_project` (default: `false`)

If `true`, the user will be asked for confirmation before creating a new project. The option can be overriden in the command line with `--confirm-new-project` flag.

#### `options.confirm_new_tag` (default: `false`)

If `true`, the user will be asked for confirmation before creating a new tag. The option can be overriden in the command line with `--confirm-new-tag` flag.

#### `options.date_format` (default: `%Y.%m.%d`)

Globally configure how `dates` should be formatted. All [python's `strftime` directives](http://strftime.org) are supported.

#### `options.include_current` (default: `false`)

If `true`, the output of `log`, `report`, `aggregate` commande will include
the currently running frame (if any) by default. The option can be overridden
on the command line with the `-c/-C` resp. `--current/--no-current` flags.

#### `options.pager` (default: `true`)

If `true`, the output of the `log` and `report` command will be
run through a pager by default. The option can be overridden on the command
line with the `-g/-G` or `--pager/--no-pager` flags. If other commands output
in colour, but `log` or `report` do not, try disabling the pager.

#### `options.stop_on_start` (default: `false`)

If `true`, starting a new project will stop running projects:

```
$ tt start samourai +pizza +cat
Starting project samourai [pizza, cat] at 11:14
$ tt start jayce +wheeled +warriors
Stopping project samourai [pizza, cat], started 2 minutes ago. (id: d08cdd0)
Starting project jayce [wheeled, warriors] at 11:16
```

Please, note that it also works with serious stuffs like:

```
$ tt start voyager2 +reactor +module
Stopping project jayce [wheeled, warriors], started 2 minutes ago. (id: 967965f)
Starting project voyager2 [reactor, module] at 11:18
```

#### `options.stop_on_restart` (default: `false`)

Similar to the `options.stop_on_start` option, but for the [`restart`](./commands.md#restart) command.

#### `options.time_format` (default: `%H:%M:%S%z`)

Globally configure how `time` should be formatted. All [python's `strftime` directives](http://strftime.org) are supported.

#### `options.week_start` (default: `monday`)

Globally configure which day corresponds to the start of a week. Allowable
values are `monday`, `tuesday`, `wednesday`, `thursday`, `friday`,
 `saturday`, and `sunday`.


### Default tags

Tags can be automatically added for selected projects. This is convenient when
the same tags are always attached to a particular project.

These automatically attached tags are defined in the `[default_tags]` section
of the configuration. Each option in that section is a project to which
tags should be attached. The entries should follow the pattern: `project = tag1 tag2`.

You can set default tags for a project from the command line:

```
$ tt config default_tags.python101 'teaching python'
```

This corresponds to the following configuration file snippets:

```ini
[default_tags]
python101 = teaching python
```

With these default tags set, the tags "teaching" and "python" will
automatically be attached to the project "python101":

```
$ tt start python101
Starting project python101 [teaching, python] at 19:27

$ tt start python101 +lecture
Starting project python101 [lecture, teaching, python] at 19:28
```

Default tags can contain space characters when written in between quotes:

```
$ tt config default_tags.voyager2 'nasa "space mission"'
```

Or in the configuration file:

```ini
[default_tags]
voyager2 = nasa 'space mission'
```

## Sample configuration file

A basic configuration file looks like the following:

```ini
# tt configuration

[backend]
url = https://api.crick.fr
token = yourapitoken

[options]
stop_on_start = true
stop_on_restart = false
date_format = %Y.%m.%d
time_format = %H:%M:%S%z
week_start = monday
log_current = false
pager = true
report_current = false
```

## Application folder

To override tt's default application folder (see first section), you can set the `$TT_DIR` environment variable to the desired path.

It may be defined globally in your shell profile:

```bash
# .bashrc or .profile
export TT_DIR=/path/to/tt/folder
```

or when calling tt:

```bash
$ TT_DIR=/path/to/tt/folder tt status
```

This can be useful to preserve your real data when hacking with tt :)
