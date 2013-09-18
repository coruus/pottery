#!/bin/sh
# TODO integrate into a build system!
libtool -dynamic -lsystem -o pottery/libottery.so libottery/src/*.o
