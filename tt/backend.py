import os

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
                safe_save(self._state_file, json_writer(lambda: state))
                self._last_state = state

            if frames is not None and frames.changed:
                safe_save(self._frames_file, json_writer(frames.dump))

        except OSError as e:
            raise TimeTrackerError(
                "Error writing file '{}': {}".format(e.filename, e)
            )

    def load_state(self) -> dict:
        self._last_state = load_json(self._state_file)
        return self._last_state

    def load_frames(self) -> list:
        return load_json(self._frames_file, type=list)
