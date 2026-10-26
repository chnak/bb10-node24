#!/bin/bash
set -e
NODE=${NODE:-/root/nodebuild/node-v24.22.1}
UV=$NODE/deps/uv
SYS=/opt/bb10ndk/target_10_3_1_995/qnx6
OUT=/root/nodebuild/uv-qnx
OBJ=$OUT/obj
rm -rf $OUT; mkdir -p $OBJ $OUT/include $OUT/lib

CC=clang-18
CFLAGS="-target armv7-unknown-nto-qnx6.6.0 -march=armv7-a -mfloat-abi=softfp -mfpu=neon --sysroot=$SYS \
  -isystem $SYS/usr/include -isystem $SYS/armle-v7/usr/include \
  -O2 -g -fPIC -fno-strict-aliasing -fno-short-enums -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE \
  -D_QNX_SOURCE -D__QNXNTO__ -D__QNX__=660 -D__LITTLEENDIAN__ -D__ARM__ -D_ALT_NS=1 \
  -DEALREADY=EALREADY_NEW \
  -I$UV/include -I$UV/src -I$UV/src/unix"

SRCS="
src/fs-poll.c
src/idna.c
src/inet.c
src/random.c
src/strscpy.c
src/strtok.c
src/thread-common.c
src/threadpool.c
src/timer.c
src/uv-common.c
src/uv-data-getter-setters.c
src/version.c
src/unix/async.c
src/unix/core.c
src/unix/dl.c
src/unix/fs.c
src/unix/getaddrinfo.c
src/unix/getnameinfo.c
src/unix/loop-watcher.c
src/unix/loop.c
src/unix/pipe.c
src/unix/poll.c
src/unix/process.c
src/unix/random-devurandom.c
src/unix/signal.c
src/unix/stream.c
src/unix/tcp.c
src/unix/thread.c
src/unix/tty.c
src/unix/udp.c
src/unix/posix-hrtime.c
src/unix/posix-poll.c
src/unix/qnx.c
src/unix/bsd-ifaddrs.c
src/unix/no-proctitle.c
src/unix/no-fsevents.c
"

echo "=== uv version: $(cat $UV/src/version.c | grep -o '\"[0-9.]*[^\"]*\"' | head -1)"
OBJS=""
for s in $SRCS; do
  o=$OBJ/$(basename $s .c).o
  echo "CC $s"
  $CC $CFLAGS -c $UV/$s -o $o
  OBJS="$OBJS $o"
done

echo "=== link"
ld.lld-18 -m armelf -shared --no-rosegment -soname libuv.so.1 -o $OUT/lib/libuv.so.1 $OBJS \
  $SYS/armle-v7/lib/crti.o $SYS/armle-v7/lib/crtn.o \
  -L$SYS/armle-v7/lib -L$SYS/armle-v7/usr/lib -lsocket -lc
ln -sf libuv.so.1 $OUT/lib/libuv.so
cp -a $UV/include/uv.h $UV/include/uv $OUT/include/
ls -l $OUT/lib $OUT/include
file $OUT/lib/libuv.so.1 2>/dev/null || true
