#!/usr/bin/env python3

"""Serpentine binning

An implementation of the so-called 'serpentine binning' procedure described
in Scolari et al.

Usage:
    serpentine.py <matrixA> <matrixB> [--threshold=10] [--min-threshold=1]
                                      [--test] [--test-size]

Options:
    -h, --help                      Display this help message.
    --version                       Display the program's current version.
    -t 10, --threshold 10           Threshold value to trigger binning.
                                    [default: 10]
    -m 1, --min-threshold 1         Minimum value to force trigger binning in
                                    either matrix. [default: 1]
    --test                          Run a demo on randomly generated matrices.
    --test-size 500                 Size of the test matrix for the demo.
                                    [default: 300]
"""

import numpy as _np
import pandas as _pd
import docopt as _doc
import itertools as _it
from matplotlib import pyplot as _plt
from matplotlib import colors as _cols
import warnings as _warns
from random import choice as _choice
import multiprocessing as _mp
from datetime import datetime as _datetime

DEFAULT_MIN_THRESHOLD = 10
DEFAULT_THRESHOLD = 40
DEFAULT_ITERATIONS = 10
DEFAULT_SIZE = 300

VERSION_NUMBER = "0.1a"


def serpentin_iteration(
    A,
    B,
    threshold=DEFAULT_THRESHOLD,
    minthreshold=DEFAULT_MIN_THRESHOLD,
    triangular=False,
    verbose=True,
):

    """Perform a single iteration of binning
    """

    if triangular:
        try:
            assert A.shape == B.shape
            assert len(A.shape) == 2
            assert min(A.shape) == max(A.shape)
        except AssertionError:
            raise ValueError(
                "Matrices must be square and have identical shape"
            )
    else:
        try:
            assert A.shape == B.shape
            assert len(A.shape) == 2
        except AssertionError:
            raise ValueError("Matrices must have identical shape")

    try:
        assert minthreshold < threshold
    except AssertionError:
        raise ValueError("Minimal threshold should be lower than maximal")

    def pixel_neighs_triangular(i, j, size):

        if i > 0:
            if i - 1 >= j:
                yield (i - 1, j)
        if i < size - 1:
            if i + 1 >= j:
                yield (i + 1, j)
        if j > 0:
            if i >= j - 1:
                yield (i, j - 1)
        if j < size - 1:
            if i >= j + 1:
                yield (i, j + 1)

    def pixel_neighs(i, j, w, h):

        if i > 0:
            yield (i - 1, j)
        if i < w - 1:
            yield (i + 1, j)
        if j > 0:
            yield (i, j - 1)
        if j < h - 1:
            yield (i, j + 1)

    size = A.shape
    U = _np.copy(A)
    V = _np.copy(B)
    U = U.reshape((size[0] * size[1]))
    V = V.reshape((size[0] * size[1]))

    if triangular:
        pixels = [
            _np.array([i * size[0] + j], dtype=_np.int32)
            for (i, j) in _it.product(range(size[0]), range(size[0]))
            if i >= j
        ]

        neighs = [
            set(
                int((a * (a + 1) / 2)) + b
                for (a, b) in pixel_neighs_triangular(i, j, size[0])
            )
            for (i, j) in _it.product(range(size[0]), range(size[0]))
            if i >= j
        ]
        start = int(size[0] * (size[0] + 1) / 2)
        tot = start

    else:
        pixels = [
            _np.array([i * size[1] + j], dtype=_np.int32)
            for (i, j) in _it.product(range(size[0]), range(size[1]))
        ]
        neighs = [
            set(
                (a * size[1]) + b
                for (a, b) in pixel_neighs(i, j, size[0], size[1])
            )
            for (i, j) in _it.product(range(size[0]), range(size[1]))
        ]
        start = size[0] * size[1]
        tot = start

    previous_existent = 0
    current_existent = 1

    def print_iteration(i, tot, start, verbose):

        percent = 100 * float(tot) / start
        iteration_string = "{}\t Total serpentines: {} ({} %)".format(
            i, tot, percent
        )
        if verbose:
            print(iteration_string)

    # merger
    i = 0
    while current_existent != previous_existent:
        print_iteration(i, tot, start, verbose)
        i += 1
        tot = 0
        for serp in _np.random.permutation(range(len(pixels))):
            if pixels[serp] is not None:
                tot += 1
                # choose where to expand
                if pixels[serp].size == 1:  # Optimization for performances
                    a = U[(pixels[serp])[0]]
                    b = V[(pixels[serp])[0]]
                else:
                    a = _np.sum(U[pixels[serp]])
                    b = _np.sum(V[pixels[serp]])

                thresh = a < threshold and b < threshold
                minthresh = a < minthreshold or b < minthreshold
                if thresh or minthresh:
                    min_neigh = _choice(tuple(neighs[serp]))

                    # Merge pixels
                    pixels[serp] = _np.concatenate(
                        (pixels[serp], pixels[min_neigh]), axis=0
                    )
                    # Merge neighbours (and remove self)
                    neighs[serp].remove(min_neigh)
                    neighs[min_neigh].remove(serp)
                    neighs[serp].update(neighs[min_neigh])

                    # Update neighbours of merged
                    for nneigh in neighs[min_neigh]:
                        neighs[nneigh].remove(min_neigh)
                        neighs[nneigh].add(serp)

                    # Delete merged serpentin
                    pixels[min_neigh] = None
                    neighs[min_neigh] = None

        previous_existent = current_existent
        current_existent = sum((serp is not None for serp in pixels))

    print_iteration(i, tot, start, verbose)
    if verbose:
        print("{}\t Over: {}".format(i, _datetime.now()))

    pix = (p for p in pixels if p is not None)

    U = U.astype(_np.float32)
    V = V.astype(_np.float32)
    for serp in pix:
        U[serp] = _np.sum(U[serp]) * 1. / len(serp)
        V[serp] = _np.sum(V[serp]) * 1. / len(serp)
    U = U.reshape((size[0], size[1]))
    V = V.reshape((size[0], size[1]))

    if triangular:
        Amod = (
            _np.tril(U)
            + _np.transpose(_np.tril(U))
            - _np.diag(_np.diag(_np.tril(U)))
        )
        Bmod = (
            _np.tril(V)
            + _np.transpose(_np.tril(V))
            - _np.diag(_np.diag(_np.tril(V)))
        )
        trili = _np.tril_indices(_np.int(_np.sqrt(Bmod.size)))
        D = _np.zeros_like(Bmod)
        D[trili] = V[trili] * 1. / U[trili]
        D[trili] = _np.log2(D[trili])

    else:
        Amod = U
        Bmod = V
        D = V * 1. / U
        D = _np.log2(D)

    return (Amod, Bmod, D)


