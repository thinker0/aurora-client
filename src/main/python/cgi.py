import importlib.util
import os
import sysconfig
import html

_stdlib = sysconfig.get_path('stdlib')
_cgi_path = os.path.join(_stdlib, 'cgi.py')
_spec = importlib.util.spec_from_file_location('_stdlib_cgi', _cgi_path)
_stdlib_cgi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stdlib_cgi)

if not hasattr(_stdlib_cgi, 'escape'):
  _stdlib_cgi.escape = html.escape

for _name in dir(_stdlib_cgi):
  if not _name.startswith('_'):
    globals()[_name] = getattr(_stdlib_cgi, _name)

__all__ = [name for name in globals() if not name.startswith('_')]
