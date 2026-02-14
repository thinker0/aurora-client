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

import inspect
import time
import unittest

from unittest import mock
import pytest
from requests.auth import AuthBase
from thrift.transport import TTransport
from twitter.common.quantity import Amount, Time
from twitter.common.zookeeper.kazoo_client import TwitterKazooClient
from twitter.common.zookeeper.serverset.endpoint import ServiceInstance

import apache.aurora.client.api.scheduler_client as scheduler_client
from apache.aurora.common.auth.auth_module import AuthModule
from apache.aurora.common.cluster import Cluster
from apache.aurora.common.transport import TRequestsTransport

import gen.apache.aurora.api.AuroraAdmin as AuroraAdmin
import gen.apache.aurora.api.AuroraSchedulerManager as AuroraSchedulerManager
from gen.apache.aurora.api.constants import BYPASS_LEADER_REDIRECT_HEADER_NAME
from gen.apache.aurora.api.ttypes import (
    ExplicitReconciliationSettings,
    Hosts,
    JobConfiguration,
    JobKey,
    JobUpdateQuery,
    JobUpdateRequest,
    ResourceAggregate,
    Response,
    ResponseCode,
    ResponseDetail,
    ScheduleStatus,
    SlaPolicy,
    TaskQuery
)

ROLE = 'foorole'
JOB_NAME = 'barjobname'
JOB_ENV = 'devel'
JOB_KEY = JobKey(role=ROLE, environment=JOB_ENV, name=JOB_NAME)
DEFAULT_RESPONSE = Response()


def test_coverage():
  """Make sure a new thrift RPC doesn't get added without minimal test coverage."""
  for name, klass in inspect.getmembers(AuroraAdmin) + inspect.getmembers(AuroraSchedulerManager):
    if name.endswith('_args'):
      rpc_name = name[:-len('_args')]
      assert hasattr(TestSchedulerProxyAdminInjection, 'test_%s' % rpc_name), (
          'No test defined for RPC %s' % rpc_name)


