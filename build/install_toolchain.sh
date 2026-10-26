#!/bin/bash
set -e
SELF=$(cd "$(dirname "$0")" && pwd)
TC=/root/nodebuild/toolchain
mkdir -p $TC /opt/qnxcompat /opt/qnxstubs
cp $SELF/toolchain/qnx-clang $TC/qnx-clang
chmod +x $TC/qnx-clang
cp $SELF/qnx_libstdcxx_shim.h /opt/qnxcompat/qnx_libstdcxx_shim.h
cp $SELF/syslog.h /opt/qnxcompat/syslog.h
ln -sf qnx-clang $TC/qnx-clang++
# QNX 6.6 has these symbols in libc; provide linker stubs for gyp lines.
echo "INPUT ( /opt/bb10ndk/target_10_3_1_995/qnx6/armle-v7/lib/libc.so.3 )" > /opt/qnxstubs/libatomic.so
ls -l $TC /opt/qnxstubs

cd /tmp
cat > wsmoke.cpp <<'EOF'
#include <cstdio>
#include <vector>
#include <string>
#include <span>
#include <bit>
int main() {
  std::vector<int> v{1,2,3};
  std::span<int> s(v);
  std::string t = "ok";
  printf("%s %zu %u\n", t.c_str(), s.size(), std::bit_cast<unsigned>(1.0f));
  return 0;
}
EOF
$TC/qnx-clang++ -std=c++20 -O1 -c wsmoke.cpp -o wsmoke.o
$TC/qnx-clang++ -o wsmoke wsmoke.o
file wsmoke
llvm-readelf-18 -d wsmoke | grep NEEDED

# shared-library path with soname + whole-archive, like gyp uses
$TC/qnx-clang -fPIC -c -x c -o wsmoke_c.o - <<'EOF'
int wsmoke_fn(void) { return 42; }
EOF
$TC/qnx-clang -o /tmp/libwsmoke.so -shared -Wl,-soname=libwsmoke.so.1 -Wl,--whole-archive wsmoke_c.o -Wl,--no-whole-archive
llvm-readelf-18 -d /tmp/libwsmoke.so | grep SONAME

if [ -d /root/nodebuild/uv-qnx/include ]; then
# link a shared lib + stdlib like node's final link
cat > wsmoke2.c <<'EOF'
#include <stdio.h>
#include <uv.h>
int main(void){ printf("uv=%s\n", uv_version_string()); return 0; }
EOF
$TC/qnx-clang -I/root/nodebuild/uv-qnx/include -c wsmoke2.c -o wsmoke2.o
$TC/qnx-clang -o wsmoke2 -Wl,--start-group wsmoke2.o -luv -Wl,--end-group -lbacktrace
file wsmoke2
llvm-readelf-18 -d wsmoke2 | grep NEEDED
cp wsmoke /tmp/wsmoke
cp wsmoke2 /tmp/wsmoke2
echo smoke-ok
else
  echo 'skip uv smoke test (build libuv first)'
fi
echo smoke-ok
