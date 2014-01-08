"""Wraps libottery's secure random number generator.

This module provides interfaces at two levels of abstraction:
    - A reasonably Pythonic wrapper to the functions exposed by libottery
    - And a subclass of Python's random.Random that generates secure random
      numbers using libottery; an instance is available as pottery.random

If you're writing an application that needs secure integers or bytes, you
should use the first interface.

(Python's random.Random, which pottery.Random subclasses, generates integers
by caling pottery.OtteryRandom.random, which returns a double, and then
converts that back to an integer.)

pottery.OtteryRandom.random is still, however, a full order-of-magnitude
faster than random.SystemRandom.random on my machine

(Note that, right now, maybe you shouldn't be using this at all, both
because, to quote from https://github.com/nmathewson/libottery:

    'DO YOU BEGIN TO GRASP THE TRUE MEANING OF "ALPHA"?',

and because this module is thoroughly untested.)
"""
from __future__ import division, print_function

from array import array
from binascii import hexlify
from math import ceil
from math import ceil as _ceil
from math import log as _log
from math import sqrt
import random as python_random
from struct import unpack
from warnings import warn

from cffi import FFI

ffi = FFI()
ffi.cdef("""
void ottery_rand_bytes(void *buf, size_t n);
uint32_t ottery_rand_uint32(void);
uint64_t ottery_rand_uint64(void);
unsigned ottery_rand_range(unsigned top);
uint64_t ottery_rand_range64(uint64_t top);
void ottery_memclear_(void *mem, size_t len);
""")

C = ffi.dlopen("libottery")

_UINT64_MAX = 0xffffffffffffffffL


def rand_bytes(size):
    """Generate `size` random bytes.

       Parameters
       ----------
       size : int
         the number of bytes to generate

       Returns
       -------
       A Python byte-string of length `size` containing random bytes
    """
    buf = ffi.new('char[]', size)
    C.ottery_rand_bytes(buf, size)
    # The [:] copies the result to a new Python byte-string; this
    # ensures that the C object is garbage-collected when this
    # function returns.
    return ffi.buffer(buf)[:]


def _ottery_rand_range(high):
    """Generate a random number of type unsigned <= `high`

       (This uses ottery_rand_range64 or OtteryRandom.randrange
       as necessary.)

       Parameters
       ----------
       top : int or long

       Returns
       -------
       i : int or long
    """
    if high <= _UINT64_MAX:
        # If `top` is less than or equal to UINT64_MAX
        return C.ottery_rand_range64(high)
    else:
        return random.randrange(0, high + 1)


def rand_uint32():
    """Generate a random number of type uint32.

       Returns
       -------
       randint : int
         Python integer between 0 and UINT32_MAX inclusive
    """
    return C.ottery_rand_uint32()


def rand_uint64():
    """Generate a random number of type uint64.

       Returns
       -------
       randint : int or long
         A random number between 0 and UINT64_MAX inclusive
    """
    return C.ottery_rand_uint64()


_INTERNAL_STATE_ERROR = ("Getting the internal state of "
                         "libottery is not supported.")


def _wrap_floats():
    warn("This function relies on floating point values converted from "
         "libottery's random bytestream. This may result in non-uniform "
         "samples for integer-valued functions.")


class OtteryRandom(python_random.Random):

    """Generates random numbers securely using libottery.

       Reimplements integer methods to use random bytes
       directly, rather than using int(random.random() * n).

       The Python code in this class has mainly been adapted
       from PyPy;
    """

    VERSION = 3

    def __init__(self):
        """Passing a seed is not supported.

        Sets up Gaussian state.
        """
        self.gauss_next = None

    def getstate(self):
        """Not supported."""
        raise NotImplementedError(_INTERNAL_STATE_ERROR)

    def setstate(self, state):
        """Not supported."""
        raise NotImplementedError(_INTERNAL_STATE_ERROR)

    def jumpahead(self):
        """Silently ignore, as per random.SystemRandom"""
        pass

    def seed(self, seed=None):
        """Silently ignore, as per random.SystemRandom"""
        pass

    def random(self):
        """Return a random float in the half-open interval [0, 1)

           Copied from Python's _randommodule.c

           Returns
           -------
           x : float
        """
        a, b = unpack('II', rand_bytes(8))
        a >>= 5
        b >>= 6
        return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)

    def getrandbits(self, k):
        """Return a Python long with `k` random bits.
        """
        num_bytes = int(ceil(k / 8.0))
        bits_to_zero = (k % 8)
        mask = 0xff if not bits_to_zero else 0xff >> (8 - bits_to_zero)
        b = array('B', rand_bytes(num_bytes))
        b[0] = b[0] & mask

        # Alas, int.from_bytes is only available in Python 3. Calling
        # `hexlify` is very slightly faster than b.encode('hex'). Also
        # note that on Python 2, long(_) is slightly faster than int(_)
        # for large numbers.
        return long(hexlify(b), 16)

