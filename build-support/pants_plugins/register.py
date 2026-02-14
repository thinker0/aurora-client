# Custom BUILD file helpers for legacy Aurora BUILD syntax.

from pants.build_graph.build_file_aliases import BuildFileAliases
from pants.source.wrapped_globs import FilesetRelPathWrapper, Globs
from twitter.common.dirutil.fileset import Fileset


class RGlobs(FilesetRelPathWrapper):
    """Recursive globs matching files under the BUILD file's directory."""

    wrapped_fn = Fileset.rglobs
    validate_files = True


class ZGlobs(FilesetRelPathWrapper):
    """Zsh-style globs including **/ for recursive matches."""

    wrapped_fn = Fileset.zglobs
    validate_files = True


def build_file_aliases():
    return BuildFileAliases(
        context_aware_object_factories={
            "globs": Globs,
            "rglobs": RGlobs,
            "zglobs": ZGlobs,
        }
    )
