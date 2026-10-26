#!/bin/bash
set -u
python3 -I /mnt/d/BB10/wslbuild/newdistro/patch_final.py || exit 1
cd /root/nodebuild/node-v24.22.1/out || exit 1
make -j3 BUILDTYPE=Release \
  /root/nodebuild/node-v24.22.1/out/Release/obj.target/v8_base_without_compiler/deps/v8/src/flags/flags.o \
  /root/nodebuild/node-v24.22.1/out/Release/obj.target/tools/v8_gypfiles/libv8_libbase.a \
  /root/nodebuild/node-v24.22.1/out/Release/obj.host/tools/v8_gypfiles/libv8_libbase.a \
  2>&1 | grep -E '^(  CXX|  AR|make.*Error)'
echo "MAKE_RC=${PIPESTATUS[0]}"
