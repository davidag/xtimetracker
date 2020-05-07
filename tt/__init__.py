# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

from .version import version
from .timetracker import TimeTracker, TimeTrackerError

__all__ = ['TimeTracker', 'TimeTrackerError']
__version__ = version
