#!/bin/bash
set -e
N=/root/nodebuild/node-v24.22.1/out/Release/node
D=/mnt/d/BB10/wslbuild/deploy
ls -l "$N"
cp -f "$N" "$D/node.bin.stackfix"
if command -v llvm-strip-18 >/dev/null 2>&1; then
  llvm-strip-18 --strip-all "$D/node.bin.stackfix"
else
  llvm-strip --strip-all "$D/node.bin.stackfix"
fi
ls -l "$D/node.bin.stackfix"
file "$D/node.bin.stackfix" 2>/dev/null || true
