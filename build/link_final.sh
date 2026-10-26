#!/bin/bash
set -u
L=$(sed -n '34646p' /tmp/dryrun3.txt)
printf '%s\n' "$L" > /tmp/link_node.sh
cd /root/nodebuild/node-v24.22.1 || exit 1
bash /tmp/link_node.sh
echo "LINK_RC=$?"
cp -f out/Release/node /mnt/d/BB10/wslbuild/deploy/node.bin.final
llvm-strip-18 --strip-all /mnt/d/BB10/wslbuild/deploy/node.bin.final
ls -l /mnt/d/BB10/wslbuild/deploy/node.bin.final