class TestSchedulerProxyInjection(unittest.TestCase):
  def setUp(self):
    self.scheduler_client_get = mock.patch.object(
        scheduler_client.SchedulerClient,
        'get')
    self.mock_get = self.scheduler_client_get.start()
    self.addCleanup(self.scheduler_client_get.stop)

    self.mock_scheduler_client = mock.create_autospec(
        spec=scheduler_client.SchedulerClient,
        spec_set=False,
        instance=True)
    self.mock_thrift_client = mock.create_autospec(AuroraAdmin.Client, instance=True)

    self.mock_get.return_value = self.mock_scheduler_client
    self.mock_scheduler_client.get_thrift_client.return_value = self.mock_thrift_client

  def make_scheduler_proxy(self):
    return scheduler_client.SchedulerProxy(Cluster(name='local'))

  def test_startCronJob(self):
    self.mock_thrift_client.startCronJob.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().startCronJob(JOB_KEY)
    self.mock_thrift_client.startCronJob.assert_called_once_with(JOB_KEY)

  def test_createJob(self):
    job = JobConfiguration()
    self.mock_thrift_client.createJob.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().createJob(job)
    self.mock_thrift_client.createJob.assert_called_once_with(job)

  def test_replaceCronTemplate(self):
    job = JobConfiguration()
    self.mock_thrift_client.replaceCronTemplate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().replaceCronTemplate(job)
    self.mock_thrift_client.replaceCronTemplate.assert_called_once_with(job)

  def test_scheduleCronJob(self):
    job = JobConfiguration()
    self.mock_thrift_client.scheduleCronJob.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().scheduleCronJob(job)
    self.mock_thrift_client.scheduleCronJob.assert_called_once_with(job)

  def test_descheduleCronJob(self):
    self.mock_thrift_client.descheduleCronJob.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().descheduleCronJob(JOB_KEY)
    self.mock_thrift_client.descheduleCronJob.assert_called_once_with(JOB_KEY)

  def test_populateJobConfig(self):
    job = JobConfiguration()
    self.mock_thrift_client.populateJobConfig.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().populateJobConfig(job)
    self.mock_thrift_client.populateJobConfig.assert_called_once_with(job)

  def test_restartShards(self):
    self.mock_thrift_client.restartShards.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().restartShards(JOB_KEY, {0})
    self.mock_thrift_client.restartShards.assert_called_once_with(JOB_KEY, {0})

  def test_getTasksStatus(self):
    query = TaskQuery()
    self.mock_thrift_client.getTasksStatus.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().getTasksStatus(query)
    self.mock_thrift_client.getTasksStatus.assert_called_once_with(query)

  def test_getJobs(self):
    self.mock_thrift_client.getJobs.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().getJobs(ROLE)
    self.mock_thrift_client.getJobs.assert_called_once_with(ROLE)

  def test_killTasks(self):
    key = JobKey()
    self.mock_thrift_client.killTasks.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().killTasks(key, {0}, None)
    self.mock_thrift_client.killTasks.assert_called_once_with(key, {0}, None)

  def test_getQuota(self):
    self.mock_thrift_client.getQuota.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().getQuota(ROLE)
    self.mock_thrift_client.getQuota.assert_called_once_with(ROLE)

  def test_addInstances(self):
    key = JobKey()
    self.mock_thrift_client.addInstances.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().addInstances(key, 1)
    self.mock_thrift_client.addInstances.assert_called_once_with(key, 1)

  def test_getJobUpdateSummaries(self):
    query = JobUpdateQuery()
    self.mock_thrift_client.getJobUpdateSummaries.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().getJobUpdateSummaries(query)
    self.mock_thrift_client.getJobUpdateSummaries.assert_called_once_with(query)

  def test_getJobUpdateDetails(self):
    self.mock_thrift_client.getJobUpdateDetails.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().getJobUpdateDetails('update_id')
    self.mock_thrift_client.getJobUpdateDetails.assert_called_once_with('update_id', None)

  def test_startJobUpdate(self):
    request = JobUpdateRequest()
    self.mock_thrift_client.startJobUpdate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().startJobUpdate(request)
    self.mock_thrift_client.startJobUpdate.assert_called_once_with(request, None)

  def test_pauseJobUpdate(self):
    self.mock_thrift_client.pauseJobUpdate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().pauseJobUpdate('update_id')
    self.mock_thrift_client.pauseJobUpdate.assert_called_once_with('update_id', None)

  def test_resumeJobUpdate(self):
    self.mock_thrift_client.resumeJobUpdate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().resumeJobUpdate('update_id')
    self.mock_thrift_client.resumeJobUpdate.assert_called_once_with('update_id', None)

  def test_abortJobUpdate(self):
    self.mock_thrift_client.abortJobUpdate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().abortJobUpdate('update_id')
    self.mock_thrift_client.abortJobUpdate.assert_called_once_with('update_id', None)

  def test_rollbackJobUpdate(self):
    self.mock_thrift_client.rollbackJobUpdate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().rollbackJobUpdate('update_id')
    self.mock_thrift_client.rollbackJobUpdate.assert_called_once_with('update_id', None)

  def test_pulseJobUpdate(self):
    self.mock_thrift_client.pulseJobUpdate.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().pulseJobUpdate('update_id')
    self.mock_thrift_client.pulseJobUpdate.assert_called_once_with('update_id')

  def test_raise_auth_error(self):
    self.mock_thrift_client.killTasks.side_effect = TRequestsTransport.AuthError()
    self.mock_scheduler_client.get_failed_auth_message.return_value = 'failed auth'
    with pytest.raises(scheduler_client.SchedulerProxy.AuthError):
      self.make_scheduler_proxy().killTasks(None, None, None)


