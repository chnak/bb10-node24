#!/usr/bin/env python3
"""Host toolset runs on Linux while the target OS is QNX.

V8_HAVE_TARGET_OS is not set for QNX, so v8config.h falls back to the host
OS and defines V8_TARGET_OS_LINUX with *no value* for the gcc -m32 host
build.  std-object-sizes.h then has `... && V8_TARGET_OS_LINUX && ...`,
which gcc rejects ("operator '&&' has no right operand").  Use defined(),
which is what the guard means anyway.
"""
P = "/root/nodebuild/node-v24.22.1/deps/v8/src/wasm/std-object-sizes.h"
s = open(P, encoding="utf-8").read()

old = "#if V8_TARGET_ARCH_X64 && defined(__clang__) && V8_TARGET_OS_LINUX &&          \\\n"
new = "#if V8_TARGET_ARCH_X64 && defined(__clang__) && defined(V8_TARGET_OS_LINUX) &&   \\\n"

if old in s:
    s = s.replace(old, new)
    open(P, "w", encoding="utf-8").write(s)
    print("patched std-object-sizes.h")
else:
    print("already patched or pattern changed")
