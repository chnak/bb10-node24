#!/bin/bash
D=/mnt/d/BB10/wslbuild/deploy
N=/root/nodebuild/node-v24.22.1/out/Release/node
U=/root/nodebuild/uv-qnx/lib/libuv.so.1
tmp=/tmp/symaudit
rm -rf $tmp; mkdir -p $tmp

# strong undefined symbols (skip weak 'w'/'v')
llvm-nm-18 -D --undefined-only "$N" 2>/dev/null | awk '$1=="U"{print $2}' | sed 's/@.*//' | sort -u > $tmp/undef_node
llvm-nm-18 -D --undefined-only "$U" 2>/dev/null | awk '$1=="U"{print $2}' | sed 's/@.*//' | sort -u > $tmp/undef_uv
cat $tmp/undef_node $tmp/undef_uv | sort -u > $tmp/undef_all

# defined symbols from every runtime library and from the executable itself
: > $tmp/defined_all
for f in "$N" "$U" "$D/libstdc++.so.6" "$D/libgcc_s.so.1" "$D/libbacktrace.so.1" \
         "$D/devlibs/libc.so.3" "$D/devlibs/libsocket.so.3" "$D/devlibs/libm.so.2"; do
  llvm-nm-18 -D --defined-only "$f" 2>/dev/null | awk '{print $3}' | sed 's/@.*//' | sort -u >> $tmp/defined_all
done
sort -u $tmp/defined_all -o $tmp/defined_all

comm -23 $tmp/undef_all $tmp/defined_all > $tmp/missing
echo "undefined (node+libuv): $(wc -l < $tmp/undef_all)"
echo "defined (all libs+exe): $(wc -l < $tmp/defined_all)"
echo "MISSING: $(wc -l < $tmp/missing)"
head -40 $tmp/missing
