from __future__ import division
from math import ceil
from operator import mul
from functools import reduce
from itertools import product

import pytest
from nchelpers.iteration import chunk_corners, chunk_slices, chunks, \
    opt_chunk_shape

import numpy as np


def size(shape):
    return reduce(mul, shape, 1)


def num_chunks(shape, chunk_shape):
    """Number of chunks of shape ``chunk_shape`` in an array of shape ``shape``."""
    return reduce(mul, (ceil(s/c) for s, c in zip(shape, chunk_shape)), 1)


def union(sets):
    """Union of all sets in iterator ``sets``."""
    result = set()
    for s in sets:
        result = result | s
    return result


def indices(slice, shape):
    """Generator yielding all indices specified by a slice tuple
    constrained by an array of shape ``shape``."""
    return product(*(range(*sl.indices(sh)) for sl, sh in zip(slice, shape)))


sc = [
    ((2, 3), (1, 1)),
    ((2, 3, 2), (1, 1, 1)),
    ((3, 3), (1, 2)),
    ((3, 3), (2, 2)),
    ((10, 10, 10), (3, 5, 7)),
]

@pytest.mark.parametrize('shape, chunk_shape', sc)
def test_print_chunk_indices(shape, chunk_shape):
    print()
    for index in chunk_corners(shape, chunk_shape):
        print(index)


@pytest.mark.parametrize('shape, chunk_shape', sc)
def test_chunk_indices(shape, chunk_shape):
    corners = list(chunk_corners(shape, chunk_shape))
    # One corner per chunk
    assert len(corners) == num_chunks(shape, chunk_shape)
    # Along each dimension, the corner indices are exactly those specified
    # by the shape of the array and stride from the chunk shape
    for d, (s, c) in enumerate(zip(shape, chunk_shape)):
        assert {index[d] for index in corners} == set(range(0, s, c))


@pytest.mark.parametrize('shape, chunk_shape', sc)
def test_print_chunk_slices(shape, chunk_shape):
    print()
    for chunk_slice in chunk_slices(shape, chunk_shape):
        print(chunk_slice)


@pytest.mark.parametrize('shape, chunk_shape', sc)
def test_chunk_slices(shape, chunk_shape):
    slices = list(chunk_slices(shape, chunk_shape))
    # One slice per chunk
    assert len(slices) == num_chunks(shape, chunk_shape)
    # The union of the sets of indices specified by the slices (set per slice)
    # exhausts all indices in the array.
    assert union(set(indices(slice, shape)) for slice in slices) == \
           set(product(*(range(s) for s in shape)))


@pytest.mark.parametrize('array, chunk_shape', [
    (np.arange(size(shape)).reshape(shape), chunk_shape)
    for shape, chunk_shape in sc
])
def test_print_chunks(array, chunk_shape):
    print()
    for chunk in chunks(array, chunk_shape):
        print(chunk)


@pytest.mark.parametrize('shape, max_chunk_size', [
    ((200, 10, 5), 1),
    ((200, 10, 5), 2),
    ((200, 10, 5), 3),
    ((200, 10, 5), 5),
    ((200, 10, 5), 6),
    ((200, 10, 5), 7),
    ((200, 10, 5), 9),
    ((200, 10, 5), 10),
    ((200, 10, 5), 11),
    ((200, 10, 5), 20),
    ((200, 10, 5), 100),
    ((200, 10, 5), 101),
    ((200, 10, 5), 150),
    ((200, 10, 5), 1000),
    ((200, 10, 5), 1100),
    ((200, 10, 5), 1251),
    ((200, 10, 5), 200*10*5),
    ((200, 10, 5), 200*10*5 + 1),
    ((200, 10, 5), 200*10*5 * 100),
])
def test_opt_chunk_shape(shape, max_chunk_size):
    ocs = opt_chunk_shape(shape, max_chunk_size)
    print("{}; {} -> {}; {}".format(shape, max_chunk_size, ocs, size(ocs)))
    assert len(ocs) == len(shape)
    assert size(ocs) <= max_chunk_size
    assert size(ocs) <= size(shape)
    assert all(c <= s for c, s in zip(ocs, shape))