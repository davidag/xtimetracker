import itertools


def deduplicate(sequence):
    """
    Return a list with all items of the input sequence but duplicates
    removed.

    Leaves the input sequence unaltered.
    """
    return [element
            for index, element in enumerate(sequence)
            if element not in sequence[:index]]


def sorted_groupby(iterator, key, reverse=False):
    """
    Similar to `itertools.groupby`, but sorts the iterator with the same
    key first.
    """
    return itertools.groupby(sorted(iterator, key=key, reverse=reverse), key)
