#!/usr/bin/env python3
PATH = "/root/nodebuild/node-v24.22.1/deps/v8/src/base/platform/platform-posix.cc"
OLD = """  uintptr_t sp =
      reinterpret_cast<uintptr_t>(Stack::GetCurrentStackPosition());
"""
NEW = """  uintptr_t sp =
      static_cast<uintptr_t>(Stack::GetCurrentStackPosition());
"""
src = open(PATH, encoding="utf-8").read()
if NEW in src:
    print("already fixed")
elif OLD in src:
    open(PATH, "w", encoding="utf-8").write(src.replace(OLD, NEW))
    print("fixed cast")
else:
    print("ERROR: pattern not found")
    raise SystemExit(1)
