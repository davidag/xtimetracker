"""Unit tests for the 'file_utils' module."""

import os

import pytest

from tt.file_utils import safe_save


def test_safe_save(config_dir):
    save_file = os.path.join(config_dir, 'test')
    backup_file = os.path.join(config_dir, 'test' + '.bak')

    assert not os.path.exists(save_file)
    safe_save(save_file, lambda f: f.write("Success"))
    assert os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Success"

    safe_save(save_file, "Again")
    assert os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Again"

    with open(backup_file) as fp:
        assert fp.read() == "Success"

    assert os.path.getmtime(save_file) >= os.path.getmtime(backup_file)


def test_safe_save_tmpfile_on_other_filesystem(config_dir, mocker):
    save_file = os.path.join(config_dir, 'test')
    backup_file = os.path.join(config_dir, 'test' + '.bak')

    assert not os.path.exists(save_file)
    safe_save(save_file, lambda f: f.write("Success"))
    assert os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Success"

    # simulate tmpfile being on another file-system
    # OSError is caught and handled by shutil.move() used by save_safe()
    mocker.patch('os.rename', side_effect=OSError)
    safe_save(save_file, "Again")
    assert os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Again"


def test_safe_save_with_exception(config_dir):
    save_file = os.path.join(config_dir, 'test')
    backup_file = os.path.join(config_dir, 'test' + '.bak')

    def failing_writer(f):
        raise RuntimeError("Save failed.")

    assert not os.path.exists(save_file)

    with pytest.raises(RuntimeError):
        safe_save(save_file, failing_writer)

    assert not os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    safe_save(save_file, lambda f: f.write("Success"))
    assert os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    with pytest.raises(RuntimeError):
        safe_save(save_file, failing_writer)

    with open(save_file) as fp:
        assert fp.read() == "Success"

    assert not os.path.exists(backup_file)
