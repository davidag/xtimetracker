# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import arrow
from dateutil import tz

from .config import Config
from .frames import Frames
from .file_utils import safe_save, json_writer, load_json
from .utils import TimeTrackerError


class Backend:
    """
    Handles file I/O to save/load data from a backend (currently filesystem regular files).
    """
    def __init__(self, config: Config):
        self._config = config
        self._frames_file = os.path.join(self._config.config_dir, 'frames')
        self._state_file = os.path.join(self._config.config_dir, 'state')
        self._last_state = None

    def save(self, state: dict, frames: Frames):
        """
        Save the state in the appropriate files. Create them if necessary.
        """
        try:
            if self._last_state is None or state != self._last_state:
                if state is not None:
                    raw_state = {
                        'project': state['project'],
                        'start': state['start'].timestamp,
                        'tags': state.get('tags', []),
                    }
                else:
                    raw_state = {}
                safe_save(self._state_file, json_writer(lambda: raw_state))
                self._last_state = state

            if frames is not None and frames.changed:
                safe_save(self._frames_file, json_writer(frames.dump))

        except OSError as e:
            raise TimeTrackerError(
                "Error writing file '{}': {}".format(e.filename, e)
            )

    def load_state(self) -> dict:
        raw_state = load_json(self._state_file)

        if not raw_state or 'project' not in raw_state:
            self._last_state = {}
            return self._last_state

        self._last_state = {
            'project': raw_state['project'],
            'start': arrow.get(raw_state['start'], tzinfo=tz.tzlocal()),
            'tags': raw_state.get('tags') or []
        }
        return self._last_state

    def load_frames(self) -> Frames:
        raw_frames = load_json(self._frames_file, type=list)
        return Frames(raw_frames)
