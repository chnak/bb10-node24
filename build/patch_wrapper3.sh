#!/bin/bash
set -e
TC=/root/nodebuild/toolchain
cp /mnt/d/BB10/wslbuild/newdistro/toolchain/qnx-clang "$TC/qnx-clang"
chmod +x "$TC/qnx-clang"
ln -sfn qnx-clang "$TC/qnx-clang++"

python3 - <<'PY'
path = "/root/nodebuild/toolchain/qnx-clang"
src = open(path).read()

old = ' -fno-short-enums -fPIC"'
new = ' -fno-short-enums -fPIC -femulated-tls"'
assert src.count(old) == 1
src = src.replace(old, new, 1)

anchor = "linkargs+=(-lstdc++ -lgcc_s)"
assert src.count(anchor) == 1
src = src.replace(anchor, 'linkargs+=("/root/nodebuild/qnxshim/shim.o")\n  ' + anchor, 1)

open(path, "w").write(src)
print("patched", path)
PY

bash -n "$TC/qnx-clang" && echo "syntax ok"
ls -l "$TC/qnx-clang" "$TC/qnx-clang++"
grep -n 'femulated-tls\|qnxshim' "$TC/qnx-clang"
echo "=== compile section ==="
sed -n '33,43p' "$TC/qnx-clang"
echo "=== link section ==="
sed -n '96,112p' "$TC/qnx-clang"
