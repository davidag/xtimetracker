"""Provide fixtures for pytest-based unit tests."""

import os
import py
import pytest

from watson import Watson


TEST_FIXTURE_DIR = py.path.local(
    os.path.dirname(
        os.path.realpath(__file__)
        )
    ) / 'resources'


@pytest.fixture
def config_dir(tmpdir):
    return str(tmpdir.mkdir('config'))


@pytest.fixture
def watson(config_dir):
    """Creates a Watson object with an empty config directory."""
    return Watson(config_dir=config_dir)


@pytest.fixture
def watson_df(datafiles):
    """Creates a Watson object with datafiles in config directory."""
    return Watson(config_dir=str(datafiles))
