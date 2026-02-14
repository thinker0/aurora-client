# Lightweight kazoo stub to avoid pulling real kazoo dependency in tests.
# Provides minimal classes used by twitter.common.zookeeper.kazoo_client.
import sys
import types


def _install_kazoo_stub():
    if 'kazoo' in sys.modules:
        return

    kazoo = types.ModuleType('kazoo')

    # kazoo.client
    client_mod = types.ModuleType('kazoo.client')

    class KazooClient:
        def __init__(self, *args, **kwargs):
            self.connecting = type('Evt', (), {'set': lambda self: None, 'wait': lambda self: None})()
            self.metrics = type('M', (), {'register': lambda *a, **k: None})()
            self._live = True

        def start_async(self):
            return None

        def start(self):
            return None

        def add_listener(self, *args, **kwargs):
            return None

    client_mod.KazooClient = KazooClient

    # kazoo.protocol.states
    protocol_mod = types.ModuleType('kazoo.protocol')
    states_mod = types.ModuleType('kazoo.protocol.states')

    class _DummyState:
        pass

    states_mod.KazooState = _DummyState
    states_mod.KeeperState = _DummyState
    protocol_mod.states = states_mod

    # kazoo.retry
    retry_mod = types.ModuleType('kazoo.retry')

    class KazooRetry:
        def __init__(self, *args, **kwargs):
            pass

    retry_mod.KazooRetry = KazooRetry

    # kazoo.recipe.barrier
    recipe_mod = types.ModuleType('kazoo.recipe')
    barrier_mod = types.ModuleType('kazoo.recipe.barrier')

    class Barrier:
        def __init__(self, *args, **kwargs):
            pass

        def wait(self, *args, **kwargs):
            return True

    barrier_mod.Barrier = Barrier
    recipe_mod.barrier = barrier_mod

    # Register modules
    kazoo.client = client_mod
    kazoo.protocol = protocol_mod
    kazoo.recipe = recipe_mod

    sys.modules['kazoo'] = kazoo
    sys.modules['kazoo.client'] = client_mod
    sys.modules['kazoo.protocol'] = protocol_mod
    sys.modules['kazoo.protocol.states'] = states_mod
    sys.modules['kazoo.retry'] = retry_mod
    sys.modules['kazoo.recipe'] = recipe_mod
    sys.modules['kazoo.recipe.barrier'] = barrier_mod


_install_kazoo_stub()

