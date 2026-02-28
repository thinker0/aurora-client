import unittest
import google.protobuf
from pesos.vendor.mesos import mesos_pb2

class TestProtobufCompat(unittest.TestCase):
    def test_protobuf_version(self):
        # Verify that we are using Protobuf 3.x
        version = google.protobuf.__version__
        print(f"Detected Protobuf version: {version}")
        major_version = int(version.split('.')[0])
        self.assertGreaterEqual(major_version, 3, "Protobuf version should be 3.x for Python 3 compatibility")

    def test_pesos_import(self):
        # Verify that we can import mesos_pb2 via the pesos vendor namespace
        self.assertIsNotNone(mesos_pb2.FrameworkInfo, "Should be able to access FrameworkInfo in mesos_pb2")
