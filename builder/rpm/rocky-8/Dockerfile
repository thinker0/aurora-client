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
FROM --platform=linux/amd64 rockylinux:8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
RUN yum update -y && \
    yum install -y \
    epel-release && \
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
    cyrus-sasl-devel \
    flex vim \
    gcc \
    gcc-c++ \
    java-11-openjdk-headless \
    libevent-devel \
    libtool \
    krb5-devel \
    libcurl-devel \
    libffi-devel \
    openssl \
    openssl-devel \
    patch \
    python39 \
    python39-devel \
    subversion-devel \
    tar \
    unzip \
    wget \
    which \
    zlib-devel

ENV LC_ALL=C
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk

ADD build.sh /build.sh
