# Minimal stub to satisfy imports when using the lightweight Kazoo shim.


class Lock:
    def __init__(self, *args, **kwargs):
        pass

    def acquire(self, *args, **kwargs):
        return True

    def release(self):
        return None


class ReadLock(Lock):
    pass


class WriteLock(Lock):
    pass


class Semaphore(Lock):
    pass

