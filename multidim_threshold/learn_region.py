"""Implements muli-dimensional threshold discovery via binary search."""
from collections import namedtuple
from itertools import combinations
from heapq import heappush as hpush, heappop as hpop

import numpy as np
from numpy import array
import funcy as fn

from multidim_threshold.utils import Result, Rec, to_rec, volume, basis_vecs
from multidim_threshold.search import binsearch, weightedbinsearch
from multidim_threshold.projection import find_boundaries


def to_tuple(r: Rec):
    return tuple(map(tuple, r))


def forward_cone(p: array, r: Rec) -> Rec:
    """Computes the forward cone from point p."""
    return Rec(p, r.top)


def backward_cone(p: array, r: Rec) -> Rec:
    """Computes the backward cone from point p."""
    return Rec(r.bot, p)


def generate_incomparables(mid, r):
    """Generate all incomparable hyper-boxes."""
    forward, backward = forward_cone(mid, r), backward_cone(mid, r)
    bases = (backward.bot, forward.bot)
    diags = (backward.top - backward.bot, forward.top - forward.bot)
    dim = len(bases[0])
    basis = basis_vecs(dim)
    for i in range(1, dim):
        for es in combinations(basis, i):
            vs = tuple(sum((diag @e) * e for e in es) for diag in diags)
            yield Rec(*[base + v for base, v in zip(bases, vs)])


def subdivide(low, mid, high, r: Rec) -> [Rec]:
    """Computes the set of incomparable cones of point p."""
    incomparables = list(generate_incomparables(mid, r))
    return backward_cone(low, r), forward_cone(high, r), incomparables


def multidim_search(lo, hi, is_member, diagsearch=None):
    """Generator for iteratively approximating the oracle's threshold."""
    rec = to_rec(lo, hi)

    if diagsearch is None:
        bool_oracle = isinstance(is_member(rec.bot), bool)
        diagsearch = binsearch if bool_oracle else weightedbinsearch
        diagsearch = fn.partial(diagsearch, oracle=is_member)

    rec = find_boundaries(rec, diagsearch)

    initial_vol = unknown_vol = volume(rec)
    queue, mids = [(unknown_vol, rec)], set()
    while queue:
        _, rec = hpop(queue)
        rec = Rec(*map(np.array, rec))
        low, mid, high = diagsearch(rec)
        if mid is None:
            mid = low
        backward, forward, incomparables = subdivide(low, mid, high, rec)
        mids.add(tuple(list(mid)))

        for r in incomparables:
            hpush(queue, (-volume(r), to_tuple(r)))

        yield Result(mids, queue)
