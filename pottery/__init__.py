"""pottery: a cffi interface to ottery."""
# pylint: disable=W0611
from pottery.ottery import rand_bytes, rand_uint32, rand_uint64, getrandbits, \
    _rand_buffer, _RandomBuffer, _randrange64, randrange