class TestSchedulerProxyAdminInjection(TestSchedulerProxyInjection):
  def test_startMaintenance(self):
    hosts = Hosts()
    self.mock_thrift_client.startMaintenance.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().startMaintenance(hosts)
    self.mock_thrift_client.startMaintenance.assert_called_once_with(hosts)

  def test_drainHosts(self):
    hosts = Hosts()
    self.mock_thrift_client.drainHosts.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().drainHosts(hosts)
    self.mock_thrift_client.drainHosts.assert_called_once_with(hosts)

  def test_slaDrainHosts(self):
    hosts = Hosts()
    policy = SlaPolicy()
    self.mock_thrift_client.slaDrainHosts.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().slaDrainHosts(hosts, policy, 10)
    self.mock_thrift_client.slaDrainHosts.assert_called_once_with(hosts, policy, 10)

  def test_maintenanceStatus(self):
    hosts = Hosts()
    self.mock_thrift_client.maintenanceStatus.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().maintenanceStatus(hosts)
    self.mock_thrift_client.maintenanceStatus.assert_called_once_with(hosts)

  def test_endMaintenance(self):
    hosts = Hosts()
    self.mock_thrift_client.endMaintenance.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().endMaintenance(hosts)
    self.mock_thrift_client.endMaintenance.assert_called_once_with(hosts)

  def test_setQuota(self):
    aggregate = ResourceAggregate()
    self.mock_thrift_client.setQuota.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().setQuota(ROLE, aggregate)
    self.mock_thrift_client.setQuota.assert_called_once_with(ROLE, aggregate)

  def test_forceTaskState(self):
    self.mock_thrift_client.forceTaskState.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().forceTaskState('taskid', ScheduleStatus.LOST)
    self.mock_thrift_client.forceTaskState.assert_called_once_with(
        'taskid', ScheduleStatus.LOST)

  def test_performBackup(self):
    self.mock_thrift_client.performBackup.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().performBackup()
    self.mock_thrift_client.performBackup.assert_called_once_with()

  def test_listBackups(self):
    self.mock_thrift_client.listBackups.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().listBackups()
    self.mock_thrift_client.listBackups.assert_called_once_with()

  def test_stageRecovery(self):
    query = TaskQuery()
    self.mock_thrift_client.stageRecovery.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().stageRecovery(query)
    self.mock_thrift_client.stageRecovery.assert_called_once_with(query)

  def test_queryRecovery(self):
    query = TaskQuery()
    self.mock_thrift_client.queryRecovery.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().queryRecovery(query)
    self.mock_thrift_client.queryRecovery.assert_called_once_with(query)

  def test_deleteRecoveryTasks(self):
    query = TaskQuery()
    self.mock_thrift_client.deleteRecoveryTasks.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().deleteRecoveryTasks(query)
    self.mock_thrift_client.deleteRecoveryTasks.assert_called_once_with(query)

  def test_commitRecovery(self):
    self.mock_thrift_client.commitRecovery.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().commitRecovery()
    self.mock_thrift_client.commitRecovery.assert_called_once_with()

  def test_unloadRecovery(self):
    self.mock_thrift_client.unloadRecovery.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().unloadRecovery()
    self.mock_thrift_client.unloadRecovery.assert_called_once_with()

  def test_snapshot(self):
    self.mock_thrift_client.snapshot.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().snapshot()
    self.mock_thrift_client.snapshot.assert_called_once_with()

  def test_pruneTasks(self):
    query = TaskQuery()
    self.mock_thrift_client.pruneTasks.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().pruneTasks(query)
    self.mock_thrift_client.pruneTasks.assert_called_once_with(query)

  def test_triggerExplicitTaskReconciliation(self):
    settings = ExplicitReconciliationSettings(batchSize=None)
    self.mock_thrift_client.triggerExplicitTaskReconciliation.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().triggerExplicitTaskReconciliation(settings)
    self.mock_thrift_client.triggerExplicitTaskReconciliation.assert_called_once_with(settings)

  def test_triggerImplicitTaskReconciliation(self):
    self.mock_thrift_client.triggerImplicitTaskReconciliation.return_value = DEFAULT_RESPONSE
    self.make_scheduler_proxy().triggerImplicitTaskReconciliation()
    self.mock_thrift_client.triggerImplicitTaskReconciliation.assert_called_once_with()


def mock_auth():
  auth_mock = mock.create_autospec(spec=AuthModule, instance=True)
  auth_mock.auth.return_value = mock.create_autospec(AuthBase)
  return auth_mock


