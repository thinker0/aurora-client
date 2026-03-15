import sys
import types

# Lightweight kazoo stub to avoid pulling real kazoo dependency in tests.
# Provides minimal classes used by twitter.common.zookeeper.kazoo_client.


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


def _install_gen_stub():
    if 'gen' in sys.modules:
        return

    import types

    def _make(name):
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod

    gen = _make('gen')
    apache = _make('gen.apache')
    aurora = _make('gen.apache.aurora')
    api = _make('gen.apache.aurora.api')

    constants = _make('gen.apache.aurora.api.constants')
    constants.GOOD_IDENTIFIER_PATTERN_PYTHON = r'^[a-zA-Z][_a-zA-Z0-9]*$'
    constants.AURORA_EXECUTOR_NAME = 'AuroraExecutor'
    constants.ACTIVE_STATES = frozenset()
    constants.LIVE_STATES = frozenset()
    constants.TERMINAL_STATES = frozenset()

    ttypes = _make('gen.apache.aurora.api.ttypes')
    for cls_name in (
        'JobKey', 'TaskQuery', 'ResponseCode', 'ScheduleStatus',
        'Resource', 'JobUpdateSettings', 'Range',
    ):
        setattr(ttypes, cls_name, type(cls_name, (), {}))

    thermos = _make('gen.apache.thermos')
    thermos_ttypes = _make('gen.apache.thermos.ttypes')
    thermos_ttypes.TaskState = type('TaskState', (), {})

    gen.apache = apache
    apache.aurora = aurora
    aurora.api = api
    api.constants = constants
    api.ttypes = ttypes
    apache.thermos = thermos
    thermos.ttypes = thermos_ttypes


_install_gen_stub()
