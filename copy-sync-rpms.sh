#!/usr/bin/env bash

rsync -avl artifacts/aurora-centos-7/rpmbuild/RPMS/x86_64/*.rpm ~/heron-release/aurora/7/x86_64/RPMS/
rsync -avl artifacts/aurora-centos-7/rpmbuild/SRPMS/*.rpm ~/heron-release/aurora/7/x86_64/SRPMS/

rsync -avl artifacts/aurora-rocky-8/rpmbuild/RPMS/x86_64/*.rpm ~/heron-release/aurora/8/x86_64/RPMS/
rsync -avl artifacts/aurora-rocky-8/rpmbuild/SRPMS/*.rpm ~/heron-release/aurora/8/x86_64/SRPMS/

~/bin/rsync-aurora.sh