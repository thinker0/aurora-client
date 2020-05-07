# Aurora Scheduler Client

Python 2 based Aurora Schduler client.

**This project is looking for a maintainer. please reach out via slack if you're interested in maintaining this project.**

## Running all tests:
`$ ./pants test src/test/python/apache/aurora::`

## Building instructions:

### Client:

`$ ./pants binary src/main/python/apache/aurora/kerberos:kaurora`

### Admin client:

`$ ./pants binary src/main/python/apache/aurora/kerberos:kaurora_admin`

### Thermos observer:
`$ ./pants binary src/main/python/apache/aurora/tools:thermos_observer`

## Create python source distributions:
`$ ./build-support/release/make-python-sdists`
