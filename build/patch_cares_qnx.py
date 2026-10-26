#!/usr/bin/env python3
# c-ares (bundled in Node) has per-OS ares_config.h.  QNX 6.6 is close to
# Linux but lacks epoll, getrandom, pipe2, inet_net_pton, arc4random_buf and
# Linux namespaces, so derive a qnx config from the linux one.
import os

NODE = '/root/nodebuild/node-v24.22.1'
SRC = os.path.join(NODE, 'deps/cares/config/linux/ares_config.h')
DSTDIR = os.path.join(NODE, 'deps/cares/config/qnx')
DST = os.path.join(DSTDIR, 'ares_config.h')
GYP = os.path.join(NODE, 'deps/cares/cares.gyp')

UNDEF = [
    'HAVE_EPOLL',
    'HAVE_SYS_EPOLL_H',
    'HAVE_GETRANDOM',
    'HAVE_SYS_RANDOM_H',
    'HAVE_PIPE2',
    'HAVE_INET_NET_PTON',
    'HAVE_USER_NAMESPACE',
    'HAVE_UTS_NAMESPACE',
    # libsocket exports getservbyport_r but QNX 6.6 netdb.h does not declare
    # it; use the plain getservbyport fallback instead.
    'HAVE_GETSERVBYPORT_R',
    'GETSERVBYPORT_R_ARGS',
]

def undefine(text, name):
    # turn '#define NAME 1' (possibly trailing spaces) into an undef comment
    import re
    return re.sub(r'^#define\s+%s\b.*$' % name,
                  '/* #undef %s */' % name,
                  text, flags=re.M)

os.makedirs(DSTDIR, exist_ok=True)
s = open(SRC).read()
s = s.replace('src/lib/ares_config.h.  Generated from ares_config.h.in by configure.',
              'src/lib/ares_config.h for QNX 6.6 (derived from the linux config).')
for name in UNDEF:
    s = undefine(s, name)
open(DST, 'w').write(s)
print('wrote', DST)

s = open(GYP).read()
old = "        [ 'OS==\"linux\"', {\n          'include_dirs': [ 'config/linux' ],\n          'sources': [ 'config/linux/ares_config.h' ]\n        }],"
new = "        [ 'OS==\"qnx\"', {\n          'include_dirs': [ 'config/qnx' ],\n          'sources': [ 'config/qnx/ares_config.h' ]\n        }],\n        [ 'OS==\"linux\"', {\n          'include_dirs': [ 'config/linux' ],\n          'sources': [ 'config/linux/ares_config.h' ]\n        }],"
if "'config/qnx'" in s:
    print('cares.gyp already patched')
else:
    assert old in s, 'cares.gyp linux block not found'
    open(GYP, 'w').write(s.replace(old, new))
    print('patched cares.gyp')
