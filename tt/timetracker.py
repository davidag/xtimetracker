import datetime
import json
import operator
import os
import configparser
import arrow
from collections import defaultdict
from functools import reduce

from .config import ConfigParser
from .file_utils import safe_save
from .utils import deduplicate, sorted_groupby
from .frames import Frames, Span


class TimeTrackerError(RuntimeError):
    pass


class ConfigurationError(configparser.Error, TimeTrackerError):
    pass


class TimeTracker:
    def __init__(self, **kwargs):
        """
        :param frames: If given, should be a list representing the
                        frames.
                        If not given, the value is extracted
                        from the frames file.
        :type frames: list

        :param current: If given, should be a dict representing the
                        current frame.
                        If not given, the value is extracted
                        from the state file.
        :type current: dict

        :param config_dir: If given, the directory where the configuration
                           files will be
        """
        self._current = None
        self._old_state = None
        self._frames = None
        self._config = None
        self._config_changed = False

        self._dir = kwargs.pop('config_dir', '')

        self.config_file = os.path.join(self._dir, 'config')
        self.frames_file = os.path.join(self._dir, 'frames')
        self.state_file = os.path.join(self._dir, 'state')

        if 'frames' in kwargs:
            self.frames = kwargs['frames']

        if 'current' in kwargs:
            self.current = kwargs['current']

    def _load_json_file(self, filename, type=dict):
        """
        Return the content of the the given JSON file.
        If the file doesn't exist, return an empty instance of the
        given type.
        """
        try:
            with open(filename) as f:
                return json.load(f)
        except IOError:
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

    def _parse_date(self, date):
        """Returns Arrow object from timestamp."""
        return arrow.Arrow.utcfromtimestamp(date).to('local')

    def _format_date(self, date):
        """Returns timestamp from string timestamp or Arrow object."""
        if not isinstance(date, arrow.Arrow):
            date = arrow.get(date)

        return date.timestamp

    def _make_json_writer(func, *args, **kwargs):
        """
        Return a function that receives a file-like object and writes the
        return value of func(*args, **kwargs) as JSON to it.
        """
        def writer(f):
            dump = json.dumps(
                func(*args, **kwargs), indent=1, ensure_ascii=False)
            f.write(dump)
        return writer

    @property
    def config(self):
        """
        Return TimeTracker's config as a ConfigParser object.
        """
        if not self._config:
            try:
                config = ConfigParser()
                config.read(self.config_file)
            except configparser.Error as e:
                raise ConfigurationError(
                    "Cannot parse config file: {}".format(e))

            self._config = config

        return self._config

    @config.setter
    def config(self, value):
        """
        Set a ConfigParser object as the current configuration.
        """
        self._config = value
        self._config_changed = True

    def save(self):
        """
        Save the state in the appropriate files. Create them if necessary.
        """
        try:
            os.makedirs(self._dir, exist_ok=True)

            if self._current is not None and self._old_state != self._current:
                if self.is_started:
                    current = {
                        'project': self.current['project'],
                        'start': self._format_date(self.current['start']),
                        'tags': self.current['tags'],
                    }
                else:
                    current = {}

                safe_save(self.state_file,
                          TimeTracker._make_json_writer(lambda: current))
                self._old_state = current

            if self._frames is not None and self._frames.changed:
                safe_save(self.frames_file,
                          TimeTracker._make_json_writer(self.frames.dump))

            if self._config_changed:
                safe_save(self.config_file, self.config.write)

        except OSError as e:
            raise TimeTrackerError(
                "Impossible to write {}: {}".format(e.filename, e)
            )

    @property
    def frames(self):
        if self._frames is None:
            self.frames = self._load_json_file(self.frames_file, type=list)

        return self._frames

    @frames.setter
    def frames(self, frames):
        self._frames = Frames(frames)

    @property
    def current(self):
        if self._current is None:
            self.current = self._load_json_file(self.state_file)

        if self._old_state is None:
            self._old_state = self._current

        return dict(self._current)

    @current.setter
    def current(self, value):
        if not value or 'project' not in value:
            self._current = {}

            if self._old_state is None:
                self._old_state = {}

            return

        start = value.get('start', arrow.now())

        if not isinstance(start, arrow.Arrow):
            start = self._parse_date(start)

        self._current = {
            'project': value['project'],
            'start': start,
            'tags': value.get('tags') or []
        }

        if self._old_state is None:
            self._old_state = self._current

    @property
    def is_started(self):
        return bool(self.current)

    def span(self, include_current=False):
        s = self.frames.span
        if include_current and self.is_started:
            s |= Span(self.current['start'], arrow.now())
        return s

    def add(self, project, from_date, to_date, tags):
        if not project:
            raise TimeTrackerError("No project given.")
        if from_date > to_date:
            raise TimeTrackerError("Task cannot end before it starts.")

        default_tags = self.config.getlist('default_tags', project)
        tags = (tags or []) + default_tags

        frame = self.frames.add(project, from_date, to_date, tags=tags)
        return frame

    def start(self, project, tags=None, gap=True):
        assert not self.is_started
        default_tags = self.config.getlist('default_tags', project)
        tags = (tags or []) + default_tags
        new_frame = {
            'project': project,
            'tags': deduplicate(tags)
        }
        if not gap:
            stop_of_prev_frame = self.frames[-1].stop
            new_frame['start'] = stop_of_prev_frame
        self.current = new_frame
        return self.current

    def stop(self, stop_at=None):
        if not self.is_started:
            raise TimeTrackerError("No project started.")

        old = self.current

        if stop_at is None:
            # One cannot use `arrow.now()` as default argument. Default
            # arguments are evaluated when a function is defined, not when its
            # called. Since there might be huge delays between defining this
            # stop function and calling it, the value of `stop_at` could be
            # outdated if defined using a default argument.
            stop_at = arrow.now()
        if old['start'] > stop_at:
            raise TimeTrackerError('Task cannot end before it starts.')
        if stop_at > arrow.now():
            raise TimeTrackerError('Task cannot end in the future.')

        frame = self.frames.add(
            old['project'], old['start'], stop_at, tags=old['tags']
        )
        self.current = None

        return frame

    def cancel(self):
        if not self.is_started:
            raise TimeTrackerError("No project started.")

        old_current = self.current
        self.current = None
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

    def rename_project(self, old_project, new_project):
        """Rename a project in all affected frames."""
        if old_project not in self.projects():
            raise TimeTrackerError('Project "%s" does not exist' % old_project)

        updated_at = arrow.utcnow()
        # rename project
        for frame in self.frames:
            if frame.project == old_project:
                self.frames[frame.id] = frame._replace(
                    project=new_project,
                    updated_at=updated_at
                )

        self.frames.changed = True
        self.save()

    def rename_tag(self, old_tag, new_tag):
        """Rename a tag in all affected frames."""
        if old_tag not in self.tags():
            raise TimeTrackerError('Tag "%s" does not exist' % old_tag)

        updated_at = arrow.utcnow()
        # rename tag
        for frame in self.frames:
            if old_tag in frame.tags:
                self.frames[frame.id] = frame._replace(
                    tags=[new_tag if t == old_tag else t for t in frame.tags],
                    updated_at=updated_at
                )

        self.frames.changed = True
        self.save()