"""
Utilities for chunking arbitrary arrays.

Definition of terms used:

An array is a multidimensional array of shape ``shape`` and dimension
``n`` = ``len(shape)``. Think ``numpy``.

An index is a ``n``-tuple specifying a single element in the
multidimensional array. Indexing on each dimension is zero-based.

A chunk is a contiguous rectangular subset of the array with maximum extent
(length) in each coordinate specified by ``chunk_shape``, but limited by
the bounds of the array. (Chunks near the outside edges of the array are
truncated if a whole number of chunks does not fit on each dimension of
the array).

A corner is the index within a chunk that has the smallest values in
each coordinate component.
"""
from itertools import product


def chunk_corners(shape, chunk_shape, d=0):
    """
    Generator that enumerates the index of the corner of each chunk of
    a specified chunk shape within a specified array shape.

    Currently, there is only one ordering available: the last index varies
    fastest

    :param shape: (tuple) shape of array
    :param chunk_shape: (tuple) shape of (full-size) chunk
    :param d: (int) return coordinates for subset of array defined by
        coordinates indexed ``d``, ``d+1``, ..., ``n-1``.
    :return (generator) that yields indices of chunk corners.
    """
    assert len(shape) == len(chunk_shape)
    return product(*(range(0, s, c) for s, c in zip(shape, chunk_shape)))
    # if d >= len(shape):
    #     yield ()
    # else:
    #     axis = range(0, shape[d], chunk_shape[d])
    #     for index in axis:
    #         for indices in chunk_corners(shape, chunk_shape, d+1):
    #             yield (index,) + indices


def chunk_slices(shape, chunk_shape):
    """
    Generator that enumerates indexing tuples containing slices that pick
    out the chunks of shape ``chunk_shape`` from an array of shape ``shape``.

    :param shape: (tuple) array shape
    :param chunk_shape: (tuple) shape of (full-size) chunk
    :return: (generator) that yields ``n``-tuples of the form
            ``(s[0], s[1], ..., s[n-1])``
        where each ``s[d]`` is a slice object valid for dimension ``d`` of
        the array. Taken together, the slices exhaust all indices of the array.
    """
    for index in chunk_corners(shape, chunk_shape):
        yield tuple(
            slice(i, min(i+c, s))
            for i, s, c in zip(index, shape, chunk_shape)
        )

def chunks(array, chunk_shape):
    """
    Generator that returns all chunks of shape ``chunk_shape`` in
    array ``array``.

    :param array: (numpy.array) array to be chunked
    :param chunk_shape: (tuple) shape of (full-size) chunk
    :return: (generator) that enumerates all chunks in array; a chunk
        is a numpy array
    """
    for chunk_slice in chunk_slices(array.shape, chunk_shape):
        yield array[chunk_slice]
