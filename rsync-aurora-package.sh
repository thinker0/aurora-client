#!/usr/bin/env bash

# This script is used to sync the aurora package to the aurora repository
mv artifacts/aurora-centos-7/rpmbuild/SRPMS/aurora-*.src.rpm ~/heron-release/aurora/7/x86_64/SRPMS/
mv artifacts/aurora-centos-7/rpmbuild/RPMS/x86_64/aurora-*.rpm ~/heron-release/aurora/7/x86_64/RPMS/

mv artifacts/aurora-rocky-8/rpmbuild/SRPMS/aurora-*.src.rpm ~/heron-release/aurora/8/x86_64/SRPMS/
mv artifacts/aurora-rocky-8/rpmbuild/RPMS/x86_64/aurora-*.rpm ~/heron-release/aurora/8/x86_64/RPMS/

~/bin/rsync-aurora.sh