#!/usr/bin/env python3
"""Host toolset runs on Linux with a QNX target.

v8config.h sees __linux__ from the host compiler and falls back to defining
V8_TARGET_OS_LINUX with an empty replacement list.  Bare uses such as
`#if V8_TARGET_OS_LINUX` (wasm-objects.cc) are then preprocessor errors.
Give the fallback definition the value 1, as the -D... gyp defines do.
"""
P = "/root/nodebuild/node-v24.22.1/deps/v8/include/v8config.h"
s = open(P, encoding="utf-8").read()

old = """#ifdef V8_OS_LINUX
# define V8_TARGET_OS_LINUX
#endif
"""
new = """#ifdef V8_OS_LINUX
# define V8_TARGET_OS_LINUX 1
#endif
"""
if old in s:
    s = s.replace(old, new)
    open(P, "w", encoding="utf-8").write(s)
    print("patched v8config.h")
else:
    print("already patched (or pattern changed)")
