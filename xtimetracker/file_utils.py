# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import shutil
import tempfile
import os
import json

from .utils import TimeTrackerError


class FileIOError(TimeTrackerError):
    pass


def safe_save(path, content, ext='.bak'):
    """
    Save given content to file at given path safely.

    `content` may either be a (unicode) string to write to the file, or a
    function taking one argument, a file object opened for writing. The
    function may write (unicode) strings to the file object (but doesn't need
    to close it).

    The file to write to is created at a temporary location first. If there is
    an error creating or writing to the temp file or calling `content`, the
    destination file is left untouched. Otherwise, if all is well, an existing
    destination file is backed up to `path` + `ext` (defaults to '.bak') and
    the temporary file moved into its place.

    """
    tmpfp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    try:
        with tmpfp as fp:
            if isinstance(content, str):
                fp.write(content)
            else:
                content(fp)
    except Exception as e:
        try:
            os.unlink(tmpfp.name)
        except (IOError, OSError):
            pass
        raise FileIOError("Error writing file '{}': {}".format(tmpfp.name, e))
    else:
        dirname = os.path.dirname(path)
        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        except (IOError, OSError) as e:
            raise FileIOError("Error creating directory '{}': {}".format(dirname, e))

        if os.path.exists(path):
            try:
                os.unlink(path + ext)
            except OSError:
                pass
            shutil.move(path, path + ext)

        shutil.move(tmpfp.name, path)


def load_json(filename, type=dict):
    """
    Return the content of the the given JSON file.
    If the file doesn't exist, return an empty instance of the
    given type.
    """
    try:
        with open(filename) as f:
            return json.load(f)
    except FileNotFoundError:
        return type()
    except ValueError as e:
        # If we get an error because the file is empty, we ignore
        # it and return an empty dict. Otherwise, we raise
        # an exception in order to avoid corrupting the file.
        if os.path.getsize(filename) == 0:
            return type()
        else:
            raise TimeTrackerError(
                "Invalid JSON file {}: {}".format(filename, e)
            )
    except Exception as e:
        raise TimeTrackerError(
            "Unexpected error while loading JSON file {}: {}".format(
                filename, e
            )
        )


def json_writer(func, *args, **kwargs):
    """
    Return a function that receives a file-like object and writes the
    return value of func(*args, **kwargs) as JSON to it.
    """
    def writer(f):
        dump = json.dumps(
            func(*args, **kwargs), indent=1, ensure_ascii=False)
        f.write(dump)
    return writer
