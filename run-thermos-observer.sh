#!/usr/bin/env bash
./pants package src/main/python/apache/aurora/tools:thermos_observer \
    && python3 build-support/flatten_dist_pex.py \
    && arch -x86_64 /usr/bin/python3 \
      dist/thermos_observer.pex \
      --log_to_stderr=google:DEBUG \
      --log_to_disk=NONE \
      "$@"
