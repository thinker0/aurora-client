import os
import sys

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_src_main = os.path.join(_repo_root, "main", "python")
if _src_main not in sys.path:
    sys.path.insert(0, _src_main)
