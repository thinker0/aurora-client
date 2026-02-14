import sys
import types
import unittest

from apache.aurora.common import kazoo_compat
from twitter.common.zookeeper.serverset import endpoint as serverset_endpoint


class KazooCompatTest(unittest.TestCase):
    def setUp(self):
        self._saved = {k: sys.modules.get(k) for k in list(sys.modules.keys()) if k.startswith("kazoo")}
        for k in list(sys.modules.keys()):
            if k.startswith("kazoo"):
                sys.modules.pop(k, None)

    def tearDown(self):
        for k in list(sys.modules.keys()):
            if k.startswith("kazoo"):
                sys.modules.pop(k, None)
        for k, v in self._saved.items():
            if v is not None:
                sys.modules[k] = v

    def test_apply_injects_shims(self):
        kazoo_mod = types.ModuleType("kazoo")
        kazoo_mod.__path__ = []
        recipe_mod = types.ModuleType("kazoo.recipe")
        sys.modules["kazoo"] = kazoo_mod
        sys.modules["kazoo.recipe"] = recipe_mod
        kazoo_mod.recipe = recipe_mod

        kazoo_compat.apply()

        from kazoo.recipe import barrier, lock, counter, election, lease, party, queue, partitioner

        self.assertTrue(hasattr(barrier, "Barrier"))
        self.assertTrue(hasattr(barrier, "DoubleBarrier"))
        self.assertTrue(hasattr(lock, "ReadLock"))
        self.assertTrue(hasattr(lock, "WriteLock"))
        self.assertTrue(hasattr(counter, "Counter"))
        self.assertTrue(hasattr(election, "Election"))
        self.assertTrue(hasattr(lease, "NonBlockingLease"))
        self.assertTrue(hasattr(lease, "MultiNonBlockingLease"))
        self.assertTrue(hasattr(party, "Party"))
        self.assertTrue(hasattr(party, "ShallowParty"))
        self.assertTrue(hasattr(queue, "Queue"))
        self.assertTrue(hasattr(queue, "LockingQueue"))
        self.assertTrue(hasattr(partitioner, "SetPartitioner"))


class ServerSetEndpointTest(unittest.TestCase):
    def test_unpack_thrift_missing_types(self):
        if serverset_endpoint.ThriftServiceInstance is not None:
            self.skipTest("Thrift types available in this environment")

        with self.assertRaises(ValueError):
            serverset_endpoint.ServiceInstance.unpack_thrift(b"blob", member_id=1)

    def test_unpack_json(self):
        value = {
            "status": "ALIVE",
            "serviceEndpoint": {"host": "h", "port": 123},
            "additionalEndpoints": {},
            "shard": 0,
        }
        import json
        inst = serverset_endpoint.ServiceInstance.unpack_json(json.dumps(value), member_id=1)
        self.assertEqual(inst.service_endpoint.host, "h")
        self.assertEqual(inst.service_endpoint.port, 123)
