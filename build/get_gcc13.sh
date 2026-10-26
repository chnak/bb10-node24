#!/bin/bash
set -u
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
mkdir -p /opt/dl && cd /opt/dl
U="http://archive.ubuntu.com/ubuntu/pool/main/g/gcc-13-cross/libstdc++-13-dev-armhf-cross_13.2.0-23ubuntu4cross1_all.deb"
DEB=$(basename "$U")
[ -s "$DEB" ] || curl -sSL --max-time 300 -O "$U"
ls -l "$DEB"
rm -rf /opt/gcc13armhf && mkdir -p /opt/gcc13armhf
dpkg-deb -x "$DEB" /opt/gcc13armhf
echo "=== target bits ==="
find /opt/gcc13armhf -name c++config.h | head
ls /opt/gcc13armhf/usr/arm-linux-gnueabihf/include/c++/13/arm-linux-gnueabihf/bits/ | head -30
echo "=== gcc 13.2 source for generic locale ==="
if [ ! -s gcc-13.2.0.tar.xz ]; then
  curl -sSL --max-time 520 -o gcc-13.2.0.tar.xz https://ftp.gnu.org/gnu/gcc/gcc-13.2.0/gcc-13.2.0.tar.xz
fi
ls -l gcc-13.2.0.tar.xz
tar -xJf gcc-13.2.0.tar.xz gcc-13.2.0/libstdc++-v3/config/locale/generic gcc-13.2.0/libstdc++-v3/config/os/qnx 2>/dev/null
echo "generic files:"; ls gcc-13.2.0/libstdc++-v3/config/locale/generic/
echo "qnx cfg files:"; ls gcc-13.2.0/libstdc++-v3/config/os/qnx/* 2>/dev/null
