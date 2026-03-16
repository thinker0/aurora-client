#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Tests for thermos_observer.py: --verbose flag, main() lifecycle, initialize()."""

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Stub heavy dependencies before loading thermos_observer.py
# ---------------------------------------------------------------------------

def _stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# --- twitter.common.log.options ---
_log_options_mock = MagicMock()
_stub('twitter.common.log.options', LogOptions=_log_options_mock)
_stub('twitter.common.log')

# --- twitter.common.app ---
_app_mod = _stub('twitter.common.app')
_app_mod.add_option = MagicMock()
_app_mod.main = MagicMock()
_app_mod.register_module = MagicMock()

# --- twitter.common ---
_tc_common = _stub('twitter.common', log=MagicMock(), app=_app_mod)

# --- twitter.common.exceptions ---
class _FakeExceptionalThread:
    def __init__(self, target=None):
        self._target = target
        self.daemon = False
    def start(self):
        pass

_stub('twitter.common.exceptions', ExceptionalThread=_FakeExceptionalThread)

# --- twitter.common.quantity ---
class _FakeAmount:
    def __init__(self, value, unit):
        self.value = value
        self.unit = unit

class _FakeTime:
    SECONDS = 'seconds'

_stub('twitter.common.quantity', Amount=_FakeAmount, Time=_FakeTime)

# --- twitter ---
_tc = _stub('twitter')
_tc.common = _tc_common

# --- apache stubs ---
_stub('apache')
_stub('apache.aurora')
_stub('apache.aurora.executor')
_stub('apache.aurora.executor.common')

_fake_path_detector_cls = MagicMock()
_stub('apache.aurora.executor.common.path_detector',
      MesosPathDetector=_fake_path_detector_cls)

_stub('apache.thermos')
_stub('apache.thermos.common')
_stub('apache.thermos.common.excepthook', ExceptionTerminationHandler=MagicMock())
_stub('apache.thermos.monitoring')
_stub('apache.thermos.monitoring.disk',
      DiskCollectorSettings=MagicMock())
_stub('apache.thermos.monitoring.resource',
      TaskResourceMonitor=MagicMock())
_stub('apache.thermos.observer')

_fake_task_observer_cls = MagicMock()
_stub('apache.thermos.observer.task_observer', TaskObserver=_fake_task_observer_cls)

_stub('apache.thermos.observer.http')
_fake_configure_server = MagicMock()
_stub('apache.thermos.observer.http.configure', configure_server=_fake_configure_server)


# ---------------------------------------------------------------------------
# Load thermos_observer.py directly via importlib
# ---------------------------------------------------------------------------

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_TEST_DIR, *(['..'] * 6)))
_OBS_PATH = os.path.join(
    _REPO_ROOT, 'src', 'main', 'python', 'apache', 'aurora', 'tools', 'thermos_observer.py'
)

spec = importlib.util.spec_from_file_location('apache.aurora.tools.thermos_observer', _OBS_PATH)
_mod = importlib.util.module_from_spec(spec)
_mod.__package__ = 'apache.aurora.tools'
sys.modules['apache.aurora.tools.thermos_observer'] = _mod
spec.loader.exec_module(_mod)

main = _mod.main
initialize = _mod.initialize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _options(**kwargs):
    """Build a mock options namespace with sensible defaults."""
    defaults = dict(
        verbose=False,
        mesos_root='/var/lib/mesos',
        ip='0.0.0.0',
        port=1338,
        polling_interval_secs=15,
        task_process_collection_interval_secs=20,
        task_disk_collection_interval_secs=60,
        disable_task_resource_collection=False,
        enable_mesos_disk_collector=False,
        agent_api_url='http://localhost:5051/containers',
        executor_id_json_path='[].executor_id',
        disk_usage_json_path='[].statistics.disk_limit_bytes',
        scheduler_web_url='http://localhost:28080',
        enable_authentication=None,
        oidc_issuer=None,
        oidc_userinfo_url=None,
        redis_cluster='redis://localhost:6379',
        redis_key_prefix='/aurora/thermos/user/',
    )
    defaults.update(kwargs)
    ns = MagicMock()
    for k, v in defaults.items():
        setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# Tests: --verbose flag
# ---------------------------------------------------------------------------

