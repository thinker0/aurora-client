# Minimal stub to satisfy imports when using the lightweight Kazoo shim.


class Party:
    def __init__(self, *args, **kwargs):
        pass

    def join(self, *args, **kwargs):
        return None

    def leave(self):
        return None


class ShallowParty(Party):
    pass

