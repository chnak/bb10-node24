#!/usr/bin/env python3
"""Add a diagnostic print to the QNX stack-start path (idempotent)."""
import sys

P = "/root/nodebuild/node-v24.22.1/deps/v8/src/base/platform/platform-posix.cc"
MARK = "[qnx-stack]"

src = open(P, encoding="utf-8").read()
if MARK in src:
    print("already instrumented")
    sys.exit(0)

old = """  return reinterpret_cast<void*>(last_mapped + kPageSize);
#else"""
new = """  {
    void* result = reinterpret_cast<void*>(last_mapped + kPageSize);
    fprintf(stderr,
            "[qnx-stack] tid=%p sp=%p start=%p delta=%ld\\n",
            reinterpret_cast<void*>(pthread_self()),
            reinterpret_cast<void*>(sp), result,
            static_cast<long>(reinterpret_cast<uintptr_t>(result) - sp));
    return result;
  }
#else"""

if old not in src:
    print("ERROR: anchor not found", file=sys.stderr)
    sys.exit(1)

src = src.replace(old, new, 1)
open(P, "w", encoding="utf-8").write(src)
print("patched", P)
