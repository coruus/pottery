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

from cffi import FFI

_FFI = FFI()
_FFI.cdef("""\
  // ottery.h
  void ottery_rand_bytes(void *buf, size_t n);
  uint32_t ottery_rand_uint32(void);
  uint64_t ottery_rand_uint64(void);
  uint64_t ottery_rand_range64(uint64_t top);
  // ottery-internal.h
  void ottery_memclear_(void *mem, size_t len);
""")
_C = _FFI.dlopen("libottery")


_UINT64_MAX = 2 ** 64 - 1


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
    buf = _FFI.new('char[]', size)
    _C.ottery_rand_bytes(buf, size)
    # The [:] copies the result to a new Python byte-string; this
    # ensures that the C object is garbage-collected when this
    # function returns.
    s = _FFI.buffer(buf)[:]
    # Clean the C buffer.
    _C.ottery_memclear_(buf, size)
    return s


def rand_uint32():
    """Generate a random number of type uint32.

    Returns
    -------
    randint : int
      Python integer between 0 and UINT32_MAX inclusive
    """
    return _C.ottery_rand_uint32()


def rand_uint64():
    """Generate a random number of type uint64.

    Returns
    -------
    randint : int or long
      A random number between 0 and UINT64_MAX inclusive
    """
    return _C.ottery_rand_uint64()


def getrandbits(bitlength):
    """Return a Python long with `k` random bits."""
    num_bytes = (bitlength + 7) // 8
    mask = 2 ** bitlength - 1
    s = rand_bytes(num_bytes)
    return mask & int(hexlify(s), 16)


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
    cdata = _FFI.new('char[]', size)
    _C.ottery_rand_bytes(cdata, size)
    return _FFI.buffer(cdata)


class _RandomBuffer(object):

    """A refreshable, persistent random buffer of a fixed size.

    This is intended for uses which require so many random bytes that
    memory allocation is a significant cost.

    Experimental.
    """

    def __init__(self, size):
        """The size of the random buffer."""
        self.size = size
        self._cdata = _FFI.new('char[]', size)
        _C.ottery_rand_bytes(self._cdata, size)
        self.buffer = _FFI.buffer(self._cdata)
        self.__buffer__ = self.buffer

    def refresh(self):
        """Refresh the random buffer in-place."""
        _C.ottery_rand_bytes(self._cdata, self.size)

    def tostring(self):
        """Return the contents of the buffer as a byte-string."""
        return self.buffer[:]

    def __repr__(self):
        """Return a string representing the _RandomBuffer."""
        return 'RandomBuffer(size={})'.format(self.size)

    def clear(self):
        """Securely clear the buffer."""
        _C.ottery_memclear(_FFI.cast('void *', self.__buffer__),
                           self.size)

__all__ = ('_rand_buffer', 'rand_bytes', 'rand_uint32',
           'rand_uint64', '_RandomBuffer')
