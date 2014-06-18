"""An implementation of random.Random using libottery.

This file is just a stub that creates an instance of OtteryRandom and puts
the expected functions into the namespace."""
from __future__ import division, print_function

from pottery._random import OtteryRandom

_OTTERY_INSTANCE = OtteryRandom()

seed = _OTTERY_INSTANCE.seed
random = _OTTERY_INSTANCE.random
uniform = _OTTERY_INSTANCE.uniform
triangular = _OTTERY_INSTANCE.triangular
randint = _OTTERY_INSTANCE.randint
choice = _OTTERY_INSTANCE.choice
sample = _OTTERY_INSTANCE.sample
shuffle = _OTTERY_INSTANCE.shuffle
normalvariate = _OTTERY_INSTANCE.normalvariate
lognormvariate = _OTTERY_INSTANCE.lognormvariate
expovariate = _OTTERY_INSTANCE.expovariate
vonmisesvariate = _OTTERY_INSTANCE.vonmisesvariate
gammavariate = _OTTERY_INSTANCE.gammavariate
gauss = _OTTERY_INSTANCE.gauss
betavariate = _OTTERY_INSTANCE.betavariate
paretovariate = _OTTERY_INSTANCE.paretovariate
weibullvariate = _OTTERY_INSTANCE.weibullvariate
getstate = _OTTERY_INSTANCE.getstate
setstate = _OTTERY_INSTANCE.setstate
jumpahead = _OTTERY_INSTANCE.jumpahead
getrandbits = _OTTERY_INSTANCE.getrandbits

randrange = _OTTERY_INSTANCE.randrange

__all__ = ('random', 'OtteryRandom', 'seed', 'random', 'uniform', 'triangular',
           'randint', 'choice', 'sample', 'shuffle', 'normalvariate',
           'lognormvariate', 'expovariate', 'vonmisesvariate', 'gammavariate',
           'gauss', 'betavariate', 'paretovariate', 'weibullvariate', 'getstate',
           'setstate', 'jumpahead', 'getrandbits', 'randrange')
