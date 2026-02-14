# Minimal stub to satisfy imports when using the lightweight Kazoo shim.


class Counter:
    def __init__(self, *args, **kwargs):
        pass

    def value(self):
        return 0

    def __int__(self):
        return int(self.value())

