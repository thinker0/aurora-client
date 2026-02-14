#!/usr/bin/env bash
./build-artifact.sh centos-7 apache-aurora-0.23.3.tar.gz 0.23.3 2>&1 | tee builder.log
./build-artifact.sh rocky-8 apache-aurora-0.23.3.tar.gz 0.23.3 2>&1 | tee builder.log
