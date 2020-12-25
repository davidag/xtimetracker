# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Provide fixtures for pytest-based unit tests."""

import pytest
from click.testing import CliRunner

from tt.timetracker import TimeTracker
from tt.config import create_configuration


@pytest.fixture
def config(tmpdir):
    config_dir = tmpdir.mkdir('config')
    return create_configuration(config_dir=str(config_dir))


@pytest.fixture
def timetracker(config):
    """Creates a TimeTracker object with an empty config directory."""
    return TimeTracker(config)


@pytest.fixture
def timetracker_df(datafiles):
    """Creates a TimeTracker object with datafiles in config directory."""
    config = create_configuration(config_dir=str(datafiles))
    return TimeTracker(config)


@pytest.fixture
def runner():
    return CliRunner()