def _serpentin_iteration_mp(value):
    return serpentin_iteration(*value)


def serpentin_binning(
    A,
    B,
    threshold=DEFAULT_THRESHOLD,
    minthreshold=DEFAULT_MIN_THRESHOLD,
    iterations=DEFAULT_ITERATIONS,
    triangular=False,
    verbose=True,
    parallel=16,
):

    """Perform binning
    """

    if triangular:
        try:
            assert A.shape == B.shape
            assert len(A.shape) == 2
            assert min(A.shape) == max(A.shape)
        except AssertionError:
            raise ValueError(
                "Matrices must be square and have identical shape"
            )
    else:
        try:
            assert A.shape == B.shape
            assert len(A.shape) == 2
        except AssertionError:
            raise ValueError("Matrices must have identical shape")

    try:
        assert minthreshold < threshold
    except AssertionError:
        raise ValueError("Minimal threshold should be lower than maximal")

    iterations = int(iterations)

    sK = _np.zeros_like(A)
    sA = _np.zeros_like(A)
    sB = _np.zeros_like(A)

    if parallel > 1:
        print(
            "Starting {} binning processes in batches of {}...".format(
                iterations, parallel
            )
        )
        p = _mp.Pool(parallel)
        iterator = (
            (A, B, threshold, minthreshold, triangular, verbose)
            for x in range(iterations)
        )
        res = p.map(_serpentin_iteration_mp, iterator)

        for r in res:
            At, Bt, Kt = r
            sK = sK + Kt
            sA = sA + At
            sB = sB + Bt

    else:
        print(
            "{} Starting {} binning processes...".format(
                _datetime.now(), iterations
            )
        )
        for _ in range(iterations):
            At, Bt, Kt = serpentin_iteration(
                A,
                B,
                threshold=threshold,
                minthreshold=minthreshold,
                triangular=triangular,
                verbose=verbose,
            )
            sK = sK + Kt
            sA = sA + At
            sB = sB + Bt

    sK = sK * 1. / iterations
    sA = sA * 1. / iterations
    sB = sB * 1. / iterations

    return sA, sB, sK


