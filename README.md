Wraps [libottery][libottery]'s secure random number generator.

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
because, to quote from https://github.com/nmathewson/libottery :

    'DO YOU BEGIN TO GRASP THE TRUE MEANING OF "ALPHA"?',

and because this module is thoroughly untested.)

[libottery]: https://github.com/nmathewson/libottery
