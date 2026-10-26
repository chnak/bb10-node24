#!/usr/bin/env python3
"""Drop the node-level '-L.../uv-qnx/lib -luv' from host tool links.

Node's config.gypi puts its shared-libuv link flags into the global
`libraries` list, which gyp also applies to host (x86 -m32) tools. The
libuv in uv-qnx/lib is ARM-only and the host has no 32-bit libuv, so
host tools (torque, bytecode_builtins_list_generator, ...) fail to link
even though they never call into libuv. Remove those two lines from the
generated host makefiles.
"""
import glob
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "/root/nodebuild/node-v24.22.1/out"

DROP = {
    "-L/root/nodebuild/uv-qnx/lib \\",
    "-luv \\",
    "-L/root/nodebuild/uv-qnx/lib",
    "-luv",
}

changed = []
for path in glob.glob(os.path.join(OUT, "**", "*.host.mk"), recursive=True):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    kept = []
    touched = False
    for line in lines:
        if line.strip() in DROP:
            touched = True
            continue
        kept.append(line)
    if touched:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(kept)
        changed.append(path)

print("patched %d host makefiles" % len(changed))
for p in changed:
    print("  " + os.path.relpath(p, OUT))
