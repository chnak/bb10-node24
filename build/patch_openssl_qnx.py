#!/usr/bin/env python3
# Make the arm/no-asm OpenSSL config selection cover OS=="qnx".
files = ('/root/nodebuild/node-v24.22.1/deps/openssl/openssl_no_asm.gypi',
         '/root/nodebuild/node-v24.22.1/deps/openssl/openssl-cl_no_asm.gypi')
old = """    }, 'target_arch=="arm" and OS in ("linux", "android")', {"""
new = """    }, 'target_arch=="arm" and OS in ("linux", "android", "qnx")', {"""
for p in files:
    s = open(p).read()
    if '("linux", "android", "qnx")' in s:
        print('already patched:', p)
        continue
    assert old in s, p
    open(p, 'w').write(s.replace(old, new))
    print('patched:', p)
