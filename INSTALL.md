As you may have observed, this module does not have a build system at
present. It expects a shared library named 'libottery.so' to be present
in the 'pottery' directory.

A build script sufficient to link such a library on OSX is provided
for testing purposes. It assumes that libottery (or a symlink to it) is
a subdirectory of this directory.