@pytest.mark.parametrize('scheme', ('http', 'https'))
def test_url_when_not_connected_and_cluster_has_no_proxy_url(scheme):
  host = 'some-host.example.com'
  port = 31181

  mock_zk = mock.create_autospec(spec=TwitterKazooClient, instance=True)

  service_json = '''{
    "additionalEndpoints": {
        "%(scheme)s": {
            "host": "%(host)s",
            "port": %(port)d
        }
    },
    "serviceEndpoint": {
        "host": "%(host)s",
        "port": %(port)d
    },
    "shard": 0,
    "status": "ALIVE"
  }''' % dict(host=host, port=port, scheme=scheme)

  service_endpoints = [ServiceInstance.unpack(service_json)]

  def make_mock_client(proxy_url):
    client = scheduler_client.ZookeeperSchedulerClient(
        Cluster(proxy_url=proxy_url),
        auth=None,
        user_agent='Some-User-Agent',
        _deadline=lambda x, **kws: x())
    client.get_scheduler_serverset = mock.MagicMock(return_value=(mock_zk, service_endpoints))
    client.SERVERSET_TIMEOUT = Amount(0, Time.SECONDS)
    client._connect_scheduler = mock.MagicMock()
    return client

  client = make_mock_client(proxy_url=None)
  assert client.url == '%s://%s:%d' % (scheme, host, port)
  assert client.url == client.raw_url
  client._connect_scheduler.assert_has_calls([])

  client = make_mock_client(proxy_url='https://scheduler.proxy')
  assert client.url == 'https://scheduler.proxy'
  assert client.raw_url == '%s://%s:%d' % (scheme, host, port)
  client._connect_scheduler.assert_has_calls([])

  client = make_mock_client(proxy_url=None)
  client.get_thrift_client()
  assert client.url == '%s://%s:%d' % (scheme, host, port)
  client._connect_scheduler.assert_has_calls([mock.call('%s://%s:%d/api' % (scheme, host, port))])
  client._connect_scheduler.reset_mock()
  client.get_thrift_client()
  client._connect_scheduler.assert_has_calls([])


