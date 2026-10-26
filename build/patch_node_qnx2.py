#!/usr/bin/env python3
"""QNX uid_t/gid_t are signed 32-bit ints, unlike Linux's uint32_t.

node_credentials.cc asserts exact type equality before converting a JS
Uint32 to uid_t.  The conversion is bit-identical on QNX, so relax the
assertion to a size check.
"""
P = "/root/nodebuild/node-v24.22.1/src/node_credentials.cc"
s = open(P, encoding="utf-8").read()

pairs = [
    ("static_assert(std::is_same<uid_t, uint32_t>::value);",
     "static_assert(sizeof(uid_t) == sizeof(uint32_t));"),
    ("static_assert(std::is_same<gid_t, uint32_t>::value);",
     "static_assert(sizeof(gid_t) == sizeof(uint32_t));"),
]
for old, new in pairs:
    if new in s:
        print("already patched:", old)
        continue
    assert s.count(old) == 1, "anchor not unique: " + old
    s = s.replace(old, new)

open(P, "w", encoding="utf-8").write(s)
print("node_credentials.cc patched")
