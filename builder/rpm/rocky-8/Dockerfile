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
    cyrus-sasl-devel \
    flex vim \
    gcc \
    gcc-c++ \
    java-1.8.0-openjdk-devel \
    krb5-devel \
    libcurl-devel \
    libffi-devel \
    openssl \
    openssl-devel \
    patch \
    python2 \
    python2-devel \
    subversion-devel \
    tar \
    unzip \
    wget \
    which \
    zlib-devel

ENV LC_ALL=C

# Crude workaround for https://github.com/gradle/gradle/issues/1782
RUN mkdir -p /usr/lib/jvm/java-8-openjdk-amd64/jre/lib/security
RUN ln -s /etc/pki/java/cacerts /usr/lib/jvm/java-8-openjdk-amd64/jre/lib/security/cacerts

ADD build.sh /build.sh
