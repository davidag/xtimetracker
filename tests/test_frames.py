# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 David Alfonso
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

import arrow

from xtimetracker.frames import Span, Frames, Frame


def test_span_union():
    d1 = arrow.get(1000)
    d2 = arrow.get(2000)
    d3 = arrow.get(3000)
    s1 = Span(d1, d2, timeframe='second')
    s2 = Span(d2, d3, timeframe='second')
    s3 = s1 | s2
    assert s3.start.timestamp == 1000 and s3.stop.timestamp == 3000


def test_span_disjoint_union():
    d1 = arrow.get(1000)
    d2 = arrow.get(1500)
    d3 = arrow.get(3000)
    d4 = arrow.get(4500)
    s1 = Span(d1, d2, timeframe='second')
    s2 = Span(d3, d4, timeframe='second')
    s3 = s1 | s2
    assert s3.start.timestamp == 1000 and s3.stop.timestamp == 4500


def test_span_union_keeps_original():
    d1 = arrow.get(1000)
    d2 = arrow.get(1500)
    d3 = arrow.get(3000)
    d4 = arrow.get(4500)
    s1 = Span(d1, d2, timeframe='second')
    s1o = s1
    s2 = Span(d3, d4, timeframe='second')
    s1 |= s2
    assert id(s1) != id(s1o)
    assert s1o.start.timestamp == 1000 and s1o.stop.timestamp == 1500
    assert s1.start.timestamp == 1000 and s1.stop.timestamp == 4500


def test_frames_empty():
    f = Frames()
    assert len(f) == 0


def test_frames_span():
    f = Frames([Frame("2019-01-15 13:30:00", "2019-01-15 14:30:00", "p", "1")])
    assert len(f) == 1
    assert f.span.start.format("YYYY-MM-DD HH:mm:ss") == "2019-01-15 00:00:00"
    assert f.span.stop.format("YYYY-MM-DD HH:mm:ss") == "2019-01-15 23:59:59"


def test_frames_updated_span():
    f = Frames([Frame("2019-01-15 13:30:00", "2019-01-15 14:30:00", "p", "1")])
    f.add("p", "2019-01-01 12:30:00", "2019-01-01 13:30:00")
    assert f.span.start.format("YYYY-MM-DD HH:mm:ss") == "2019-01-01 00:00:00"
    assert f.span.stop.format("YYYY-MM-DD HH:mm:ss") == "2019-01-15 23:59:59"
    f.add("p", "2019-02-01 14:30:00", "2019-02-01 15:30:00")
    assert f.span.start.format("YYYY-MM-DD HH:mm:ss") == "2019-01-01 00:00:00"
    assert f.span.stop.format("YYYY-MM-DD HH:mm:ss") == "2019-02-01 23:59:59"
