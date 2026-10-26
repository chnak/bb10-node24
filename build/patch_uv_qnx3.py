#!/usr/bin/env python3
p = '/root/nodebuild/node-v24.22.1/deps/uv/src/unix/qnx.c'
s = open(p).read()
n0 = s

s = s.replace("((__ptr) = (__type *)((char *)(__ptr) + (__size)))",
              "((__ptr) = (__typeof__(__ptr))((char *)(__ptr) + (__size)))")

s = s.replace("    *totalmem = msg.o.info.__posix_tmi_total;\n"
              "    *freemem = msg.o.info.posix_tmi_length;",
              "#if __QNX__ >= 700\n"
              "    *totalmem = msg.o.info.__posix_tmi_total;\n"
              "#else\n"
              "    *totalmem = msg.o.size;\n"
              "#endif\n"
              "    *freemem = msg.o.info.posix_tmi_length;")

assert s != n0
open(p, 'w').write(s)
print('patched qnx.c round 3')
