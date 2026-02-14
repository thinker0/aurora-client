import contextlib

# Provide a Python 3 replacement for deprecated contextlib.nested used in legacy tests.
if not hasattr(contextlib, "nested"):
  @contextlib.contextmanager
  def _nested(*contexts):
    with contextlib.ExitStack() as stack:
      yield tuple(stack.enter_context(c) for c in contexts)

  contextlib.nested = _nested
