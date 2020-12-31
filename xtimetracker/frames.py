# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import uuid
from copy import copy

import arrow

from .utils import TimeTrackerError


class Frame:
    __slots__ = ('start', 'stop', 'project', 'id', 'tags', 'updated_at')

    def __init__(self, start, stop, project, id, tags=None, updated_at=None):
        try:
            if not isinstance(start, arrow.Arrow):
                start = arrow.get(start)

            if not isinstance(stop, arrow.Arrow):
                stop = arrow.get(stop)

            if updated_at is None:
                self.updated_at = arrow.now()
            elif not isinstance(updated_at, arrow.Arrow):
                self.updated_at = arrow.get(updated_at)
        except (ValueError, TypeError) as e:
            raise TimeTrackerError("Error converting date: {}".format(e))

        self.start = start.to('local')
        self.stop = stop.to('local')
        self.project = project
        self.id = id
        self.tags = [] if tags is None else tags

    def dump(self):
        start = self.start.timestamp
        stop = self.stop.timestamp
        updated_at = self.updated_at.timestamp

        return (start, stop, self.project, self.id, self.tags, updated_at)

    def copy(self, start=None, stop=None) -> "Frame":
        start = copy(self.start) if start is None else start
        stop = copy(self.stop) if stop is None else stop
        tags = copy(self.tags) if self.tags is not None else []
        return Frame(start, stop, self.project, self.id, tags, self.updated_at)

    def __getitem__(self, index):
        """ Make Frame iterable, to be able to do Frame(*frame) """
        try:
            return getattr(self, self.__slots__[index])
        except KeyError:
            raise IndexError

    def __lt__(self, other):
        return self.start < other.start

    def __lte__(self, other):
        return self.start <= other.start

    def __gt__(self, other):
        return self.start > other.start

    def __gte__(self, other):
        return self.start >= other.start


class Span():
    def __init__(self, start, stop, timeframe='day'):
        self.timeframe = timeframe
        self.start = start.floor(self.timeframe)
        self.stop = stop.ceil(self.timeframe)

    def overlaps(self, frame: Frame) -> bool:
        return frame.start <= self.stop and frame.stop >= self.start

    def __or__(self, other: "Span") -> "Span":
        new_span = Span(self.start, self.stop, self.timeframe)
        if other.start < self.start:
            new_span.start = other.start.floor(self.timeframe)
        if other.stop > self.stop:
            new_span.stop = other.stop.ceil(self.timeframe)
        return new_span

    def __contains__(self, frame: Frame) -> bool:
        return frame.start >= self.start and frame.stop <= self.stop


class Frames():
    def __init__(self, frames=None):
        if not frames:
            frames = []
        self._rows = []
        min_start, max_stop = arrow.now(), arrow.get(0)
        for frame in frames:
            f = Frame(*frame)
            min_start = min(min_start, f.start)
            max_stop = max(max_stop, f.stop)
            self._rows.append(f)
        self.span = Span(min_start, max_stop)
        self.changed = False

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._rows[key]
        try:
            return tuple(getattr(row, key) for row in self._rows)
        except AttributeError:
            return self._rows[self._get_index_by_id(key)]

    def __setitem__(self, key, value):
        self.changed = True

        if isinstance(value, Frame):
            frame = value
        else:
            frame = self.new_frame(*value)

        if isinstance(key, int):
            self._rows[key] = frame
        else:
            frame.id = key
            try:
                self._rows[self._get_index_by_id(key)] = frame
            except KeyError:
                self._rows.append(frame)

    def __delitem__(self, key):
        self.changed = True

        if isinstance(key, int):
            del self._rows[key]
        else:
            del self._rows[self._get_index_by_id(key)]

    def _get_index_by_id(self, id):
        try:
            return next(
                i for i, v in enumerate(self['id']) if v.startswith(id)
            )
        except StopIteration:
            raise KeyError("Frame with id {} not found.".format(id))

    def _update_span(self, start, stop):
        min_start = min(start, self.span.start)
        max_stop = max(stop, self.span.stop)
        self.span = Span(min_start, max_stop)

    def add(self, *args, **kwargs):
        self.changed = True
        frame = self.new_frame(*args, **kwargs)
        self._rows.append(frame)
        self._update_span(frame.start, frame.stop)
        return frame

    def new_frame(self, project, start, stop, tags=None, id=None,
                  updated_at=None):
        if not id:
            id = uuid.uuid4().hex
        return Frame(start, stop, project, id, tags=tags,
                     updated_at=updated_at)

    def dump(self):
        return tuple(frame.dump() for frame in self._rows)

    def filter(
        self,
        projects=None,
        tags=None,
        ignore_projects=None,
        ignore_tags=None,
        span=None,
    ):

        for frame in self._rows:
            if projects and frame.project not in projects:
                continue
            if ignore_projects and frame.project in ignore_projects:
                continue

            if tags and not any(tag in frame.tags for tag in tags):
                continue
            if ignore_tags and any(tag in frame.tags for tag in ignore_tags):
                continue

            if not span:
                yield frame
            elif frame in span:
                yield frame
            elif span.overlaps(frame):
                # If requested, return the part of the frame that is within the
                # span, for frames that are *partially* within span or reaching
                # over span
                start = span.start if frame.start < span.start else frame.start
                stop = span.stop if frame.stop > span.stop else frame.stop
                yield frame.copy(start=start, stop=stop)
