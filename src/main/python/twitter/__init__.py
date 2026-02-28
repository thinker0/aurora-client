import os
import sys
from pkgutil import extend_path

_package_root = os.path.dirname(__file__)
_repo_src = os.path.dirname(_package_root)
if _repo_src not in sys.path:
  sys.path.insert(0, _repo_src)

__path__ = extend_path(__path__, __name__)
