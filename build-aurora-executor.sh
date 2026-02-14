#!/usr/bin/env bash

./build-artifact.sh builder apache-aurora-0.23.3.tar.gz 0.23.3 2>&1 && ~/bin/beta-rsync-aurora-executor.sh | tee builder.log