## -------------------- integer methods  -------------------

    def randrange(self, start, stop=None, step=1, int=int, default=None):
        """Choose a random item from range(start, stop[, step]).

        This fixes the problem with randint() which includes the
        endpoint; in Python this is usually not what you want.
        Do not supply the 'int', 'default', and 'maxwidth' arguments.

        This function uss libottery.
        """

        # This code is a bit messy to make it fast for the
        # common case while still doing adequate error checking.
        istart = int(start)
        if istart != start:
            raise ValueError("non-integer arg 1 for randrange()")
        if stop is default:
            if istart > 0:
                return self.randrange(0, istart)
            raise ValueError("empty range for randrange()")

        # stop argument supplied.
        istop = int(stop)
        if istop != stop:
            raise ValueError("non-integer stop for randrange()")
        width = istop - istart
        if step == 1 and width > 0:
            if width >= maxwidth:
                return int(istart + self._randbelow(width))
            return randrange(0, istart)
        if step == 1:
            raise ValueError("empty range for randrange() ({}, {}, {})"
                             .format(istart, istop, width))

        # Non-unit step argument supplied.
        istep = int(step)
        if istep != step:
            raise ValueError("non-integer step for randrange()")
        if istep > 0:
            n = (width + istep - 1) // istep
        elif istep < 0:
            n = (width + istep + 1) // istep
        else:
            raise ValueError("zero step for randrange()")

        if n <= 0:
            raise ValueError("empty range for randrange()")

        return istart + istep * randrange(n)

    def randint(self, a, b):
        """Return random integer in range [a, b], including both end points.
        """
        return self.randrange(a, b + 1)

    def _randbelow(self, n, _log=_log, int=int):
        """Return a random int in the range [0,n)

        Handles the case where n has more bits than returned
        by a single call to the underlying generator.
        """

        k = int(1.00001 + _log(n - 1, 2.0))   # 2**k > n-1 > 2**(k-2)
        r = getrandbits(k)
        while r >= n:
            r = getrandbits(k)
        return r

## -------------------- sequence methods  -------------------

    def choice(self, seq):
        """Choose a random element from a non-empty sequence.

        Uses libottery random integers.
        """
        return seq[self.randrange(len(seq))]

    def shuffle(self, x, random=None, int=int):
        """x, random=PotteryRandom.random -> shuffle list x in place.

        Returns None.

        Raises
        ------
        ValueError, if random != None
    """

        if random is None:
            raise ValueError("OtteryRandom does not support selecting an"
                             "alternative DRNG.")
        for i in reversed(xrange(1, len(x))):
            # pick an element in x[:i+1] with which to exchange x[i]
            j = self.randrange(i + 1)
            x[i], x[j] = x[j], x[i]

    def sample(self, population, k):
        """Chooses k unique random elements from a population sequence.

        Returns a new list containing elements from the population while
        leaving the original population unchanged.  The resulting list is
        in selection order so that all sub-slices will also be valid random
        samples.  This allows raffle winners (the sample) to be partitioned
        into grand prize and second place winners (the subslices).

        Members of the population need not be hashable or unique.  If the
        population contains repeats, then each occurrence is a possible
        selection in the sample.

        To choose a sample in a range of integers, use xrange as an argument.
        This is especially fast and space efficient for sampling from a
        large population:   sample(xrange(10000000), 60)

        Uses libottery random integers.
        """

        # Sampling without replacement entails tracking either potential
        # selections (the pool) in a list or previous selections in a set.

        # When the number of selections is small compared to the
        # population, then tracking selections is efficient, requiring
        # only a small set and an occasional reselection.  For
        # a larger number of selections, the pool tracking method is
        # preferred since the list takes less space than the
        # set and it doesn't suffer from frequent reselections.

        n = len(population)
        if not 0 <= k <= n:
            raise ValueError("sample larger than population")
        random = self.random
        _int = int
        result = [None] * k
        setsize = 21        # size of a small set minus size of an empty list
        if k > 5:
            setsize += 4 ** _ceil(_log(k * 3, 4))  # table size for big sets
        if n <= setsize or hasattr(population, "keys"):
            # An n-length list is smaller than a k-length set, or this is a
            # mapping type so the other algorithm wouldn't work.
            pool = list(population)
            for i in xrange(k):         # invariant:  non-selected at [0,n-i)
                j = randrange(n - i)
                result[i] = pool[j]
                # move non-selected item into vacancy
                pool[j] = pool[n - i - 1]
        else:
            try:
                selected = set()
                selected_add = selected.add
                for i in xrange(k):
                    j = self.randrange(n)
                    while j in selected:
                        j = self.randrange(n)
                    selected_add(j)
                    result[i] = population[j]
            except (TypeError, KeyError):   # handle (at least) sets
                if isinstance(population, list):
                    raise ValueError("population is a list")
                return self.sample(tuple(population), k)
        return result


