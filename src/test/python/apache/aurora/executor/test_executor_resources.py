import os
import shutil
import tempfile
import traceback
import unittest
import zipfile

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
            pex_path = os.path.join(self.test_dir, 'fake_thermos_executor.pex')
            resource_path = 'apache/aurora/executor/resources/thermos_runner.pex'
            runner_bytes = b'#!/usr/bin/env python3\nprint(\"ok\")\n'
            with zipfile.ZipFile(pex_path, 'w') as zf:
                zf.writestr(resource_path, runner_bytes)

            previous_pex = os.environ.get('PEX')
            os.environ['PEX'] = pex_path
            try:
                from apache.aurora.executor.bin.thermos_runner_resources import dump_runner_pex
                path = dump_runner_pex()
                print(f"DEBUG: Extracted to {path}")
                self.assertTrue(os.path.exists(path))
                self.assertEqual(os.path.basename(path), 'thermos_runner.pex')
                with open(path, 'rb') as f:
                    header = f.read(2)
                    self.assertEqual(header, b'#!', "PEX should start with shebang")
            finally:
                if previous_pex is None:
                    os.environ.pop('PEX', None)
                else:
                    os.environ['PEX'] = previous_pex
        except Exception:
            traceback.print_exc()
            raise
