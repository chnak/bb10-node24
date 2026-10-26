#!/bin/bash
set -e
python3 - <<'PY'
import os, subprocess
for name in ("qnx-clang", "qnx-clang++"):
    path = "/root/nodebuild/toolchain/" + name
    orig = path + ".orig"
    if os.path.exists(orig):
        src = open(orig).read()
    else:
        src = open(path).read()
    if "-femulated-tls" not in src:
        old = ' -fno-short-enums -fPIC"'
        new = ' -fno-short-enums -fPIC -femulated-tls"'
        assert old in src, "target flags line not found in " + name
        src = src.replace(old, new, 1)
    anchor = "linkargs+=(-lstdc++ -lgcc_s)"
    shim = 'linkargs+=("/root/nodebuild/qnxshim/shim.o")\n  '
    if "qnxshim/shim.o" not in src:
        assert src.count(anchor) == 1, "link anchor count != 1 in " + name
        src = src.replace(anchor, shim + anchor, 1)
    open(path, "w").write(src)
    r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
    print(name, "syntax_rc:", r.returncode, r.stderr.strip())
PY
grep -n 'femulated-tls\|qnxshim' /root/nodebuild/toolchain/qnx-clang /root/nodebuild/toolchain/qnx-clang++
echo "=== link section ==="
sed -n '30,45p;98,112p' /root/nodebuild/toolchain/qnx-clang