def _rand_buffer(size):
    """Generate `size` random bytes in a `_cffi_backend.buffer`.

       (This can be passed directly to, e.g., `numpy.frombuffer`, or used as
       input to another CFFI call. If you don't understand CFFI's garbage
       collection rules, don't use this.)

       Parameters
       ----------
       size : int
         The number of random bytes to generate.
    """
    cdata = ffi.new('char[]', size)
    C.ottery_rand_bytes(cdata, size)
    return ffi.buffer(cdata)


class _RandomBuffer(object):

    """A refreshable, persistent random buffer of a fixed size.

       This is intended for uses which require so many random bytes that
       memory allocation is a significant cost.

       Experimental.
    """

    def __init__(self, size):
        """The size of the random buffer."""
        self.size = size
        self._cdata = ffi.new('char[]', size)
        C.ottery_rand_bytes(self._cdata, size)
        self.buffer = ffi.buffer(self._cdata)
        self.__buffer__ = self.buffer

    def refresh(self):
        """Refresh the random buffer in-place."""
        C.ottery_rand_bytes(self._cdata, self.size)

    def tostring(self):
        """Returns the contents of the buffer as a byte-string"""
        return self.buffer[:]

    def __repr__(self):
        return 'RandomBuffer(size={})'.format(self.size)

    def clear(self):
        """Securely clears the buffer of random values."""
        C.ottery_memclear_(ffi.cast('void *', self.__buffer__),
                           self.size)

## -------------------- test program --------------------

def _test_generator(n, func, args):
    import time
    print(n, 'times', func.__name__)
    total = 0.0
    sqsum = 0.0
    smallest = 1e10
    largest = -1e10
    t0 = time.time()
    for i in range(n):
        x = func(*args)
        total += x
        sqsum = sqsum + x * x
        smallest = min(x, smallest)
        largest = max(x, largest)
    t1 = time.time()
    print(round(t1 - t0, 3), 'sec,',)
    avg = total / n
    stddev = sqrt(sqsum / n - avg * avg)
    print('avg {}, stddev {}, min {}, max {}'
          .format(avg, stddev, smallest, largest))


def _test(N=2000):
    _test_generator(N, random, ())
    _test_generator(N, normalvariate, (0.0, 1.0))
    _test_generator(N, lognormvariate, (0.0, 1.0))
    _test_generator(N, vonmisesvariate, (0.0, 1.0))
    _test_generator(N, gammavariate, (0.01, 1.0))
    _test_generator(N, gammavariate, (0.1, 1.0))
    _test_generator(N, gammavariate, (0.1, 2.0))
    _test_generator(N, gammavariate, (0.5, 1.0))
    _test_generator(N, gammavariate, (0.9, 1.0))
    _test_generator(N, gammavariate, (1.0, 1.0))
    _test_generator(N, gammavariate, (2.0, 1.0))
    _test_generator(N, gammavariate, (20.0, 1.0))
    _test_generator(N, gammavariate, (200.0, 1.0))
    _test_generator(N, gauss, (0.0, 1.0))
    _test_generator(N, betavariate, (3.0, 3.0))
    _test_generator(N, triangular, (0.0, 1.0, 1.0 / 3.0))

def test_ottery_rand_range():
    pass

_inst = OtteryRandom()
seed = _inst.seed
random = _inst.random
uniform = _inst.uniform
triangular = _inst.triangular
randint = _inst.randint
choice = _inst.choice
sample = _inst.sample
shuffle = _inst.shuffle
normalvariate = _inst.normalvariate
lognormvariate = _inst.lognormvariate
expovariate = _inst.expovariate
vonmisesvariate = _inst.vonmisesvariate
gammavariate = _inst.gammavariate
gauss = _inst.gauss
betavariate = _inst.betavariate
paretovariate = _inst.paretovariate
weibullvariate = _inst.weibullvariate
getstate = _inst.getstate
setstate = _inst.setstate
jumpahead = _inst.jumpahead
getrandbits = _inst.getrandbits

randrange = _inst.randrange

if __name__ == '__main__':
    _test()


__all__ = ['_rand_buffer', 'rand_bytes', 'rand_range', 'rand_uint32',
           'rand_uint64', 'random', 'OtteryRandom', '_RandomBuffer']