def _MDplot(ACmean, ACdiff, trans, xlim=None, ylim=None):
    _plt.scatter(ACmean, ACdiff - trans)
    _plt.xlabel("Log2 Mean contact number")
    _plt.ylabel("Log2 ratio")
    if xlim is not None:
        _plt.xlim(xlim[0], xlim[1])
    if ylim is not None:
        _plt.ylim(ylim[0], ylim[1])


def mad(data, axis=None):

    """Median absolute deviation
    """

    return _np.median(_np.absolute(data - _np.median(data, axis)), axis)


def outstanding_filter(X):

    """Generate filtering index that removes outstanding values (three standard
    deviations above or below the mean).
    """

    with _np.errstate(divide="ignore", invalid="ignore"):
        norm = _np.log10(_np.sum(X, axis=0))
        median = _np.median(norm)
        sigma = 1.4826 * mad(norm)

    return (norm < median - 3 * sigma) + (norm > median + 3 * sigma)


def fltmatr(X, flt):

    """Filter a 2D matrix in both dimensions according to an index.
    """

    X = _np.copy(X)
    X = X[flt, :]
    X = X[:, flt]
    return X


def _madplot(
    ACmean, ACdiff, s=10, xlim=None, ylim=None, showthr=True, show=True
):
    df = _pd.DataFrame({"m": ACmean, "d": ACdiff})

    with _warns.catch_warnings():
        _warns.simplefilter("ignore")

        df = df[_np.logical_not(_np.isinf(abs(df["m"])))]
        df = df[_np.logical_not(_np.isinf(abs(df["d"])))]

        df = df.sort_values(by="m", ascending=False)
        x = _np.zeros(s)
        y1 = _np.zeros(s)
        y2 = _np.zeros(s)
        q = (max(df["m"]) - min(df["m"])) / (s)

        k = 0
        for i in _np.arange(min(df["m"]), max(df["m"]), q):
            r = df[(df["m"] > i) * (df["m"] < i + q)]
            x[k] = _np.median(r["m"])
            y1[k] = _np.median(r["d"])
            y2[k] = 1.4826 * mad(r["d"])
            if _np.isnan(y2[k]):
                y2[k] = 0
            k = k + 1

    y1lim = _np.mean(y1[-3:])
    y2lim = _np.mean(y2[-3:])
    y2limv = _np.std(y2[-3:])
    if show:
        _MDplot(ACmean, ACdiff, y1lim, xlim=xlim, ylim=ylim)
        _plt.plot(x, y1 - y1lim, color="y")
        _plt.plot(x, y2, color="r")

    if _np.sum(_np.abs(y2 - y2lim) > y2limv * 2) > 0:
        xa = (x[(_np.abs(y2 - y2lim) > y2limv * 2)])[-1]
    else:
        xa = _np.percentile(ACmean[ACmean > 0], 99)

    if _np.isnan(xa) or _np.isinf(xa) or xa < _np.log2(25.):
        print("Could not set a good threshold, your data is probably awful")
        print("Good that you use serpentine!")
        print("Choosing 25 as a threshold, please finetune it by hand")
        xa = _np.log2(25.)

    if showthr and show:
        _plt.axvline(x=xa)
    return y1lim, 2 ** xa


def MDbefore(XA, XB, s=10, xlim=None, ylim=None, triangular=False, show=True):

    """MD plot before binning
    """

    if triangular:
        with _np.errstate(divide="ignore", invalid="ignore"):
            ACmean = _np.log2(
                (_np.tril(XA).flatten() + _np.tril(XB).flatten()) * 1. / 2
            )
            ACdiff = _np.log2(_np.tril(XB).flatten() / _np.tril(XA).flatten())
    else:
        with _np.errstate(divide="ignore", invalid="ignore"):
            ACmean = _np.log2(XA.flatten() + XB.flatten()) * 1. / 2
            ACdiff = _np.log2(XB.flatten() / XA.flatten())

    return _madplot(ACmean, ACdiff, s, xlim, ylim, show=show)


def MDafter(
    XA, XB, XD, s=10, xlim=None, ylim=None, triangular=False, show=True
):

    """MD plot after binning
    """

    if triangular:
        with _np.errstate(divide="ignore", invalid="ignore"):
            ACmean = _np.log2(
                (_np.tril(XA).flatten() + _np.tril(XB).flatten()) * 1. / 2
            )
            ACdiff = _np.tril(XD).flatten()
    else:
        with _np.errstate(divide="ignore", invalid="ignore"):
            ACmean = _np.log2(XA.flatten() + XB.flatten()) * 1. / 2
            ACdiff = XD.flatten()

    return _madplot(ACmean, ACdiff, s, xlim, ylim, showthr=False, show=show)


