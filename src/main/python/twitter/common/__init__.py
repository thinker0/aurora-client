import collections
import collections.abc
import inspect
from pkgutil import extend_path

# Provide collections.Mutable* aliases for Python 3.11+ compatibility.
for name in ('MutableSet', 'MutableMapping', 'MutableSequence', 'Mapping', 'Sequence', 'Iterable', 'Callable'):
  if not hasattr(collections, name) and hasattr(collections.abc, name):
    setattr(collections, name, getattr(collections.abc, name))

# Restore inspect.getargspec for libraries that still use it.
if not hasattr(inspect, 'getargspec'):
  from collections import namedtuple
  ArgSpec = namedtuple('ArgSpec', 'args varargs keywords defaults')
  def _getargspec(func):
    spec = inspect.getfullargspec(func)
    return ArgSpec(spec.args, spec.varargs, spec.varkw, spec.defaults)
  inspect.getargspec = _getargspec

__path__ = extend_path(__path__, __name__)
