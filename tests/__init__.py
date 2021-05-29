# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Utility functions for the unit tests."""

import os
import datetime
from unittest import mock

import py


TEST_FIXTURE_DIR = (
    py.path.local(os.path.dirname(os.path.realpath(__file__))) / "resources"
)


def mock_datetime(dt, dt_module):
    class DateTimeMeta(type):
        @classmethod
        def __instancecheck__(mcs, obj):
            return isinstance(obj, datetime.datetime)

    class BaseMockedDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.replace(tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return dt

        @classmethod
        def today(cls):
            return dt

    MockedDateTime = DateTimeMeta("datetime", (BaseMockedDateTime,), {})

    return mock.patch.object(dt_module, "datetime", MockedDateTime)
