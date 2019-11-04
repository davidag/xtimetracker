from arrow import Arrow
from watson.frames import Span


def test_span_union():
    d1 = Arrow.fromtimestamp(1000)
    d2 = Arrow.fromtimestamp(2000)
    d3 = Arrow.fromtimestamp(3000)
    s1 = Span(d1, d2, timeframe='second')
    s2 = Span(d2, d3, timeframe='second')
    s3 = s1 | s2
    assert s3.start.timestamp == 1000 and s3.stop.timestamp == 3000


def test_span_disjoint_union():
    d1 = Arrow.fromtimestamp(1000)
    d2 = Arrow.fromtimestamp(1500)
    d3 = Arrow.fromtimestamp(3000)
    d4 = Arrow.fromtimestamp(4500)
    s1 = Span(d1, d2, timeframe='second')
    s2 = Span(d3, d4, timeframe='second')
    s3 = s1 | s2
    assert s3.start.timestamp == 1000 and s3.stop.timestamp == 4500


def test_span_union_keeps_original():
    d1 = Arrow.fromtimestamp(1000)
    d2 = Arrow.fromtimestamp(1500)
    d3 = Arrow.fromtimestamp(3000)
    d4 = Arrow.fromtimestamp(4500)
    s1 = Span(d1, d2, timeframe='second')
    s1o = s1
    s2 = Span(d3, d4, timeframe='second')
    s1 |= s2
    assert id(s1) != id(s1o)
    assert s1o.start.timestamp == 1000 and s1o.stop.timestamp == 1500
    assert s1.start.timestamp == 1000 and s1.stop.timestamp == 4500
