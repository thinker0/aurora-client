import os
import sys

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_src_main = os.path.join(_repo_root, "main", "python")
if _src_main not in sys.path:
    sys.path.insert(0, _src_main)

import types

_twitter_dir = os.path.join(_src_main, "twitter")
if os.path.isdir(_twitter_dir):
    twitter_mod = sys.modules.get("twitter")
    if twitter_mod is None or not hasattr(twitter_mod, "__path__"):
        twitter_mod = types.ModuleType("twitter")
        sys.modules["twitter"] = twitter_mod
    twitter_mod.__path__ = [_twitter_dir]

_twitter_common_dir = os.path.join(_src_main, "twitter", "common")
if os.path.isdir(_twitter_common_dir):
    common_mod = sys.modules.get("twitter.common")
    if common_mod is None or not hasattr(common_mod, "__path__"):
        common_mod = types.ModuleType("twitter.common")
        sys.modules["twitter.common"] = common_mod
    common_mod.__path__ = [_twitter_common_dir]
