#!/usr/bin/env bash
set -euo pipefail

./pants package ::
python3 build-support/flatten_dist_pex.py
