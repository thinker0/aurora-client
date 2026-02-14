#!/usr/bin/env bash
./pants package src/main/python/apache/aurora/client:aurora \
    && python3 build-support/flatten_dist_pex.py \
    && dist/aurora.pex "$@"

./pants package src/main/python/apache/aurora/admin:aurora_admin \
    && python3 build-support/flatten_dist_pex.py \
    && dist/aurora_admin.pex "$@"
