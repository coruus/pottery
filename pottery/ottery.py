"""Wraps libottery's secure random number generator.

This module provides interfaces at two levels of abstraction:
    - A reasonably Pythonic wrapper to the functions exposed by libottery
    - And a subclass of Python's random.Random that generates secure random
      numbers using libottery; an instance is available as pottery.random

If you're writing an application that needs secure integers or bytes, you
should use the first interface.

pottery.OtteryRandom.random is still, however, a full order-of-magnitude
faster than random.SystemRandom.random on my machine.

(Note that, right now, maybe you shouldn't be using this at all, both
because, to quote from https://github.com/nmathewson/libottery:

    'DO YOU BEGIN TO GRASP THE TRUE MEANING OF "ALPHA"?',

and because this module is thoroughly untested.)
"""
from __future__ import division, print_function

from binascii import hexlify
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


def getrandbits(k):
    """Return a Python long with `k` random bits.
    """
    num_bytes = (k + 7) // 8
#    num_bytes += 1 if k % 8 else 0
    mask = 2 ** k - 1
    b = rand_bytes(num_bytes)
    return mask & long(hexlify(b), 16)


def testrandbits(repeats=2**20):
    for k in range(1, 512):
        vals = [getrandbits(k) for c in range(repeats)]
        print('k = {} : max={:#0x} min={:#0x}'
              .format(k, max(vals), min(vals)))

_INTERNAL_STATE_ERROR = ("Getting the internal state of "
                         "libottery is not supported.")


def _wrap_floats():
    warn("This function relies on floating point values converted from "
         "libottery's random bytestream. This may result in non-uniform "
         "samples for integer-valued functions.")


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

__all__ = ['_rand_buffer', 'rand_bytes', 'rand_uint32',
           'rand_uint64', '_RandomBuffer']
