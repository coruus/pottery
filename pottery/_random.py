"""An implementation of random.Random using libottery."""
# pylint: disable=abstract-class-not-used,too-many-public-methods,no-self-use
from __future__ import division, print_function

from array import array
from binascii import hexlify
from math import ceil as _ceil
from math import log as _log
import random as python_random
from struct import unpack

from pottery.ottery import getrandbits, rand_bytes

_INTERNAL_STATE_ERROR = ("Getting the internal state of libottery "
                         "is not supported.")


class OtteryRandom(python_random.Random):

    """Generates random numbers securely using libottery.

    Reimplements integer methods to use random bytes directly, rather than using
    int(random.random() * n), which involves a conversion to binary64.

    The Python code in this class has mainly been adapted from PyPy.
    """

    VERSION = 3

    def __init__(self):
        """Passing a seed is not supported.

        Just sets up Gaussian state.
        """
        # pylint: disable=super-init-not-called
        self.gauss_next = None

    def getstate(self):
        """Not supported."""
        raise NotImplementedError(_INTERNAL_STATE_ERROR)

    def setstate(self, state):
        """Not supported."""
        raise NotImplementedError(_INTERNAL_STATE_ERROR)

    def jumpahead(self):
        """Silently ignore, as per random.SystemRandom."""
        pass

    def seed(self, seed=None):
        """Silently ignore, as per random.SystemRandom."""
        pass

    def random(self):
        """Return a random float in the half-open interval [0, 1).

        Copied from Python's _randommodule.c.

        Returns
        -------
        x : float
        """
        high, low = unpack('II', rand_bytes(8))
        high >>= 5
        low >>= 6
        return (high * 67108864.0 + low) * (1.0 / 9007199254740992.0)

    def getrandbits(self, bitlength):
        """Return a Python long with `bitlength` random bits."""
        num_bytes = int(_ceil(bitlength / 8.0))
        bits_to_zero = (bitlength % 8)
        mask = 0xff if not bits_to_zero else 0xff >> (8 - bits_to_zero)
        s = array('B', rand_bytes(num_bytes))
        s[0] = s[0] & mask

        # Alas, int.from_bytes is only available in Python 3. Calling
        # `hexlify` is very slightly faster than b.encode('hex'). Also
        # note that on Python 2, long(_) is slightly faster than int(_)
        # for large numbers.
        return long(hexlify(s), 16)

    # -------------------- integer methods  -------------------

    def randrange(self, start, stop=None, step=1, _=None, default=None):
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
                return self._randbelow(istart)
            raise ValueError("empty range for randrange()")

        # stop argument supplied.
        istop = int(stop)
        if istop != stop:
            raise ValueError("non-integer stop for randrange()")
        width = istop - istart
        if step == 1 and width > 0:
            return self._randbelow(istart)
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

        return istart + istep * self._randbelow(n)

    def randint(self, low, high):
        """Return random integer in range [a, b], including both end points."""
        return self.randrange(low, high + 1)

    def _randbelow(self, n, _flog=_log, iint=int):
        """Return a random int in the range [0,n).

        Handles the case where `n` has more bits than returned
        by a single call to the underlying generator.
        """
        bits = iint(1.00001 + _flog(n - 1, 2.0))  # 2**k > n-1 > 2**(k-2)
        x = getrandbits(bits)
        while x >= n:
            x = getrandbits(bits)
        return x

    # -------------------- sequence methods  -------------------

    def choice(self, seq):
        """Choose a random element from a non-empty sequence.

        Uses libottery random integers.
        """
        return seq[self.randrange(len(seq))]

    def shuffle(self, x, random=None, _=None):
        """x, random=PotteryRandom.random -> shuffle list x in place.

        Returns None.

        Raises
        ------
        ValueError if random != None
        """
        if random is None:
            raise ValueError("OtteryRandom does not support selecting an"
                             "alternative DRNG.")
        for i in reversed(xrange(1, len(x))):
            # pick an element in x[:i+1] with which to exchange x[i]
            j = self.randrange(i + 1)
            x[i], x[j] = x[j], x[i]

    def sample(self, population, k):
        """Choose `k` unique random elements from a population sequence.

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
        result = [None] * k
        setsize = 21        # size of a small set minus size of an empty list
        if k > 5:
            setsize += 4 ** _ceil(_log(k * 3, 4))  # table size for big sets
        if n <= setsize or hasattr(population, "keys"):
            # An n-length list is smaller than a k-length set, or this is a
            # mapping type so the other algorithm wouldn't work.
            pool = list(population)
            for i in xrange(k):         # invariant:  non-selected at [0,n-i)
                j = self._randbelow(n - i)
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
