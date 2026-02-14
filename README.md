# Aurora Scheduler Client

Python 2 based Aurora Schduler client.

**This project is looking for a maintainer. please reach out via slack if you're interested in maintaining this project.**

## Running all tests:
`$ ./pants test src/test/python/apache/aurora::`

If you want to force local wheels (to avoid pulling external `twitter.common` packages),
use the wrapper:

`$ ./run-pants-local-wheels.sh test ::`

## Building instructions:

### Client:

`$ ./pants package src/main/python/apache/aurora/kerberos:kaurora`

### Admin client:

`$ ./pants package src/main/python/apache/aurora/kerberos:kaurora_admin`

### Kazoo Compatibility (aurora_admin)

The admin client uses `kazoo==2.10.0` while legacy `twitter.common.zookeeper`
expects older recipe APIs. We fork `twitter.common.zookeeper` into the repo and
apply a small compat shim:

- Shim: `src/main/python/apache/aurora/common/kazoo_compat.py`
- Applied early in: `src/main/python/apache/aurora/admin/aurora_admin.py`
- Forked package: `src/main/python/twitter/common/zookeeper`
- Wheels used from: `3rdparty/python/wheels`

If you update `kazoo`, update the wheel in `3rdparty/python/wheels` and re-run
`./run-aurora-admin.sh` to verify the host command still works.

To build a wheel for the forked package:

`$ ./pants package src/main/python/twitter/common/zookeeper:zookeeper_dist`

### Thermos observer:
`$ ./pants package src/main/python/apache/aurora/tools:thermos_observer`

## Create python source distributions:
`$ ./build-support/release/make-python-sdists`
