#!/usr/bin/env python3
"""Give the host-toolset js2c a host libuv.

configure.py puts the shared-libuv include dir and `-luv` in the global
target_defaults, which also applies to `node_js2c` (toolsets: host).  The
only libuv available there is the ARM/QNX target library, so the 32-bit host
link fails.  js2c does use libuv (scandir/chdir/strerror), so instead of
dropping libuv we drop the target `-luv` and link a 32-bit Linux libuv built
separately at /root/nodebuild/uv-host.
"""
P = "/root/nodebuild/node-v24.22.1/node.gyp"

with open(P, "r", encoding="utf-8") as f:
    src = f.read()

anchor = """      'target_name': 'node_js2c',
      'type': 'executable',
      'toolsets': ['host'],
"""
repl = anchor + """      # libuv is configured for the QNX target here; the host toolset needs
      # its own 32-bit Linux build of libuv instead.
      'libraries!': [ '-luv' ],
      'libraries': [ '/root/nodebuild/uv-host/libuv.a' ],
"""

if "/root/nodebuild/uv-host/libuv.a" in src:
    print("already patched")
else:
    if "'libraries!': [ '-luv' ]" in src:
        old = """      # libuv is configured for the QNX target here, not for the host toolset.
      'libraries!': [ '-luv' ],
"""
        src = src.replace(old, """      # libuv is configured for the QNX target here; the host toolset needs
      # its own 32-bit Linux build of libuv instead.
      'libraries!': [ '-luv' ],
      'libraries': [ '/root/nodebuild/uv-host/libuv.a' ],
""")
    else:
        assert src.count(anchor) == 1, "node_js2c anchor not unique"
        src = src.replace(anchor, repl)
    with open(P, "w", encoding="utf-8") as f:
        f.write(src)
    print("node.gyp patched")