def dshow(dif, trend, limit, triangular=False):

    """Show differential matrix
    """

    colors = [(0, 0, .5), (0, 0, 1), (1, 1, 1), (1, 0, 0), (.5, 0, 0)]
    cmap_name = "my_list"
    cm = _cols.LinearSegmentedColormap.from_list(cmap_name, colors, N=64)

    if triangular:
        trili = _np.tril_indices(_np.int(_np.sqrt(dif.size)))
        triui = _np.triu_indices(_np.int(_np.sqrt(dif.size)))
        diagi = _np.diag_indices(_np.int(_np.sqrt(dif.size)))
        plotta = _np.copy(dif)
        plotta[trili] = plotta[trili] - trend
        plottadiag = plotta[diagi]
        plotta[triui] = _np.nan
        plotta[diagi] = plottadiag
    else:
        plotta = _np.copy(dif) - trend

    im = _plt.imshow(
        plotta, vmin=-limit, vmax=limit, cmap=cm, interpolation="none"
    )
    _plt.colorbar(im)


def mshow(XX, subplot=_plt, colorbar=True, triangular=False):

    """Boilerplate around the imshow function to show a matrix.
    """

    del triangular
    colors = [(1, 1, 1), (1, 0, 0), (0, 0, 0)]
    cmap_name = "radios"
    cm2 = _cols.LinearSegmentedColormap.from_list(cmap_name, colors, N=64)

    with _np.errstate(divide="ignore", invalid="ignore"):
        im = subplot.imshow(_np.log10(XX), cmap=cm2, interpolation="none")
        if colorbar:
            _plt.colorbar(im)

    return im


def fromupdiag(filename):

    """Load a DADE matrix into a numpy array
    """

    result = None
    with open(filename) as f:
        header = f.readline().split()
        header.pop(0)
        total = len(header)
        result = _np.zeros((total, total))
        count = 0
        for line in f:
            data = line.split()
            data.pop(0)
            len(data)
            result[count, count:total] = data
            count += 1

    result = result + _np.transpose(result) - _np.diag(_np.diag(result))
    return result


def _plot(U, V, W):

    fig = _plt.figure()

    ax1 = fig.add_subplot(2, 2, 1)
    im1 = ax1.imshow(
        U,
        interpolation="none",
        clim=(0, 27),
        vmax=_np.percentile(U, 99),
        cmap="Reds",
    )
    _plt.colorbar(im1)

    ax2 = fig.add_subplot(2, 2, 2)
    im2 = ax2.imshow(
        V,
        interpolation="none",
        clim=(0, 27),
        vmax=_np.percentile(U, 99),
        cmap="Reds",
    )
    _plt.colorbar(im2)

    ax3 = fig.add_subplot(2, 2, 3)
    im3 = ax3.imshow(W, interpolation="none", cmap="seismic", clim=(-3, 3))
    _plt.colorbar(im3)
    _plt.show()


def _test(
    threshold=DEFAULT_THRESHOLD,
    minthreshold=DEFAULT_MIN_THRESHOLD,
    size=DEFAULT_SIZE,
):

    """Perform binning on a random matrix
    """

    _np.random.seed(15)

    A = _np.random.random((size, size)) * 10

    _np.random.seed(80)

    B = _np.random.random((size, size)) * 10
    A = A + A.T
    B = B + B.T
    U, V, W = serpentin_binning(
        A,
        B,
        threshold=threshold,
        minthreshold=minthreshold,
        parallel=4,
        triangular=True,
    )
    _plot(U, V, W)


def _main():

    arguments = _doc.docopt(__doc__, version=VERSION_NUMBER)

    inputA = arguments["<matrixA>"]
    inputB = arguments["<matrixB>"]
    threshold = int(arguments["--threshold"])
    minthreshold = int(arguments["--min-threshold"])
    size = int(arguments["--test-size"])
    is_test = int(arguments["--test"])

    if is_test:
        _test(threshold=threshold, minthreshold=minthreshold, size=size)

    elif inputA and inputB:
        A = fromupdiag(inputA)
        B = fromupdiag(inputB)
        A = A + A.T - _np.diag(_np.diag(A))
        B = B + B.T - _np.diag(_np.diag(B))
        U, V, W = serpentin_binning(
            A,
            B,
            threshold=threshold,
            minthreshold=minthreshold,
            triangular=True,
        )
        _plot(U, V, W)


if __name__ == "__main__":

    _main()