import unittest
import os
import shutil
import tempfile
import traceback

class TestExecutorResources(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.environ['MESOS_SANDBOX'] = self.test_dir

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_dump_runner_pex(self):
        try:
            from apache.aurora.executor.bin.thermos_executor_main import dump_runner_pex
            path = dump_runner_pex()
            print(f"DEBUG: Extracted to {path}")
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.path.basename(path), 'thermos_runner.pex')
            with open(path, 'rb') as f:
                header = f.read(2)
                self.assertEqual(header, b'#!', "PEX should start with shebang")
        except Exception:
            traceback.print_exc()
            raise
