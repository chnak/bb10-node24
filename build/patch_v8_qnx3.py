#!/usr/bin/env python3
"""GCC 13 rejects the dependent member-template call `__ Tuple<...>(...)`
in int64-lowering-reducer.h; the standard form needs `template`, as V8
already writes for `__ template Projection<0>` just above.  Clang tolerates
it, but the ia32 host toolset is compiled with gcc -m32.
"""
P = "/root/nodebuild/node-v24.22.1/deps/v8/src/compiler/turboshaft/int64-lowering-reducer.h"

s = open(P, encoding="utf-8").read()
old = "return __ Tuple<Word32, Word32>(result, __ Word32Constant(0));"
new = "return __ template Tuple<Word32, Word32>(result, __ Word32Constant(0));"

n = s.count(old)
if n:
    s = s.replace(old, new)
    open(P, "w", encoding="utf-8").write(s)
    print(f"patched {n} occurrence(s)")
else:
    print("already patched")
