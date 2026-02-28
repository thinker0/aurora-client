import os
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_src_twitter = os.path.join(_repo_root, "main", "python", "twitter")
if _src_twitter not in __path__:
    __path__.append(_src_twitter)
