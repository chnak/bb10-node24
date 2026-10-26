#!/bin/bash
set -e
python3 - <<'PY'
import os
for name in ("qnx-clang", "qnx-clang++"):
    path = "/root/nodebuild/toolchain/" + name
    src = open(path).read()
    if not os.path.exists(path + ".orig"):
        open(path + ".orig", "w").write(src)
    if "-femulated-tls" not in src:
        old = ' -fno-short-enums -fPIC"'
        new = ' -fno-short-enums -fPIC -femulated-tls"'
        assert old in src, "target flags line not found in " + name
        src = src.replace(old, new, 1)
    shim = 'linkargs+=("/root/nodebuild/qnxshim/shim.o")\n'
    if shim not in src:
        anchor = 'if [ "$IS_CXX" = 1 ]; then'
        assert anchor in src, "link section not found in " + name
        src = src.replace(anchor, shim + anchor, 1)
    open(path, "w").write(src)
    print("patched", path)
PY
grep -n 'femulated-tls\|qnxshim' /root/nodebuild/toolchain/qnx-clang /root/nodebuild/toolchain/qnx-clang++