class TestSchedulerClient(unittest.TestCase):

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_scheduler(self, mock_client):
    mock_client.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    client = scheduler_client.SchedulerClient(mock_auth(), 'Some-User-Agent', verbose=True)
    client._connect_scheduler('https://scheduler.example.com:1337', mock_time)

    assert mock_client.return_value.open.has_calls(mock.call(), mock.call())
    mock_time.sleep.assert_called_once_with(
        scheduler_client.SchedulerClient.RETRY_TIMEOUT.as_(Time.SECONDS))

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_scheduler_with_user_agent(self, mock_transport):
    mock_transport.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    auth = mock_auth()
    user_agent = 'Some-User-Agent'

    client = scheduler_client.SchedulerClient(auth, user_agent, verbose=True)

    uri = 'https://scheduler.example.com:1337'
    client._connect_scheduler(uri, mock_time)

    mock_transport.assert_called_once_with(
        uri,
        auth=auth.auth(),
        user_agent=user_agent,
        session_factory=mock.ANY)

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_scheduler_without_bypass_leader_redirect(self, mock_transport):
    mock_transport.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    auth = mock_auth()
    user_agent = 'Some-User-Agent'

    client = scheduler_client.SchedulerClient(
        auth,
        user_agent,
        verbose=True,
        bypass_leader_redirect=False)

    uri = 'https://scheduler.example.com:1337'
    client._connect_scheduler(uri, mock_time)

    mock_transport.assert_called_once_with(
        uri,
        auth=auth.auth(),
        user_agent=user_agent,
        session_factory=mock.ANY)

    _, _, kwargs = mock_transport.mock_calls[0]
    session = kwargs['session_factory']()
    assert session.headers.get(BYPASS_LEADER_REDIRECT_HEADER_NAME) is None

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_scheduler_with_bypass_leader_redirect(self, mock_transport):
    mock_transport.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    auth = mock_auth()
    user_agent = 'Some-User-Agent'

    client = scheduler_client.SchedulerClient(
        auth,
        user_agent,
        verbose=True,
        bypass_leader_redirect=True)

    uri = 'https://scheduler.example.com:1337'
    client._connect_scheduler(uri, mock_time)

    mock_transport.assert_called_once_with(
        uri,
        auth=auth.auth(),
        user_agent=user_agent,
        session_factory=mock.ANY)

    _, _, kwargs = mock_transport.mock_calls[0]
    session = kwargs['session_factory']()
    assert session.headers[BYPASS_LEADER_REDIRECT_HEADER_NAME] == 'true'

  @mock.patch('apache.aurora.client.api.scheduler_client.SchedulerClient',
              spec=scheduler_client.SchedulerClient)
  @mock.patch('threading.Event.wait')
  def test_transient_error(self, _, client):
    mock_scheduler_client = mock.create_autospec(
        spec=scheduler_client.SchedulerClient,
        spec_set=False,
        instance=True)
    mock_thrift_client = mock.create_autospec(spec=AuroraAdmin.Client, instance=True)
    mock_thrift_client.killTasks.side_effect = [
        Response(responseCode=ResponseCode.ERROR_TRANSIENT,
                 details=[ResponseDetail(message="message1"), ResponseDetail(message="message2")]),
        Response(responseCode=ResponseCode.ERROR_TRANSIENT),
        Response(responseCode=ResponseCode.OK)]

    mock_scheduler_client.get_thrift_client.return_value = mock_thrift_client
    client.get.return_value = mock_scheduler_client

    proxy = scheduler_client.SchedulerProxy(Cluster(name='local'))
    proxy.killTasks(JobKey(), None, None)

    assert mock_thrift_client.killTasks.call_count == 3

  @mock.patch('apache.aurora.client.api.scheduler_client.SchedulerClient',
              spec=scheduler_client.SchedulerClient)
  @mock.patch('threading.Event.wait')
  def test_performBackup_retriable_errors(self, mock_wait, mock_client):
    mock_scheduler_client = mock.create_autospec(
        spec=scheduler_client.SchedulerClient,
        spec_set=False,
        instance=True)
    mock_thrift_client = mock.create_autospec(spec=AuroraAdmin.Client, instance=True)
    mock_thrift_client.performBackup.side_effect = [
      Response(responseCode=ResponseCode.ERROR_TRANSIENT),
      scheduler_client.SchedulerProxy.TimeoutError,
      Response(responseCode=ResponseCode.OK)]

    mock_scheduler_client.get_thrift_client.return_value = mock_thrift_client
    mock_client.get.return_value = mock_scheduler_client

    proxy = scheduler_client.SchedulerProxy(Cluster(name='local'))
    proxy.performBackup()

    assert mock_thrift_client.performBackup.call_count == 3
    assert mock_wait.call_count == 2

  @mock.patch('apache.aurora.client.api.scheduler_client.SchedulerClient',
              spec=scheduler_client.SchedulerClient)
  @mock.patch('threading.Event.wait')
  def test_performBackup_transport_exception(self, mock_wait, mock_client):
    mock_scheduler_client = mock.create_autospec(
      spec=scheduler_client.SchedulerClient,
      spec_set=False,
      instance=True)

    mock_thrift_client = mock.create_autospec(spec=AuroraAdmin.Client, instance=True)
    mock_thrift_client.performBackup.side_effect = TTransport.TTransportException('error')
    mock_scheduler_client.get_thrift_client.return_value = mock_thrift_client
    mock_client.get.return_value = mock_scheduler_client

    proxy = scheduler_client.SchedulerProxy(Cluster(name='local'))
    with pytest.raises(scheduler_client.SchedulerProxy.NotRetriableError):
      proxy.performBackup()

    assert mock_thrift_client.performBackup.call_count == 1
    assert not mock_wait.called

  @mock.patch('apache.aurora.client.api.scheduler_client.SchedulerClient',
              spec=scheduler_client.SchedulerClient)
  @mock.patch('threading.Event.wait')
  def test_getTierConfigs_transport_exception(self, mock_wait, mock_client):
    mock_scheduler_client = mock.create_autospec(
      spec=scheduler_client.SchedulerClient,
      spec_set=False,
      instance=True)

    mock_thrift_client = mock.create_autospec(spec=AuroraAdmin.Client, instance=True)
    mock_thrift_client.getTierConfigs.side_effect = [
      TTransport.TTransportException('error'),
      Response(responseCode=ResponseCode.OK)
    ]
    mock_scheduler_client.get_thrift_client.return_value = mock_thrift_client
    mock_client.get.return_value = mock_scheduler_client

    proxy = scheduler_client.SchedulerProxy(Cluster(name='local'))
    proxy.getTierConfigs(retry=True)

    assert mock_thrift_client.getTierConfigs.call_count == 2
    assert mock_wait.call_count == 1

  @mock.patch('apache.aurora.client.api.scheduler_client.SchedulerClient',
              spec=scheduler_client.SchedulerClient)
  def test_unknown_connection_error(self, client):
    mock_scheduler_client = mock.create_autospec(spec=scheduler_client.SchedulerClient,
                                                 instance=True)
    client.get.return_value = mock_scheduler_client
    proxy = scheduler_client.SchedulerProxy(Cluster(name='local'))

    # unknown, transient connection error
    mock_scheduler_client.get_thrift_client.side_effect = RuntimeError
    with pytest.raises(Exception):
      proxy.client()

    # successful connection on re-attempt
    mock_scheduler_client.get_thrift_client.side_effect = None
    assert proxy.client() is not None

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_direct_scheduler_with_user_agent(self, mock_transport):
    mock_transport.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    auth = mock_auth()
    user_agent = 'Some-User-Agent'
    uri = 'https://scheduler.example.com:1337'

    client = scheduler_client.DirectSchedulerClient(
        uri,
        auth=auth,
        verbose=True,
        user_agent=user_agent)

    client._connect_scheduler(uri, mock_time)

    mock_transport.assert_called_once_with(
        uri,
        auth=auth.auth(),
        user_agent=user_agent,
        session_factory=mock.ANY)

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_zookeeper_client_with_auth(self, mock_transport):
    mock_transport.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    user_agent = 'Some-User-Agent'
    uri = 'https://scheduler.example.com:1337'
    auth = mock_auth()
    cluster = Cluster(zk='zk', zk_port='2181')

    def auth_factory(_):
      return auth

    client = scheduler_client.SchedulerClient.get(
        cluster,
        auth_factory=auth_factory,
        user_agent=user_agent)

    client._connect_scheduler(uri, mock_time)

    mock_transport.assert_called_once_with(
        uri,
        auth=auth.auth(),
        user_agent=user_agent,
        session_factory=mock.ANY)

  @mock.patch('apache.aurora.client.api.scheduler_client.TRequestsTransport',
              spec=TRequestsTransport)
  def test_connect_direct_client_with_auth(self, mock_transport):
    mock_transport.return_value.open.side_effect = [TTransport.TTransportException, True]
    mock_time = mock.create_autospec(spec=time, instance=True)

    user_agent = 'Some-User-Agent'
    uri = 'https://scheduler.example.com:1337'
    auth = mock_auth()
    cluster = Cluster(scheduler_uri='uri')

    def auth_factory(_):
      return auth

    client = scheduler_client.SchedulerClient.get(
        cluster,
        auth_factory=auth_factory,
        user_agent=user_agent)

    client._connect_scheduler(uri, mock_time)

    mock_transport.assert_called_once_with(
        uri,
        auth=auth.auth(),
        user_agent=user_agent,
        session_factory=mock.ANY)

  def test_no_zk_or_scheduler_uri(self):
    cluster = None
    with self.assertRaises(TypeError):
      scheduler_client.SchedulerClient.get(cluster)
    cluster = Cluster()
    with self.assertRaises(ValueError):
      scheduler_client.SchedulerClient.get(cluster)

  def test__internal_connect(self):
    client = scheduler_client.SchedulerClient(mock_auth(), 'Some-User-Agent', verbose=True)
    self.assertIsNone(client._connect())
