# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Unit tests for the 'autocompletion' module."""

import json
from argparse import Namespace

import pytest

from tt.autocompletion import (
    get_frames,
    get_project_or_tag_completion,
    get_projects,
    get_tags,
)
from tt.timetracker import TimeTracker

from . import TEST_FIXTURE_DIR


AUTOCOMPLETION_FRAMES_PATH = TEST_FIXTURE_DIR / "autocompletion"
with open(str(AUTOCOMPLETION_FRAMES_PATH / "frames")) as fh:
    N_FRAMES = len(json.load(fh))
N_PROJECTS = 5
N_TASKS = 3
N_VARIATIONS_OF_PROJECT3 = 2
N_FRAME_IDS_FOR_PREFIX = 2

ClickContext = Namespace


@pytest.mark.datafiles(AUTOCOMPLETION_FRAMES_PATH)
@pytest.mark.parametrize(
    "func_to_test, args",
    [
        (get_frames, []),
        (get_project_or_tag_completion, ["project1", "+tag1"]),
        (get_project_or_tag_completion, []),
        (get_projects, []),
        (get_tags, []),
    ],
)
def test_if_returned_values_are_distinct(
    timetracker_df, func_to_test, args
):
    ctx = ClickContext(obj=timetracker_df)
    prefix = ""
    ret_list = list(func_to_test(ctx, args, prefix))
    assert sorted(ret_list) == sorted(set(ret_list))


@pytest.mark.datafiles(AUTOCOMPLETION_FRAMES_PATH)
@pytest.mark.parametrize(
    "func_to_test, n_expected_returns, args",
    [
        (get_frames, N_FRAMES, []),
        (get_project_or_tag_completion, N_TASKS, ["project1", "+"]),
        (get_project_or_tag_completion, N_PROJECTS, []),
        (get_projects, N_PROJECTS, []),
        (get_tags, N_TASKS, []),
    ],
)
def test_if_empty_prefix_returns_everything(
    timetracker_df, func_to_test, n_expected_returns, args
):
    prefix = ""
    ctx = ClickContext(obj=timetracker_df)
    completed_vals = set(func_to_test(ctx, args, prefix))
    assert len(completed_vals) == n_expected_returns


@pytest.mark.datafiles(AUTOCOMPLETION_FRAMES_PATH)
@pytest.mark.parametrize(
    "func_to_test, args",
    [
        (get_frames, []),
        (get_project_or_tag_completion, ["project1", "+"]),
        (get_project_or_tag_completion, ["project1", "+tag1", "+"]),
        (get_project_or_tag_completion, []),
        (get_projects, []),
        (get_tags, []),
    ],
)
def test_completion_of_nonexisting_prefix(
    timetracker_df, func_to_test, args
):
    ctx = ClickContext(obj=timetracker_df)
    prefix = "NOT-EXISTING-PREFIX"
    ret_list = list(func_to_test(ctx, args, prefix))
    assert not ret_list


@pytest.mark.datafiles(AUTOCOMPLETION_FRAMES_PATH)
@pytest.mark.parametrize(
    "func_to_test, prefix, n_expected_vals, args",
    [
        (get_frames, "f4f7", N_FRAME_IDS_FOR_PREFIX, []),
        (
            get_project_or_tag_completion,
            "+tag",
            N_TASKS,
            ["project1", "+tag3"],
        ),
        (get_project_or_tag_completion, "+tag", N_TASKS, ["project1"]),
        (
            get_project_or_tag_completion,
            "project3",
            N_VARIATIONS_OF_PROJECT3,
            [],
        ),
        (get_projects, "project3", N_VARIATIONS_OF_PROJECT3, []),
        (get_tags, "tag", N_TASKS, []),
    ],
)
def test_completion_of_existing_prefix(
    timetracker_df, func_to_test, prefix, n_expected_vals, args
):
    ctx = ClickContext(obj=timetracker_df)
    ret_set = set(func_to_test(ctx, args, prefix))
    assert len(ret_set) == n_expected_vals
    assert all(cur_elem.startswith(prefix) for cur_elem in ret_set)


@pytest.mark.parametrize("func", [
    get_projects, get_tags, get_frames, get_project_or_tag_completion])
def test_timetracker_object_gets_created_if_empty_with_positional_args(func):
    ctx = ClickContext(obj=None)
    func(ctx, [], "")
    assert isinstance(ctx.obj, TimeTracker)


@pytest.mark.parametrize("func", [
    get_projects, get_tags, get_frames, get_project_or_tag_completion])
def test_timetracker_object_gets_created_if_empty_with_keyword_args(func):
    ctx = ClickContext(obj=None)
    func(ctx=ctx, args=[], incomplete="")
    assert isinstance(ctx.obj, TimeTracker)
