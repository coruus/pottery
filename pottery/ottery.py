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
from os.path import dirname, join
from math import ceil
import random as python_random
from struct import unpack

from cffi import FFI

ffi = FFI()
ffi.cdef("""
void ottery_rand_bytes(void *buf, size_t n);
uint32_t ottery_rand_uint32(void);
uint64_t ottery_rand_uint64(void);
unsigned ottery_rand_range(unsigned top);
uint64_t ottery_rand_range64(uint64_t top);
""")

C = ffi.dlopen(join(dirname(__file__), "libottery.so"))


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


def rand_range(high):
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
    if high <= 18446744073709551615L:
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


class OtteryRandom(python_random.Random):

    """Generates random numbers securely using libottery"""

    def __init__(self):
        """No-op. Passing a seed is not supported.
        """
        pass

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

           (Used by the superclass to implement randrange for
           arbitrary Python floats.)
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


random = OtteryRandom()

__all__ = ['_rand_buffer', 'rand_bytes', 'rand_range', 'rand_uint32',
           'rand_uint64', 'random', 'OtteryRandom', '_RandomBuffer']
