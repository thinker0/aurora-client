python_sources(
  name = 'process_handle_ps_shim',
  sources = [
    'cgi.py',
    'cStringIO.py',
    'kazoo/__init__.py',
    'kazoo/recipe/__init__.py',
    'kazoo/recipe/barrier.py',
    'kazoo/recipe/counter.py',
    'kazoo/recipe/election.py',
    'kazoo/recipe/lease.py',
    'kazoo/recipe/lock.py',
    'kazoo/recipe/party.py',
    'kazoo/recipe/partitioner.py',
    'kazoo/recipe/queue.py',
    'kazoo/recipe/watchers.py',
    'Queue.py',
    'process_handle.py',
    'process_handle_ps.py',
    'process_provider.py',
    'sitecustomize.py',
    'StringIO.py',
    'urlparse.py',
  ],
)

# Fat source target for PEX packaging (Pants 2 migration shortcut)
target(
  name = 'all_src',
  dependencies = [
    'src/main/python:process_handle_ps_shim',
    'src/main/python/apache/aurora/admin:_admin',
    'src/main/python/apache/aurora/client:client',
    'src/main/python/apache/aurora/client/cli:auroraversion',
    'src/main/python/apache/aurora/common:common',
    'src/main/python/apache/aurora/config:config',
    'src/main/python/apache/aurora/executor:executor',
    'src/main/python/apache/aurora/kerberos:kerberos',
    'src/main/python/apache/aurora/tools:tools',
    'src/main/python/apache/thermos/cli',
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
    'src/main/python/apache/thermos/core',
    'src/main/python/apache/thermos/monitoring',
    'src/main/python/apache/thermos/observer',
    'src/main/python/apache/thermos/runner',
    'src/main/python/twitter:twitter_pkg',
    'src/main/python/twitter/common:common_sources',
    'src/main/python/twitter/common/zookeeper',
  ],
)

# Reduced source set for admin/client tools (excludes executor to avoid pesos/futures conflict)
target(
  name = 'admin_src',
  dependencies = [
    'src/main/python:process_handle_ps_shim',
    'src/main/python/apache/aurora/admin:_admin',
    'src/main/python/apache/aurora/client:client',
    'src/main/python/apache/aurora/client/cli:auroraversion',
    'src/main/python/apache/aurora/common:common',
    'src/main/python/apache/aurora/config:config',
    'src/main/python/apache/aurora/kerberos:kerberos',
    'src/main/python/apache/aurora/tools:tools',
    'src/main/python/apache/thermos/cli',
    'src/main/python/apache/thermos/common',
    'src/main/python/apache/thermos/config',
    'src/main/python/apache/thermos/core',
    'src/main/python/apache/thermos/monitoring',
    'src/main/python/apache/thermos/observer',
    'src/main/python/twitter:twitter_pkg',
    'src/main/python/twitter/common:common_sources',
    'src/main/python/twitter/common/zookeeper',
  ],
)

python_distribution(
  name = 'all_src_dist',
  dependencies = [
    ':all_src',
  ],
  provides = python_artifact(
    name = 'aurora-all-src',
    version = '0.0.0',
  ),
)
