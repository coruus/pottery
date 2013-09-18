# Python wrapper for libottery

Wraps [libottery][libottery]'s secure random number generator using [CFFI][cffi].

## Interface

This module provides interfaces at two levels of abstraction:
- A reasonably Pythonic wrapper to the core functions exposed by libottery
  (rand_bytes, rand_range, rand_uint32, rand_uint64)
- A drop-in replacement for Python's random module (via a subclass of Python's
  random.Random that generates secure random numbers using libottery); an instance
  is available as pottery.random

## Performance

If you're writing an application that needs secure integers or bytes, you
should use the first interface.

(Python's random.Random, which pottery.Random subclasses, generates integers
by caling pottery.OtteryRandom.random, which returns a double, and then
converts that back to an integer.)

pottery.OtteryRandom.random is still, however, a full order-of-magnitude
faster than random.SystemRandom.random for generating random doubles. And it's
only about twice as slow as Mersenne Twister.

(Timings based on poor-quality micro-benchmarks on my Core i7 MBP.)

## Nota bene

Right now, maybe you shouldn't be using this at all, both because, to
quote [Nick Mathewson][libottery]:

    'DO YOU BEGIN TO GRASP THE TRUE MEANING OF "ALPHA"?',

and because this module is thoroughly untested.

[cffi]: https://pypi.python.org/pypi/cffi
[libottery]: https://github.com/nmathewson/libottery