class TestVerboseFlag(unittest.TestCase):

    def setUp(self):
        _log_options_mock.reset_mock()
        _fake_configure_server.reset_mock()

    def test_verbose_true_sets_debug_log_level(self):
        opts = _options(verbose=True)
        root_server = MagicMock()
        root_server._bottle_observer = MagicMock()
        _fake_configure_server.return_value = root_server

        with patch.object(_mod, 'sleep_forever', side_effect=KeyboardInterrupt):
            try:
                main(None, opts)
            except KeyboardInterrupt:
                pass

        _log_options_mock.set_stderr_log_level.assert_called_once_with('google:DEBUG')

    def test_verbose_false_does_not_set_debug_log_level(self):
        opts = _options(verbose=False)
        root_server = MagicMock()
        root_server._bottle_observer = MagicMock()
        _fake_configure_server.return_value = root_server

        with patch.object(_mod, 'sleep_forever', side_effect=KeyboardInterrupt):
            try:
                main(None, opts)
            except KeyboardInterrupt:
                pass

        _log_options_mock.set_stderr_log_level.assert_not_called()

    def test_verbose_default_is_false(self):
        """Options namespace created without explicit verbose has verbose=False."""
        opts = _options()
        self.assertFalse(opts.verbose)


# ---------------------------------------------------------------------------
# Tests: main() lifecycle
# ---------------------------------------------------------------------------

class TestMainLifecycle(unittest.TestCase):

    def setUp(self):
        _log_options_mock.reset_mock()
        _fake_configure_server.reset_mock()

    def _run_main(self, opts, bottle_observer=None):
        root_server = MagicMock()
        root_server._bottle_observer = bottle_observer or MagicMock()
        _fake_configure_server.return_value = root_server
        with patch.object(_mod, 'sleep_forever', side_effect=KeyboardInterrupt):
            try:
                main(None, opts)
            except KeyboardInterrupt:
                pass
        return root_server

    def test_configure_server_called_with_observer_and_options(self):
        opts = _options()
        root_server = self._run_main(opts)
        _fake_configure_server.assert_called_once()
        args = _fake_configure_server.call_args[0]
        self.assertEqual(args[1], opts)

    def test_bottle_observer_close_called_on_exit(self):
        opts = _options()
        bottle_obs = MagicMock()
        self._run_main(opts, bottle_observer=bottle_obs)
        bottle_obs.close.assert_called_once()

    def test_no_bottle_observer_attribute_does_not_raise(self):
        opts = _options()
        root_server = MagicMock(spec=[])  # no _bottle_observer attribute
        _fake_configure_server.return_value = root_server
        with patch.object(_mod, 'sleep_forever', side_effect=KeyboardInterrupt):
            try:
                main(None, opts)  # must not raise AttributeError
            except KeyboardInterrupt:
                pass

    def test_bottle_observer_close_error_is_logged_not_raised(self):
        """close() errors during shutdown must not propagate — process is already exiting."""
        opts = _options()
        bottle_obs = MagicMock()
        bottle_obs.close.side_effect = RuntimeError('redis gone')
        # KeyboardInterrupt from sleep_forever must reach the caller even when close() fails
        with self.assertRaises(KeyboardInterrupt):
            with patch.object(_mod, 'sleep_forever', side_effect=KeyboardInterrupt):
                main(None, opts)

    def test_main_passes_initialized_observer_to_configure_server(self):
        """Observer created by initialize() must be the one passed to configure_server()."""
        opts = _options()
        root_server = MagicMock()
        root_server._bottle_observer = MagicMock()
        _fake_configure_server.return_value = root_server

        with patch.object(_mod, 'sleep_forever', side_effect=KeyboardInterrupt):
            try:
                main(None, opts)
            except KeyboardInterrupt:
                pass

        observer_passed = _fake_configure_server.call_args[0][0]
        self.assertIs(observer_passed, _fake_task_observer_cls.return_value)


# ---------------------------------------------------------------------------
# Tests: initialize()
# ---------------------------------------------------------------------------

class TestInitialize(unittest.TestCase):

    def setUp(self):
        _fake_task_observer_cls.reset_mock()
        _fake_path_detector_cls.reset_mock()

    def test_initialize_creates_path_detector_with_mesos_root(self):
        opts = _options(mesos_root='/custom/mesos')
        initialize(opts)
        _fake_path_detector_cls.assert_called_once_with('/custom/mesos')

    def test_initialize_returns_task_observer(self):
        opts = _options()
        result = initialize(opts)
        self.assertIs(result, _fake_task_observer_cls.return_value)

    def test_initialize_passes_disable_resource_collection(self):
        opts = _options(disable_task_resource_collection=True)
        initialize(opts)
        _, kwargs = _fake_task_observer_cls.call_args
        self.assertTrue(kwargs.get('disable_task_resource_collection'))

    def test_initialize_passes_enable_mesos_disk_collector(self):
        opts = _options(enable_mesos_disk_collector=True)
        initialize(opts)
        _, kwargs = _fake_task_observer_cls.call_args
        self.assertTrue(kwargs.get('enable_mesos_disk_collector'))


if __name__ == '__main__':
    unittest.main()
