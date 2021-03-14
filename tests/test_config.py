# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Unit tests for the 'config' module."""

import pytest

from xtimetracker.cli.utils import create_configuration
from xtimetracker.config import ConfigurationError


def test_config_dir(config):
    assert 'pytest-' in config.config_dir


def test_config_wrong():
    content = """
toto
    """
    with pytest.raises(ConfigurationError):
        create_configuration(content)


def test_config_empty():
    config = create_configuration('')
    assert len(config.sections()) == 0


def test_config_reload_from_string(config):
    content = """
[section]
option1 = foo
other_option =
    """
    config.reload(content)
    assert config.get('section', 'option1') == 'foo'
    assert config.get('section', 'other_option') == ''
    content = """
[other_section]
option2 = foo
other_option = bar
    """
    config.reload(content)
    assert config.get('section', 'option1') is None
    assert config.get('section', 'other_option') is None
    assert config.get('other_section', 'option2') == 'foo'
    assert config.get('other_section', 'other_option') == 'bar'


def test_config_get():
    content = """
[section]
option1 = foo
other_option =
    """
    config = create_configuration(content)
    assert config.get('section', 'option1') == 'foo'
    assert config.get('section', 'other_option') == ''
    assert config.get('section', 'foo') is None
    assert config.get('section', 'foo', 'bar') == 'bar'
    assert config.get('option', 'spamm') is None
    assert config.get('option', 'spamm', 'eggs') == 'eggs'


def test_config_getboolean():
    content = """
[options]
flag1 = 1
flag2 = ON
flag3 = True
flag4 = yes
flag5 = false
flag6 =
    """
    config = create_configuration(content)
    assert config.getboolean('options', 'flag1') is True
    assert config.getboolean('options', 'flag1', False) is True
    assert config.getboolean('options', 'flag2') is True
    assert config.getboolean('options', 'flag3') is True
    assert config.getboolean('options', 'flag4') is True
    assert config.getboolean('options', 'flag5') is False
    assert config.getboolean('options', 'flag6') is False
    assert config.getboolean('options', 'flag6', True) is True
    assert config.getboolean('options', 'missing') is False
    assert config.getboolean('options', 'missing', True) is True


def test_config_getint():
    content = """
[options]
value1 = 42
value2 = spamm
value3 =
    """
    config = create_configuration(content)
    assert config.getint('options', 'value1') == 42
    assert config.getint('options', 'value1', 666) == 42
    assert config.getint('options', 'missing') is None
    assert config.getint('options', 'missing', 23) == 23
    # default is not converted!
    assert config.getint('options', 'missing', '42') == '42'
    assert config.getint('options', 'missing', 6.66) == 6.66

    with pytest.raises(ValueError):
        config.getint('options', 'value2')

    with pytest.raises(ValueError):
        config.getint('options', 'value3')


def test_config_getfloat():
    content = """
[options]
value1 = 3.14
value2 = 42
value3 = spamm
value4 =
    """
    config = create_configuration(content)
    assert config.getfloat('options', 'value1') == 3.14
    assert config.getfloat('options', 'value1', 6.66) == 3.14
    assert config.getfloat('options', 'value2') == 42.0
    assert isinstance(config.getfloat('options', 'value2'), float)
    assert config.getfloat('options', 'missing') is None
    assert config.getfloat('options', 'missing', 3.14) == 3.14
    # default is not converted!
    assert config.getfloat('options', 'missing', '3.14') == '3.14'

    with pytest.raises(ValueError):
        config.getfloat('options', 'value3')

    with pytest.raises(ValueError):
        config.getfloat('options', 'value4')


def test_config_getlist():
    content = """
# empty lines in option values (including the first one) are discarded
[options]
value1 =
    one

    two three
    four
    five six
# multiple inner space preserved
value2 = one  "two three" four 'five  six'
value3 = one
    two  three
# outer space stripped
value4 = one
     two three
    four
# hash char not at start of line does not start comment
value5 = one
   two #three
   four # five
"""
    config = create_configuration(content)
    assert config.getlist('options', 'value1') == ['one', 'two three', 'four', 'five six']
    assert config.getlist('options', 'value2') == ['one', 'two three', 'four', 'five  six']
    assert config.getlist('options', 'value3') == ['one', 'two  three']
    assert config.getlist('options', 'value4') == ['one', 'two three', 'four']
    assert config.getlist('options', 'value5') == ['one', 'two #three', 'four # five']

    # default values
    assert config.getlist('options', 'novalue') == []
    assert config.getlist('options', 'novalue', None) == []
    assert config.getlist('options', 'novalue', 42) == 42
    assert config.getlist('nosection', 'dummy') == []
    assert config.getlist('nosection', 'dummy', None) == []
    assert config.getlist('nosection', 'dummy', 42) == 42

    default = config.getlist('nosection', 'dummy')
    default.append(42)
    assert config.getlist('nosection', 'dummy') != [42], (
        "Modifying default return value should not have side effect.")


def test_config_set():
    config = create_configuration()
    config.set('foo', 'bar', 'lol')
    assert config.get('foo', 'bar') == 'lol'
