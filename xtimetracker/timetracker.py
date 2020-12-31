# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import datetime
import operator
import arrow
from collections import defaultdict
from functools import reduce
from typing import List

from .backend import Backend
from .config import Config
from .utils import deduplicate, sorted_groupby, TimeTrackerError
from .frames import Span


class TimeTracker:
    def __init__(self, config: Config, **kwargs):
        """
        :param config: Configuration object to use.
        :type config: _ConfigParser
        """
        self.config = config
        self._current = None
        self._frames = None
        self._backend = Backend(config)

    def save(self):
        self._backend.save(self._current, self._frames)

    @property
    def frames(self):
        if self._frames is None:
            self._frames = self._backend.load_frames()
        return self._frames

    @property
    def current(self):
        if self._current is None:
            self._current = self._backend.load_state()
        return self._current

    @property
    def is_started(self):
        return self.current

    def full_span(self, include_current: bool = False) -> Span:
        s = self.frames.span
        if include_current and self.is_started:
            s |= Span(self.current['start'], arrow.now())
        return s

    def add(self, project: str, from_date: arrow.Arrow, to_date: arrow.Arrow, tags: List[str]):
        if not project:
            raise TimeTrackerError("No project given.")
        if from_date > to_date:
            raise TimeTrackerError("Task cannot end before it starts.")

        default_tags = self.config.getlist('default_tags', project)
        tags = (tags or []) + default_tags

        frame = self.frames.add(project, from_date, to_date, tags=tags)
        return frame

    def edit(self, id: str, project: str, start: arrow.Arrow, stop: arrow.Arrow, tags: List[str]):
        if id:
            self.frames[id] = (project, start, stop, tags)
        else:
            self.current = dict(start=start, project=project, tags=tags)

    def start(self, project, tags=None, stretch=False):
        assert not self.is_started
        default_tags = self.config.getlist('default_tags', project)
        tags = (tags or []) + default_tags
        new_frame = {
            'project': project,
            'tags': deduplicate(tags)
        }
        if stretch and len(self.frames) > 0:
            max_elapsed = self.config.getint('options', 'autostretch_max_elapsed_secs', 28800)
            if arrow.now().timestamp - self.frames[-1].stop.timestamp < max_elapsed:
                new_frame['start'] = self.frames[-1].stop
        if 'start' not in new_frame:
            new_frame['start'] = arrow.now()
        self._current = new_frame
        return self._current

    def stop(self):
        if not self.is_started:
            raise TimeTrackerError("No project started.")
        frame = self.frames.add(
            self._current['project'],
            self._current['start'],
            arrow.now(),
            tags=self._current['tags']
        )
        self._current = None
        return frame

    def cancel(self):
        if not self.is_started:
            raise TimeTrackerError("No project started.")
        old_current = self._current
        self._current = None
        return old_current

    def projects(self, tags=None):
        """
        Return the list of all the existing projects, sorted by name.
        """
        frames = self.frames.filter(tags=tags)
        matched_tags = defaultdict(set)
        projects = set()
        for f in frames:
            for t in f.tags:
                matched_tags[t].add(f.project)
            projects.add(f.project)
        return sorted(
            p for p in projects
            if not tags or all(p in matched_tags[t] for t in tags))

    def tags(self, projects=None):
        """
        Return the list of the tags, sorted by name.
        """
        frames = self.frames.filter(projects=projects)
        matched_projects = defaultdict(set)
        tags = set()
        for f in frames:
            for t in f.tags:
                matched_projects[f.project].add(t)
                tags.add(t)
        return sorted(
            t for t in tags
            if not projects or all(t in matched_projects[p] for p in projects))

    def _validate_inclusion_options(self, included, excluded):
        return not bool(
            included
            and excluded
            and set(included).intersection(set(excluded))
        )

    def log(self, from_, to, current=None, projects=None, tags=None,
            ignore_projects=None, ignore_tags=None, year=None, month=None,
            week=None, day=None, full=None):
        for start_time in (_ for _ in [day, week, month, year, full]
                           if _ is not None):
            from_ = start_time

        if not self._validate_inclusion_options(projects, ignore_projects):
            raise TimeTrackerError(
                "given projects can't be ignored at the same time")

        if not self._validate_inclusion_options(tags, ignore_tags):
            raise TimeTrackerError(
                "given tags can't be ignored at the same time")

        if from_ > to:
            raise TimeTrackerError("'from' must be anterior to 'to'")

        if current is None:
            current = self.config.getboolean('options', 'include_current')

        if self.is_started and current:
            cur = self.current
            self.frames.add(cur['project'], cur['start'], arrow.now(),
                            cur['tags'], id="current")

        span = Span(from_, to)
        filtered_frames = self.frames.filter(
            projects=projects,
            tags=tags,
            ignore_projects=ignore_projects,
            ignore_tags=ignore_tags,
            span=span,
        )

        return filtered_frames

    def report(self, from_, to, current=None, projects=None, tags=None,
               ignore_projects=None, ignore_tags=None, year=None,
               month=None, week=None, day=None, full=None):

        filtered_frames = self.log(
            from_,
            to,
            current=current,
            projects=projects,
            tags=tags,
            ignore_projects=ignore_projects,
            ignore_tags=ignore_tags,
            year=year,
            month=month,
            week=week,
            day=day,
            full=full
        )

        frames_by_project = sorted_groupby(
            filtered_frames,
            operator.attrgetter('project')
        )

        # After sorting by project, the filtered_frames generator has been
        # consumed and this removal does not affect frames_by_project.
        # That's why we don't delete the current frame inside log().
        if self.is_started and current:
            del self.frames['current']

        total = datetime.timedelta()
        span = Span(from_, to)

        report = {
             'timespan': {
                 'from': span.start,
                 'to': span.stop,
             },
             'projects': []
        }

        for project, frames in frames_by_project:
            frames = tuple(frames)
            delta = reduce(
                operator.add,
                (f.stop.datetime - f.start.datetime for f in frames),
                datetime.timedelta()
            )
            total += delta

            project_report = {
                'name': project,
                'time': delta.total_seconds(),
                'tags': []
            }

            if tags is None:
                tags = []

            tags_to_print = sorted(
                set(tag for frame in frames for tag in frame.tags
                    if tag in tags or not tags)
            )

            for tag in tags_to_print:
                delta = reduce(
                    operator.add,
                    (f.stop.datetime - f.start.datetime
                     for f in frames
                     if tag in f.tags),
                    datetime.timedelta()
                )

                project_report['tags'].append({
                    'name': tag,
                    'time': delta.total_seconds()
                })

            report['projects'].append(project_report)

        report['time'] = total.total_seconds()
        return report
