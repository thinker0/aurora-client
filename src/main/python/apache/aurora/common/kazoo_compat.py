"""
Compatibility shims for newer kazoo versions used by legacy twitter.common.zookeeper.
"""

from __future__ import annotations

import sys
import types


def _ensure_module(name: str) -> types.ModuleType:
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return mod


def _set_default(mod: types.ModuleType, name: str, obj) -> None:
    if not hasattr(mod, name):
        setattr(mod, name, obj)


def apply() -> None:
    try:
        import kazoo.recipe  # type: ignore
    except Exception:
        return

    recipe_mod = _ensure_module("kazoo.recipe")

    # barrier
    barrier_mod = _ensure_module("kazoo.recipe.barrier")

    class Barrier:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            pass

        def wait(self, *args, **kwargs):
            return True

    class DoubleBarrier:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            pass

        def enter(self, *args, **kwargs):
            return True

        def leave(self, *args, **kwargs):
            return True

    _set_default(barrier_mod, "Barrier", Barrier)
    _set_default(barrier_mod, "DoubleBarrier", DoubleBarrier)

    # counter
    counter_mod = _ensure_module("kazoo.recipe.counter")

    class Counter:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            self._value = 0

        def value(self):
            return self._value

        def increment(self, value=1):
            self._value += value
            return self._value

        def decrement(self, value=1):
            self._value -= value
            return self._value

    _set_default(counter_mod, "Counter", Counter)

    # election
    election_mod = _ensure_module("kazoo.recipe.election")

    class Election:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            pass

        def run(self, func, *args, **kwargs):
            return func(*args, **kwargs)

    _set_default(election_mod, "Election", Election)

    # lease
    lease_mod = _ensure_module("kazoo.recipe.lease")

    class NonBlockingLease:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return True

        def __exit__(self, exc_type, exc, tb):
            return False

    class MultiNonBlockingLease(NonBlockingLease):  # pragma: no cover
        pass

    _set_default(lease_mod, "NonBlockingLease", NonBlockingLease)
    _set_default(lease_mod, "MultiNonBlockingLease", MultiNonBlockingLease)

    # lock
    lock_mod = _ensure_module("kazoo.recipe.lock")

    class Lock:  # pragma: no cover - simple shim
        def __init__(self, *args, **kwargs):
            pass

        def acquire(self, *args, **kwargs):
            return True

        def release(self):
            return True

    class ReadLock(Lock):  # pragma: no cover
        pass

    class WriteLock(Lock):  # pragma: no cover
        pass

    class Semaphore(Lock):  # pragma: no cover
        pass

    _set_default(lock_mod, "Lock", Lock)
    _set_default(lock_mod, "ReadLock", ReadLock)
    _set_default(lock_mod, "WriteLock", WriteLock)
    _set_default(lock_mod, "Semaphore", Semaphore)

    # party
    party_mod = _ensure_module("kazoo.recipe.party")

    class Party:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

        def __iter__(self):
            return iter(())

    class ShallowParty(Party):  # pragma: no cover
        pass

    _set_default(party_mod, "Party", Party)
    _set_default(party_mod, "ShallowParty", ShallowParty)

    # queue
    queue_mod = _ensure_module("kazoo.recipe.queue")

    class Queue:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

        def put(self, *args, **kwargs):
            return True

        def get(self, *args, **kwargs):
            return None

    class LockingQueue(Queue):  # pragma: no cover
        pass

    _set_default(queue_mod, "Queue", Queue)
    _set_default(queue_mod, "LockingQueue", LockingQueue)

    # partitioner
    partitioner_mod = _ensure_module("kazoo.recipe.partitioner")

    class SetPartitioner:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("SetPartitioner is not supported in this shim.")

    _set_default(partitioner_mod, "SetPartitioner", SetPartitioner)

    # Wire recipe modules under kazoo.recipe namespace
    for mod in (
        barrier_mod,
        counter_mod,
        election_mod,
        lease_mod,
        lock_mod,
        party_mod,
        queue_mod,
        partitioner_mod,
    ):
        name = mod.__name__.split(".")[-1]
        _set_default(recipe_mod, name, mod)
