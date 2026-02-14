# Minimal stub to satisfy imports when using the lightweight Kazoo shim.


class Queue:
    def __init__(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        return None


class LockingQueue(Queue):
    pass

