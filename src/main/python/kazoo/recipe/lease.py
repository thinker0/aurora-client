# Minimal stub to satisfy imports when using the lightweight Kazoo shim.


class NonBlockingLease:
    def __init__(self, *args, **kwargs):
        pass

    def acquire(self, *args, **kwargs):
        return True

    def release(self):
        return None


class MultiNonBlockingLease(NonBlockingLease):
    pass

