# Minimal stub to satisfy imports when using the lightweight Kazoo shim.
# The real Kazoo recipe provides synchronization primitives; tests here only
# need the module to exist.

class Barrier:
    def __init__(self, *args, **kwargs):
        pass

    def wait(self, *args, **kwargs):
        return True


class DoubleBarrier:
    def __init__(self, *args, **kwargs):
        pass

    def enter(self, *args, **kwargs):
        return True

    def leave(self, *args, **kwargs):
        return True
