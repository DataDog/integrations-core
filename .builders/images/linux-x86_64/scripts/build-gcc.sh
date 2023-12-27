#!/bin/bash

set -e

if [ -z "$GCC_VERSION" ] || [ -z "$GCC_SHA256" ]; then
	echo "The GCC_VERSION and GCC_SHA256 environment variables should be defined to run this script" >&2
	exit 1
fi

PREFIX=/opt/gcc-${GCC_VERSION}

compile_with_autoconf() {
	LIB=lib
	if [[ "$DD_TARGET_ARCH" == *64* ]]; then
		LIB=lib64
	fi
	[ -e /etc/redhat-release ] && configure_args="--libdir=$PREFIX/$LIB" || true
	./configure --prefix=$PREFIX $configure_args $*
	cpu_count=$(grep process /proc/cpuinfo | wc -l)
	make -j $cpu_count --silent
	make install-strip
}

url="https://mirrors.kernel.org/gnu/gcc/gcc-${GCC_VERSION}/gcc-${GCC_VERSION}.tar.gz"
archive=$(basename $url)
[ ! -e "$archive" ] && curl -LO $url || true
echo "${GCC_SHA256}  ${archive}" | sha256sum --check

tar xzf $(basename $url)
cd "gcc-${GCC_VERSION}"

contrib/download_prerequisites

compile_with_autoconf \
    --disable-nls \
    --enable-languages=c,c++ \
    --disable-multilib

cd -

rm -rf "gcc-${GCC_VERSION}" "gcc-${GCC_VERSION}.tar.gz"
