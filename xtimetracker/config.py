# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""A convenience and compatibility wrapper for ConfigParser."""
import os
import shlex
import configparser

from click import get_app_dir

from .utils import TimeTrackerError


class ConfigurationError(configparser.Error, TimeTrackerError):
    pass


class Config(configparser.ConfigParser):
    """A simple wrapper for ConfigParser to make options access easier."""

    def __init__(self, config_dir=None, **kwargs):
        if config_dir is None:
            self.config_dir = os.environ.get('XTIMETRACKER_DIR', get_app_dir('xtimetracker'))
        else:
            self.config_dir = config_dir
        self.config_file = os.path.join(self.config_dir, 'config')
        super().__init__(**kwargs)

    def reload(self, contents=None):
        """
        Reloads the configuration from a file or string.
        """
        for section in self.sections():
            self.remove_section(section)

        try:
            if contents is not None:
                self.read_string(contents)
            else:
                self.read(self.config_file)
        except configparser.Error as e:
            raise ConfigurationError("Cannot parse config: {}".format(e))

    def get(self, section, option, default=None, **kwargs):
        """
        Return value of option in given configuration section as a string.

        If option is not set, return default instead (defaults to None).
        """
        return super().get(section, option, fallback=default, **kwargs)

    def getint(self, section, option, default=None):
        """
        Return value of option in given configuration section as an integer.

        If option is not set, return default (defaults to None).

        Raises ValueError if the value cannot be converted to an integer.
        """
        val = self.get(section, option)
        return default if val is None else int(val)

    def getfloat(self, section, option, default=None):
        """
        Return value of option in given configuration section as a float.

        If option is not set, return default (defaults to None).

        Raises ValueError if the value cannot be converted to a float.

        """
        val = self.get(section, option)
        return default if val is None else float(val)

    def getboolean(self, section, option, default=False):
        """
        Return value of option in given configuration section as a boolean.

        A configuration option is considered true when it has one of the
        following values: '1', 'on', 'true' or 'yes'. The comparison is
        case-insensitive. All other values are considered false.

        If option is not set or empty, return default (defaults to False).
        """
        val = self.get(section, option)
        return val.lower() in ('1', 'on', 'true', 'yes') if val else default

    def getlist(self, section, option, default=None):
        """
        Return value of option in given section as a list of strings.

        If option is not set, return default (defaults to an empty list).

        The option value is split into list tokens using one of two strategies:

        * If the value contains any newlines, i.e. it was written in the
          configuration file using continuation lines, the value is split at
          newlines and empty items are discarded.
        * Otherwise, the value is split according to unix shell parsing rules.
          Items are separated by whitespace, but items can be enclosed in
          single or double quotes to preserve spaces in them.

        Example::

            [test]
            option2 =
                one
                two three
                four
                five six
            option1 = one  "two three" four 'five  six'
        """
        if not self.has_option(section, option):
            return [] if default is None else default

        value = self.get(section, option)

        if '\n' in value:
            return [item.strip()
                    for item in value.splitlines() if item.strip()]
        else:
            return shlex.split(value)

    def set(self, section, option, value):
        """
        Set option in given configuration section to value.

        If section does not exist yet, it is added implicitly.
        """
        if not self.has_section(section):
            self.add_section(section)

        super().set(section, option, value)


def create_configuration(contents=None, config_dir=None) -> Config:
    c = Config(config_dir=config_dir, interpolation=None)
    c.reload(contents)
    return c
