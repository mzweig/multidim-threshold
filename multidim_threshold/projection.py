from operator import itemgetter as ig
from collections import namedtuple

import funcy as fn
import numpy as np
from lenses import lens
import random

import multidim_threshold as mdt

ProjVec = namedtuple('ProjVec', 'root direc')
t_proj = lambda lo, hi, i : lo[i] + (hi[i] - lo[i])*random.uniform(0,1)


def clip_rec(pi, hi):
    root, direc = mdt.map_array(pi)
    v = ((np.array(hi) - root) / direc).min()
    return root + v * direc


def learn_search(oracle, bot):
    kind = oracle(bot)
    search = mdt.binsearch if isinstance(kind, bool) else mdt.weightedbinsearch
    return fn.compose(ig(1), fn.partial(search, oracle=oracle))


def projections(hi, proj, *, searches):
    rec = mdt.to_rec(lo=proj.root, hi=clip_rec(proj, hi))
    return [search(rec) for search in searches]


def generate_boundary_approxes(lo, hi, member_oracles, **kwargs):
    boundaries = [set() for _ in member_oracles]
    for points in generate_projections(lo, hi, member_oracles, **kwargs):
        for b, p in zip(boundaries, points):
            b.add(tuple(p))
        yield boundaries


def generate_projections(lo, hi, member_oracles, *, direc=None, searches=None, random=None):
    axes_hi = generate_axes_intersects(lo, hi, member_oracles)
    if random is None:
        proj_vecs = generate_proj_vecs(lo, axes_hi, direc)
    else:
        proj_vecs = generate_t_proj_vecs(lo, axes_hi, direc)

    if searches is None:
        searches = [learn_search(f, lo) for f in member_oracles]

    for vec in proj_vecs:
        yield projections(hi, vec, searches=searches)


def generate_proj_vecs(lo, hi, direc=None):
    lo, hi = mdt.map_array((lo, hi))
    if direc is None:
        direc = hi - lo

    vecs = [ProjVec(lo, direc)]
    while True:
        yield from vecs
        vecs = [ProjVec(r, direc) for r in next_roots(lo, hi, vecs)]

def generate_axes_intersects(lo, hi, member_oracles, *, searches=None):
    lo, hi = mdt.map_array((lo, hi))
    direc = mdt.basis_vecs(len(lo))
    mids = np.array([fn.nth(0, generate_projections(lo, hi, member_oracles, direc=dir)) for dir in direc])
    return [axes_mid[:,i].min() for i, axes_mid in enumerate(mids)]

def generate_t_proj_vecs(lo, hi, direc=None):
    lo, hi = mdt.map_array((lo, hi))
    if direc is None:
        direc = hi - lo

    vecs = [ProjVec(lo, direc)]
    while True:
        yield from vecs
        vecs = [ProjVec(random_root(lo, hi), direc)]

def project_along_axes(lo, mid):
    return [lens(lo)[i].set(mid[i]) for i in range(len(lo))]


def midpoint(lo, hi, proj_vec):
    hi = clip_rec(proj_vec, hi)
    return (np.array(lo) + np.array(hi)) / 2

def random_root(lo, hi):
    dim = len(lo)
    root_axis = random.randint(0, dim-1)
    return [0 if i == root_axis else t_proj(lo, hi, i) for i in range(dim)]


def next_roots(lo, hi, prev_vecs):
    mids = [midpoint(v.root, hi, v) for v in prev_vecs]
    return fn.cat(project_along_axes(lo, mid) for mid in mids)
