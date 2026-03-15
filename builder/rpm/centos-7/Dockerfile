# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
FROM --platform=linux/amd64 centos:7
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
# CentOS 7.9.2009(EOL) is the latest version available in the vault
RUN sed -i -e '/^mirrorlist/d;/^#baseurl=/{s,^#,,;s,/mirror,/vault,;}' /etc/yum.repos.d/CentOS*.repo

RUN yum -y upgrade --exclude 'kernel*' \
    && yum -y install centos-release-scl-rh epel-release \
    && sed -i -e '/^mirrorlist/d;/^#baseurl=/{s,^#,,;s,/mirror,/vault,;}' /etc/yum.repos.d/CentOS-SCLo*.repo \
    && sed -i -e 's|^#baseurl=https://download.fedoraproject.org/pub/epel/|baseurl=https://archives.fedoraproject.org/pub/archive/epel/|' /etc/yum.repos.d/epel*.repo \
    && sed -i -e '/^mirrorlist/d' /etc/yum.repos.d/epel*.repo

RUN yum update -y
# java-17-openjdk-headless may not be in the CentOS 7 vault; add Adoptium as fallback
RUN yum install -y java-17-openjdk-headless 2>/dev/null || \
    (printf '[Adoptium]\nname=Adoptium\nbaseurl=https://packages.adoptium.net/artifactory/rpm/rhel/7/x86_64\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.adoptium.net/artifactory/api/gpg/key/public\n' \
        > /etc/yum.repos.d/adoptium.repo && \
    yum install -y temurin-17-jdk && \
    ln -sfn /usr/lib/jvm/temurin-17 /usr/lib/jvm/java-17-openjdk)

RUN yum install -y \
    make \
    rpm-build \
    yum-utils \
    apr-devel \
    autoconf \
    automake \
    bison \
    boost-devel \
    cmake3 \
    cyrus-sasl-devel \
    flex \
    gcc \
    gcc-c++ \
    krb5-devel \
    libcurl-devel \
    libevent-devel \
    libffi-devel \
    libtool \
    openssl \
    openssl-devel \
    patch \
    python2-devel \
    rh-python38-python \
    rh-python38-python-devel \
    rh-python38-python-pip \
    rh-python38-python-wheel \
    subversion-devel \
    tar \
    unzip \
    wget \
    which \
    zlib-devel

RUN /usr/bin/ln -sfT /opt/rh/rh-python38/root/usr/bin/python3 /usr/bin/python3 \
      && /usr/bin/ln -sfT /opt/rh/rh-python38/root/usr/bin/python3.8 /usr/bin/python3.8

ENV LC_ALL=en_US.utf8
RUN JAVA_DIR=$(dirname $(dirname $(readlink -f /usr/bin/java))) && \
    ln -sfn "$JAVA_DIR" /usr/lib/jvm/java-17-openjdk
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk

ADD build.sh /build.sh
ADD build_wheels.sh /build_wheels.sh
