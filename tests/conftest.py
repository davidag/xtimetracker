# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Provide fixtures for pytest-based unit tests."""

import pytest
from click.testing import CliRunner

from tt import TimeTracker


@pytest.fixture
def config_dir(tmpdir):
    return str(tmpdir.mkdir('config'))


@pytest.fixture
def timetracker(config_dir):
    """Creates a TimeTracker object with an empty config directory."""
    return TimeTracker(config_dir=config_dir)


@pytest.fixture
def timetracker_df(datafiles):
    """Creates a TimeTracker object with datafiles in config directory."""
    return TimeTracker(config_dir=str(datafiles))


@pytest.fixture
def runner():
    return CliRunner()
