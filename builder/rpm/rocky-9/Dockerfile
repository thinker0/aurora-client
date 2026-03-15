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
FROM --platform=linux/amd64 rockylinux:9

RUN yum update -y && \
    yum --enablerepo=crb install -y epel-release tix && \
    yum install -y \
    make vim \
    glibc-locale-source \
    rpm-build \
    yum-utils \
    apr-devel \
    autoconf \
    automake \
    bison \
    boost-devel \
    cmake \
    cyrus-sasl-devel \
    flex vim \
    gcc \
    gcc-c++ \
    java-17-openjdk-headless \
    krb5-devel \
    libcurl-devel \
    libevent-devel \
    libffi-devel \
    libtool \
    openssl \
    openssl-devel \
    patch \
    python3 \
    python3-devel \
    subversion-devel \
    tar \
    unzip \
    wget \
    which \
    zlib-devel

ENV LC_ALL=C
RUN JAVA_DIR=$(dirname $(dirname $(readlink -f /usr/bin/java))) && \
    ln -sfn "$JAVA_DIR" /usr/lib/jvm/java-17-openjdk
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk

ADD build.sh /build.sh
