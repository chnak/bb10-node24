#!/bin/bash
set -u
D=/root/nodebuild/node-v24.22.1-icu
echo "== patch host mk again =="
python3 -I /mnt/d/BB10/wslbuild/newdistro/patch_host_mk.py "$D/out" | head -3
echo "== genccode LIBS now =="
sed -n '/^LIBS :=/,/^$/p' "$D/out/tools/icu/genccode.host.mk"
echo "== restart build =="
cd "$D" || exit 1
make -j3 BUILDTYPE=Release node
rc=$?
echo "BUILD_RC=$rc $(date)"
if [ $rc -eq 0 ]; then
  cp -f out/Release/node /mnt/d/BB10/wslbuild/deploy/node.bin.icu
  llvm-strip-18 --strip-all /mnt/d/BB10/wslbuild/deploy/node.bin.icu
  ls -l /mnt/d/BB10/wslbuild/deploy/node.bin.icu
fi
