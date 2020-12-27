# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

from functools import wraps
from .config import create_configuration
from .cli_utils import create_timetracker, parse_tags


def patch_click_ctx_object(func):
    # When pallets/click#942 is fixed, this won't be needed...
    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > 0:
            ctx = args[0]
        elif 'ctx' in kwargs:
            ctx = kwargs['ctx']
        if ctx.obj is None:
            ctx.obj = create_timetracker(create_configuration())
        return func(*args, **kwargs)
    return wrapper


@patch_click_ctx_object
def get_project_or_tag_completion(ctx, args, incomplete):
    """Function to autocomplete either organisations or tasks, depending on the
       shape of the current argument."""

    assert isinstance(incomplete, str)

    def get_incomplete_tag(args, incomplete):
        """Get incomplete tag from command line string."""
        cmd_line = " ".join(args + [incomplete])
        found_tags = parse_tags(cmd_line)
        return found_tags[-1] if found_tags else ""

    def fix_broken_tag_parsing(incomplete_tag):
        """
        Remove spaces from parsed tag

        The function `parse_tags` inserts a space after each character. In
        order to obtain the actual command line part, the space needs to be
        removed.
        """
        return "".join(char for char in incomplete_tag.split(" "))

    def prepend_plus(tag_suggestions):
        """
        Prepend '+' to each tag suggestion.

        For the `xtt` targeted with the function
        get_project_or_tag_completion, a leading plus in front of a tag is
        expected. The get_tags() suggestion generation does not include those
        as it targets other subcommands.

        In order to not destroy the current tag stub, the plus must be
        prepended.
        """
        for cur_suggestion in tag_suggestions:
            yield "+{cur_suggestion}".format(cur_suggestion=cur_suggestion)

    project_is_completed = any(
        tok.startswith("+") for tok in args + [incomplete]
    )
    if project_is_completed:
        incomplete_tag = get_incomplete_tag(args, incomplete)
        fixed_incomplete_tag = fix_broken_tag_parsing(incomplete_tag)
        tag_suggestions = get_tags(ctx, args, fixed_incomplete_tag)
        return prepend_plus(tag_suggestions)
    else:
        return get_projects(ctx, args, incomplete)


@patch_click_ctx_object
def get_projects(ctx, args, incomplete):
    """Function to return all projects matching the prefix."""
    timetracker = ctx.obj
    for cur_project in timetracker.projects():
        if cur_project.startswith(incomplete):
            yield cur_project


@patch_click_ctx_object
def get_tags(ctx, args, incomplete):
    """Function to return all tags matching the prefix."""
    timetracker = ctx.obj
    for cur_tag in timetracker.tags():
        if cur_tag.startswith(incomplete):
            yield cur_tag


@patch_click_ctx_object
def get_frames(ctx, args, incomplete):
    """
    Return all matching frame IDs

    This function returns all frame IDs that match the given prefix in a
    generator. If no ID matches the prefix, it returns the empty generator.
    """
    timetracker = ctx.obj
    for cur_frame in timetracker.frames:
        yield_candidate = cur_frame.id
        if yield_candidate.startswith(incomplete):
            yield yield_candidate
