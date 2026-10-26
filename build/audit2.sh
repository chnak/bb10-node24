#!/bin/bash
D=/mnt/d/BB10/wslbuild/deploy
S=/opt/bb10ndk/target_10_3_1_995/qnx6/armle-v7
N=/root/nodebuild/node-v24.22.1/out/Release/node
U=/root/nodebuild/uv-qnx/lib/libuv.so.1
tmp=/tmp/symaudit2
rm -rf $tmp; mkdir -p $tmp
llvm-nm-18 -D --undefined-only "$N" 2>/dev/null | awk '$1=="U"{print $2}' | sed 's/@.*//' | sort -u > $tmp/u1
llvm-nm-18 -D --undefined-only "$U" 2>/dev/null | awk '$1=="U"{print $2}' | sed 's/@.*//' | sort -u > $tmp/u2
cat $tmp/u1 $tmp/u2 | sort -u > $tmp/undef
: > $tmp/def
for f in "$N" "$U" "$D/libstdc++.so.6" "$D/libgcc_s.so.1" "$D/libbacktrace.so.1" \
         "$S/lib/libc.so.3" "$S/lib/libsocket.so.3" "$S/lib/libm.so.2"; do
  [ -f "$f" ] || continue
  llvm-nm-18 -D --defined-only "$f" 2>/dev/null | awk '{print $3}' | sed 's/@.*//' | sort -u >> $tmp/def
done
sort -u $tmp/def -o $tmp/def
comm -23 $tmp/undef $tmp/def > $tmp/missing
echo "undefined: $(wc -l < $tmp/undef)  defined: $(wc -l < $tmp/def)  missing: $(wc -l < $tmp/missing)"
cat $tmp/missing
