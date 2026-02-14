import cgi
import collections
import collections.abc
import html
import inspect
import os
import sys
import types

if not hasattr(cgi, 'escape'):
  cgi.escape = html.escape

# Restore inspect.getargspec for libraries that still use it.
if not hasattr(inspect, 'getargspec'):
  from collections import namedtuple
  ArgSpec = namedtuple('ArgSpec', 'args varargs keywords defaults')
  def _getargspec(func):
    spec = inspect.getfullargspec(func)
    return ArgSpec(spec.args, spec.varargs, spec.varkw, spec.defaults)
  inspect.getargspec = _getargspec

# Provide collections.Mutable* aliases for Python 3.11+ compatibility.
for name in ('MutableSet', 'MutableMapping', 'MutableSequence', 'Mapping', 'Sequence', 'Iterable', 'Callable'):
  if not hasattr(collections, name) and hasattr(collections.abc, name):
    setattr(collections, name, getattr(collections.abc, name))

# Provide minimal kazoo stubs early to avoid pulling real kazoo wheels in test runs.
if 'kazoo' not in sys.modules:
  kazoo = types.ModuleType('kazoo')
  client_mod = types.ModuleType('kazoo.client')

  class KazooClient(object):
    def __init__(self, *args, **kwargs):
      self.connecting = type('Evt', (), {'set': lambda self: None, 'wait': lambda self: None})()
      self.metrics = type('M', (), {'register': lambda *a, **k: None})()
      self._live = True
    def start_async(self): pass
    def start(self): pass
    def add_listener(self, *a, **k): pass
    def _session_callback(self, state): return None

  client_mod.KazooClient = KazooClient

  protocol_mod = types.ModuleType('kazoo.protocol')
  states_mod = types.ModuleType('kazoo.protocol.states')
  class _DummyState: pass
  states_mod.KazooState = _DummyState
  states_mod.KeeperState = _DummyState
  protocol_mod.states = states_mod

  retry_mod = types.ModuleType('kazoo.retry')
  class KazooRetry(object):
    def __init__(self, *args, **kwargs): pass
  retry_mod.KazooRetry = KazooRetry

  recipe_mod = types.ModuleType('kazoo.recipe')
  barrier_mod = types.ModuleType('kazoo.recipe.barrier')
  class Barrier(object):
    def __init__(self, *args, **kwargs): pass
    def wait(self, *args, **kwargs): return True
  barrier_mod.Barrier = Barrier

  sys.modules['kazoo'] = kazoo
  sys.modules['kazoo.client'] = client_mod
  sys.modules['kazoo.protocol'] = protocol_mod
  sys.modules['kazoo.protocol.states'] = states_mod
  sys.modules['kazoo.retry'] = retry_mod
  sys.modules['kazoo.recipe'] = recipe_mod
  sys.modules['kazoo.recipe.barrier'] = barrier_mod
  kazoo.client = client_mod
  kazoo.protocol = protocol_mod
  kazoo.recipe = recipe_mod

# Provide a kazoo.recipe.partitioner stub to avoid Python 3.7+ "async" syntax errors in old kazoo.
if 'kazoo.recipe.partitioner' not in sys.modules:
  recipe_mod = sys.modules.get('kazoo.recipe')
  if recipe_mod is None:
    recipe_mod = types.ModuleType('kazoo.recipe')
    sys.modules['kazoo.recipe'] = recipe_mod

  partitioner_mod = types.ModuleType('kazoo.recipe.partitioner')
  class SetPartitioner(object):
    def __init__(self, *args, **kwargs):
      raise NotImplementedError('SetPartitioner is not supported in this shim.')
  partitioner_mod.SetPartitioner = SetPartitioner
  sys.modules['kazoo.recipe.partitioner'] = partitioner_mod
  setattr(recipe_mod, 'partitioner', partitioner_mod)

try:
  from gen.apache.aurora.api import ttypes as aurora_ttypes
  if hasattr(aurora_ttypes, 'HostStatus'):
    host_status = aurora_ttypes.HostStatus
    if getattr(host_status, '__hash__', None) is None:
      host_status.__hash__ = object.__hash__
except Exception:
  pass

# Work around certifi resource loading issues in packed PEX by using system CA bundle.
try:
  import ssl
  _cafile = ssl.get_default_verify_paths().cafile
  if _cafile and os.path.exists(_cafile):
    os.environ.setdefault('SSL_CERT_FILE', _cafile)
    try:
      import certifi
      def _certifi_where():
        return os.environ.get('SSL_CERT_FILE', _cafile)
      certifi.where = _certifi_where
    except Exception:
      pass
except Exception:
  pass

# Ensure forked twitter.common.zookeeper sources are discoverable even when
# twitter.common comes from site-packages.
try:
  import twitter.common as _tc
  _common_dir = os.path.join(os.path.dirname(__file__), 'twitter', 'common')
  if hasattr(_tc, '__path__') and _common_dir not in _tc.__path__:
    _tc.__path__.append(_common_dir)
except Exception:
  pass
