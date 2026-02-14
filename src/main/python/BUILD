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
    'twitter/__init__.py',
    'twitter/common/__init__.py',
    'twitter/common/collections/__init__.py',
    'twitter/common/collections/orderedset.py',
    'twitter/common/lang/__init__.py',
    'twitter/common/recordio/__init__.py',
    'twitter/common/zookeeper/kazoo_client.py',
    'urlparse.py',
  ],
)

# Fat source target for PEX packaging (Pants 2 migration shortcut)
python_sources(
  name = 'all_src',
  sources = [
    'apache/**/*.py',
    'twitter/**/*.py',
    'process_handle_ps.py',
  ],
  resolve = 'python-default',
)

# Reduced source set for admin/client tools (excludes executor to avoid pesos/futures conflict)
python_sources(
  name = 'admin_src',
  sources = [
    'apache/**/*.py',
    'twitter/**/*.py',
    '!apache/aurora/executor/**',
    '!apache/aurora/executor/**/*.py',
  ],
  resolve = 'python-default',
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
