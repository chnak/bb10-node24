#!/usr/bin/env python3
"""Stop the host toolset from adopting Linux as the *target* OS.

The host toolset is built for OS=="qnx", so gyp defines neither
V8_HAVE_TARGET_OS nor any V8_TARGET_OS_*.  v8config.h then falls back to the
compiler's own OS, and the Linux host compiler makes V8_TARGET_OS_LINUX
defined with an empty value, which gcc rejects in `#if V8_TARGET_OS_LINUX`.

Defining it as 1 (patch_v8_qnx5) instead switched on Linux-only code in
wasm-objects.cc, but that file includes <sys/mman.h>/<sys/stat.h> under the
same macro *before* v8config.h is reached, so the includes were skipped and
the Linux code failed to compile.

The host toolset simulates the QNX target, so the target OS should be
"unknown" there, exactly as it is for the target compile.  Drop the fallback
definition and make the remaining bare tests use defined(), which is false
for both toolsets.
"""
import re
import subprocess

# 1) drop the V8_OS_LINUX -> V8_TARGET_OS_LINUX fallback in v8config.h
P = "/root/nodebuild/node-v24.22.1/deps/v8/include/v8config.h"
s = open(P, encoding="utf-8").read()
old = """#ifdef V8_OS_LINUX
# define V8_TARGET_OS_LINUX 1
#endif
"""
new = """// The host toolset is built for the QNX target with a Linux host compiler.
// Do not adopt the host OS as the target OS; see deps/v8/src/wasm/wasm-objects.cc.
"""
if old in s:
    s = s.replace(old, new)
elif "# define V8_TARGET_OS_LINUX\n" in s:
    old0 = """#ifdef V8_OS_LINUX
# define V8_TARGET_OS_LINUX
#endif
"""
    s = s.replace(old0, new)
open(P, "w", encoding="utf-8").write(s)
print("v8config.h: fallback removed")

# 2) rewrite bare uses so an empty definition can never come back to bite
files = subprocess.run(
    ["grep", "-rl", "--include=*.h", "--include=*.cc",
     "V8_TARGET_OS_LINUX", "/root/nodebuild/node-v24.22.1/deps/v8/src"],
    capture_output=True, text=True).stdout.split()

pat = re.compile(r"#(if|elif)(\s+)V8_TARGET_OS_LINUX(?!\w)")
for f in files:
    t = open(f, encoding="utf-8").read()
    n = pat.sub(lambda m: "#%s%sdefined(V8_TARGET_OS_LINUX)" % (m.group(1), m.group(2)), t)
    if n != t:
        open(f, "w", encoding="utf-8").write(n)
        print("patched", f)
