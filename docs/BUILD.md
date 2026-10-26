> **Repo note:** paths like `D:\BB10\wslbuild\newdistro` and `deploy` come from the original development machine. In this repository the same scripts are under `build/` (formerly `newdistro/`) and `deploy/`. The ICU build is documented in `ICU-BUILD.md`.

# BB10 / QNX 6.6 交叉编译 Node.js 24（BlackBerry Q20）

本文记录在 WSL 里为 BlackBerry Q20（BB10 10.3.3.3216 / QNX 6.6 / armle-v7 softfp）交叉编译
Node.js **v24.22.1**、部署到设备、并在终端里使用 `node` / `npm` / `npx` 的完整方法与坑。

- 最后更新：2026-10-24
- 构建机：Windows 11 + WSL2 发行版 `BB10Build`（Ubuntu）
- 目标：`armv7-unknown-nto-qnx6.6.0`，softfp，NEON
- 设备：Q20 Classic（SQC100-2），rooted，SSH 登录用户 `devuser`

> 约定：文中 `$` 表示 WSL 内命令，`#` 表示设备（QNX）内命令。

---

## 1. 目录与环境

| 用途 | 路径 |
|---|---|
| Node 源码 | `/root/nodebuild/node-v24.22.1` |
| NDK sysroot | `/opt/bb10ndk/target_10_3_1_995/qnx6` |
| GCC 13 C++ 头文件 | `/opt/gcc13qnx/include/c++/13`（+ `.../arm-qnx`） |
| GCC 9.3 头文件（设备运行时对应版本） | `/opt/gcc9qnx`（辅助参考） |
| 交叉编译器包装器 | `/root/nodebuild/toolchain/qnx-clang`（`qnx-clang++` 为符号链接） |
| 兼容头 | `/opt/qnxcompat/qnx_libstdcxx_shim.h`、`/opt/qnxcompat/syslog.h` |
| 链接桩 | `/opt/qnxstubs/libatomic.so`（链接脚本，指向设备 libc） |
| C++ 运行时 shim | `/root/nodebuild/qnxshim/shim.o` |
| 单独编译的 libuv | 源码 `deps/uv` → 输出 `/root/nodebuild/uv-qnx/{include,lib}` |
| 构建产物 | `/root/nodebuild/node-v24.22.1/out/Release/node`（未 strip，约 72MB） |
| 部署包 | `/root/nodebuild/deploy/`，对应设备 `/var/tmp/nodedist/` |
| 构建脚本/补丁 | `D:\BB10\wslbuild\newdistro\`（WSL 内为 `/mnt/d/BB10/wslbuild/newdistro/`） |

> 注意：C 盘空间紧张，大文件（node 源码、out、部署包）都放在 D 盘或 WSL 虚拟磁盘里，不要放 C 盘。

---

## 2. 核心难点概览

1. **QNX 6.6 没有原生 ELF TLS** → 必须给目标代码加 `-femulated-tls`（包装器里已加）。QB 的 `libgcc_s.so.1` 提供 `__emutls_get_address`。
2. **Node 24 需要 C++20 库，但设备只有 GCC 9.3 的 libstdc++** → 用 GCC 13 头文件编译，再链接到设备 GCC 9.3 的 `libstdc++.so.6`，并用 `qnxshim/shim.o` 补齐 GCC 11+ 才有的符号（`__once_proxy`、`__once_call`、`__throw_bad_array_new_length` 等）。
3. **clang 的 nto 驱动会去调用不存在的 QNX gcc** → 包装器在链接模式下把 GNU 风格链接行翻译成 `ld.lld-18` 直接调用。
4. **V8 的 host 工具会用宿主 OS（Linux）** → 必须打 `patch_v8_qnx6.py`，避免 host toolset 采用 Linux 目标配置。
5. **QNX 的若干 libc 行为与 Linux 不同** → 见第 5 节，每一处都有对应补丁。

---

## 3. 一次性准备（仅首次）

在 WSL (`BB10Build`) 中：

```bash
# 1) 安装交叉工具链包装器、兼容头、链接桩
MSYS_NO_PATHCONV=1 wsl -d BB10Build -- bash /mnt/d/BB10/wslbuild/newdistro/install_toolchain.sh

# 2) 编译并安装 C++ 运行时 shim（生成 /root/nodebuild/qnxshim/shim.o）
MSYS_NO_PATHCONV=1 wsl -d BB10Build -- bash /mnt/d/BB10/wslbuild/newdistro/install_shim.sh

# 3) 获取/解压 GCC 13 头文件（若 /opt/gcc13qnx 不存在）
MSYS_NO_PATHCONV=1 wsl -d BB10Build -- bash /mnt/d/BB10/wslbuild/newdistro/get_gcc13.sh

# 4) 应用源码补丁（详见第 5 节，按需执行）
```

> Windows 端调用 WSL 时加 `MSYS_NO_PATHCONV=1`，否则 Git Bash 会把 `/mnt/d/...` 转成 `C:/Program Files/Git/mnt/d/...`。

---

## 4. 配置与编译

### 4.1 配置（已生成过 `config.status`，一般不需要重跑）

```bash
cd /root/nodebuild/node-v24.22.1
./configure \
  --dest-os=qnx \
  --dest-cpu=arm \
  --cross-compiling \
  --shared-libuv \
  --shared-libuv-includes=/root/nodebuild/uv-qnx/include \
  --shared-libuv-libpath=/root/nodebuild/uv-qnx/lib \
  --with-intl=none \
  --without-inspector \
  --without-node-snapshot \
  --openssl-no-asm
```

**重要：如果重跑了 `./configure`，生成的 `out/**/*.host.mk` 会被覆盖，必须重新执行第 5.7 节的
`patch_host_mk.py`，否则宿主工具链接会失败。**

### 4.2 单独编译 libuv（启用 `--shared-libuv` 后 libuv 是独立 .so）

```bash
MSYS_NO_PATHCONV=1 wsl -d BB10Build -- bash /mnt/d/BB10/wslbuild/newdistro/build_uv_qnx.sh
# 产物：/root/nodebuild/uv-qnx/lib/libuv.so.1（约 644KB）
```

好处：libuv 的补丁、重编、重新部署**不需要重新链接 node**。

### 4.3 编译 node

```bash
cd /root/nodebuild/node-v24.22.1
make -j3 BUILDTYPE=Release node
```

- 首次全量编译耗时较长（数小时）；改 V8/Node 源码后是增量编译。
- 只改 libuv：执行 4.2 即可，不用动 node。
- 只改 V8 的某个 `.cc`（例如 `deps/v8/src/base/platform/platform-posix.cc`）会触发
  `v8_libbase` 重建，并可能连带重编 `v8_compiler` 等一批文件（10～30 分钟量级）。
- 产物：`out/Release/node`（未 strip，约 72MB）。

---

## 5. 已知 QNX 问题与补丁（非常重要）

所有补丁脚本都在 `D:\BB10\wslbuild\newdistro\`，用 `python3 -I <脚本>` 或 `bash <脚本>` 执行。

### 5.1 V8 host toolset 误用宿主 OS

- 症状：交叉编译时 V8 的 host 工具按 Linux 配置编译/链接，报错或产物不对。
- 补丁：`patch_v8_qnx6.py`（修改 v8config / gyp 目标 OS 判定）。

### 5.2 QNX 没有原生 TLS → 必须 `-femulated-tls`

- 包装器 `toolchain/qnx-clang` 的 `TARGET_FLAGS` 已包含 `-femulated-tls`，**任何重建都不要去掉**。
- 已用设备程序验证：emulated TLS 的线程隔离工作正常。

### 5.3 `struct dirent::d_name` 是柔性数组（libuv scandir 兼容层）

- 症状：`fs.readdir` 返回乱码文件名。
- 补丁：`patch_uv_qnx6.py`，按 `d_namelen+1` 拷贝，而不是只拷贝结构体头。
- 重编：`build_uv_qnx.sh`，只重部署 `libuv.so.1`。

### 5.4 最坑：QNX 的 `fcntl()` 成功时返回“旧标志位”

- 症状：`npm run` / `npx` / `npm exec` 子进程报 `ESRCH`（errno 3），`stdio:'inherit'` 失败。
- 根因：QNX 上 `fcntl(fd, F_SETFD/F_SETFL, flags)` 成功时返回的是**之前的 flags**（例如 1），
  而 libuv 的 `uv__cloexec` / `uv__nonblock_fcntl` 写成 `if (r) return UV__ERR(errno);`，
  把成功当失败，errno 又是陈旧值。
- 补丁：`patch_uv_core_qnx.py`，把判断改成 `if (r == -1)`。
- 文件：`deps/uv/src/unix/core.c`
- 重编：`build_uv_qnx.sh` → 重新部署 `libuv.so.1`。

### 5.5 V8 保守栈扫描越界（SIGSEGV）→ 用 `/proc/self/pmap` 求栈顶

- 症状（旧二进制）：`npm init -y`、空目录 `npm install` 等触发 GC 的操作段错误；
  崩溃地址稳定在 `heap::base::IteratePointersInStack`，扫描地址在 0x7fxxxxxx 未映射区。
- 根因：V8 的 QNX 分支把栈顶算成 `sp + __stackavail()`。但 QNX 的 `__stackavail()` 返回的是
  **向下到栈底还剩多少空间**，方向反了，导致栈顶被高估约一整个栈大小（主线程约 512KB），
  GC 扫描直接越过真实栈顶。
- 设备实测（重要）：
  - QNX 没有可用的 `pthread_getattr_np()` / `pthread_stackseg_np()`（头文件无声明或运行时为 NULL）。
  - 主线程栈 = **512KB**；`pthread_create` 默认线程栈 = **128KB**；自定义 64KB 线程栈也正确。
  - 线程栈的整个区域是预先映射的；`msync(addr, 4096, MS_ASYNC)` 对未映射页返回 ENOMEM。
  - **`/proc/self/pmap`（以及 `/proc/self/mappings`）可读**，每个线程栈是一条
    `vaddr,size,...,{stack}` 映射，`vaddr+size` 就是精确栈顶。
  - `sp - __stackavail()` 与映射起点差 0x200 左右，不能用来精确匹配；但「sp 落在哪条
    `{stack}` 区间」100% 可靠。
- 补丁：`patch_v8_stackstart_pmap.py`，改
  `deps/v8/src/base/platform/platform-posix.cc` 的 `Stack::ObtainCurrentThreadStackStart()`：
  解析 `/proc/self/pmap`，找到包含当前 sp 的 `{stack}` 映射并返回其末端；找不到时退回
  逐页 `msync` 探测（上限 16MB）。
- 为什么不再用纯 msync 探测：逐页向上探测在**上方紧邻其它映射**（如 V8 堆）时会一路成功，
  返回高出数 MB 的栈顶。设置 `QNX_STACK_DEBUG=1` 可打印实际取值：
  ```
  [qnx-stack] pmap sp=7ff04910 top=7ff05000 stack_lines=1
  ```
- 备份：源码同目录 `platform-posix.cc.pre-stackfix`（**不含**本补丁，含更早的 QNX 修改）。
- 注意：打补丁时锚点必须限定在 `ObtainCurrentThreadStackStart()` 函数内——本文件里
  `#elif defined(V8_OS_QNX)` 出现多次，用文件级锚点会误删整段代码。

### 5.5b 真正的 GC/分配崩溃根因：Maglev 取模代码生成（重要）

`npm init -y` / 空目录 `npm install` / 大循环 GC 的崩溃，**主因不是栈扫描**，而是 Maglev：

- 症状：`Fatal error in , line 0 / unreachable code`，随后 SIGTRAP；`--trace-gc` 能看到
  崩溃发生在分配触发的 Scavenge 附近，但关闭并发标记/并行 scavenge 都无效。
- 设备实测：同样的脚本加 `--no-maglev` 或 `--jitless` **全部通过**，默认（Maglev 开启）必崩。
- 定位方法：临时给 `V8_Fatal()` 加 `__builtin_return_address(0/1)` 打印，符号化后得到：
  - `UseScratchRegisterScope::AcquireVfp<DwVfpRegister>()`（UNREACHABLE）
  - 调用者 `maglev::(anonymous namespace)::Uint32Mod()`
  即 Maglev 生成 `%`（取模）代码时申请 VFP 暂存寄存器失败。
- 补丁：`patch_final.py`，把 `deps/v8/src/flags/flag-definitions.h` 的
  `DEFINE_BOOL(maglev, true, ...)` 改为默认 **false**。该头文件只被 `flags.cc` 包含，
  改默认值只需重编 `flags.o`，不用全量重编。
- 运行时仍可用 `--maglev` 手动开启（**会崩**，仅用于复现/调试）。
- 影响：失去 Maglev 中间层 JIT，仍有 Sparkplug + Turbofan；对 Q20 上的 npm 使用足够。

### 5.6 TTY 下 `unknown symbol: ptsname`（设备终端里 node/npm 起不来）

- 症状：在设备 Terminal 或 `ssh -t` 下运行 `node -v` / `npm`：
  ```
  unknown symbol: ptsname
  ldd:FATAL: Unresolved symbol "ptsname" called from libuv.so.1
  ```
  普通 SSH（无 TTY）不触发——QNX 的动态链接是懒解析，只有初始化 TTY 时才会调用。
- 根因：QNX libc 的 `<stdlib.h>` 声明了 `ptsname()` / `ptsname_r()`，但
  **libc.so.3 并不导出这两个符号**（NDK sysroot 与设备一致）。libuv 的
  `uv__tty_is_slave()` 在非 Linux/BSD/macOS 分支里回退调用 `ptsname()`。
- 全量审计：把 node + libuv 的全部 `U` 符号与 NDK libc/socket/m 的导出对比，
  **仅缺 `ptsname` 一个**。
- 补丁：`patch_uv_ptsname_qnx.py`，在 `deps/uv/src/unix/tty.c` 加：
  ```c
  #elif defined(__QNX__)
    /* QNX libc does not provide ptsname(); standard streams are slaves. */
    (void) fd;
    result = 1;
  #else
  ```
- 重编：`build_uv_qnx.sh`（libuv 是独立的 `.so`，**不需要重链 node**）。
- 部署：备份为 `libuv.so.1.pre-ptsname`，替换 `/var/tmp/nodedist/lib/libuv.so.1`。
- 验证：`ssh -t ... 'node -v; npm --version'`，以及 TTY 下 `npm init -y` /
  `npm install` / `npm exec` / GC 压力全部通过。
- 注意：QNX 上把任何 tty 都视为 slave 终端；若将来需要区分 pty master（node 不走此路径），
  再按 QNX 的 `/dev/pty*` 命名规则补充判断。

### 5.7 宿主工具（x86 -m32）被注入了 `-luv`

- 症状：编译过程中 `torque`、`bytecode_builtins_list_generator`、`mksnapshot` 等
  **LINK(host)** 失败：
  ```
  /usr/bin/ld: skipping incompatible .../uv-qnx/lib/libuv.so when searching for -luv
  /usr/bin/ld: cannot find -luv
  ```
- 根因：node 的 `config.gypi` 把 `-L.../uv-qnx/lib -luv` 放进全局 `libraries`，
  gyp 同样把它加到了 host 工具；而 host 工具是 **`-m32`（32 位）** 编译的，
  系统里只有 64 位 libuv，ARM 的 libuv 更不兼容。
- 补丁：`patch_host_mk.py`，删除 `out/**/*.host.mk` 里 `LIBS` 中的
  `-L/root/nodebuild/uv-qnx/lib \` 和 `-luv \` 两行（host 工具本身不用 libuv）。
- 执行时机：**每次重新 configure 之后**都要执行一次。

### 5.8 其它已处理的小问题

- OpenSSL / cares / ada / simdjson 等源码在 QNX 上的小兼容补丁：见
  `patch_openssl_qnx.py`、`patch_cares_qnx.py` 等（构建已通过，一般不需要再动）。
- `patch_js2c_qnx.py`、`patch_node_qnx*.py`：Node 自身在 QNX 下的兼容修正。
- 链接时缺 `libatomic`：`/opt/qnxstubs/libatomic.so` 是链接脚本，实际符号在设备 libc 中。

---

## 6. 产物处理与 strip

```bash
N=/root/nodebuild/node-v24.22.1/out/Release/node
cp -f "$N" /mnt/d/BB10/wslbuild/deploy/node.bin.final
llvm-strip-18 --strip-all /mnt/d/BB10/wslbuild/deploy/node.bin.final
# 约 72MB → 约 51MB
```

- 保留一份未 strip 的二进制用于崩溃符号化（`llvm-addr2line` / `llvm-nm` / `llvm-objdump`）。
- 该二进制是非 PIE 的 ELF32 EXEC，vaddr 基址 `0x10000`；
  例如 ip `0x01fa6fbc` → `llvm-addr2line -e out/Release/node 0x1fa6fbc`。

---

## 7. 部署到设备

### 7.1 连接前提

- 设备 USB 网络地址：`169.254.0.1`（Windows 侧）
- `bb10mt.exe` 的 qconnDoor 保持运行（它负责把 SSH 拉起来）：
  ```
  D:\BB10\v3root\bb10mt.exe connect -i 169.254.0.1 -p <端口> -k C:\Users\Administrator\.ssh\bb10_rsa4096.pub
  ```
  **SSH 只在它运行期间可用；需要重启它时先停掉旧进程再启动，不要同时跑两个。**
- Windows OpenSSH 需要显式打开老算法：

```powershell
$s = @(
  '-i','C:\Users\Administrator\.ssh\bb10_rsa4096',
  '-o','HostKeyAlgorithms=+ssh-rsa',
  '-o','PubkeyAcceptedAlgorithms=+ssh-rsa',
  '-o','KexAlgorithms=+diffie-hellman-group1-sha1',
  '-o','Ciphers=+aes128-ctr,aes128-cbc,3des-cbc',
  '-o','MACs=+hmac-sha1',
  '-o','StrictHostKeyChecking=no',
  '-o','BatchMode=yes'
)
```

### 7.2 上传与安装

```powershell
scp @s D:\BB10\wslbuild\deploy\node.bin.final devuser@169.254.0.1:/tmp/node.bin.final
scp @s D:\BB10\wslbuild\deploy\install_final.sh devuser@169.254.0.1:/tmp/install_final.sh
ssh @s devuser@169.254.0.1 'sh /tmp/install_final.sh'
```

设备端安装脚本的要点：

```sh
B=/var/tmp/nodedist/bin
[ -f "$B/node.bin.pre-final" ] || cp -p "$B/node.bin" "$B/node.bin.pre-final"
cp -f /tmp/node.bin.final "$B/node.bin"
chmod 755 "$B/node.bin"
```

> - `/var/tmp/nodedist` 属主是 `devuser`，可直接写。
> - scp 上去的文件默认不可执行，**必须 chmod 755**。
> - `/var/tmp` 可能在设备重启后被清空；若 `node` 失效，先检查该目录是否还在。

### 7.3 设备目录结构

```
/var/tmp/nodedist/
├── bin/
│   ├── node.bin              # 真正的 ELF（strip 后约 51MB）
│   ├── node                  # 包装脚本：设置 LD_LIBRARY_PATH 后 exec node.bin
│   ├── npm                   # 包装脚本：node.bin .../npm/bin/npm-cli.js
│   └── npx                   # 包装脚本：node.bin .../npm/bin/npx-cli.js
└── lib/
    ├── libuv.so.1            # 单独编译，可独立替换
    ├── libstdc++.so.6        # 来自设备的 GCC 9.3（/opt/build/nodeinspect/bin）
    ├── libgcc_s.so.1
    ├── libbacktrace.so.1
    └── node_modules/npm/     # npm 11.x，已去掉 test/docs
```

---

## 8. 在终端里使用 node / npm / npx

设备默认 shell 的 PATH 很精简（甚至连 `head` 都没有），推荐如下环境：

```sh
PATH=/accounts/1000/shared/misc/chnak/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH
```

- `chnak/bin/node` 是 BerryCore/clitools 自带的 v22 包装脚本，已替换为**优先使用
  `/var/tmp/nodedist/bin/node.bin`（v24）、失败再回退 v22 `--jitless`** 的版本。
- 原 v22 文件备份为：`/accounts/1000/shared/misc/chnak/bin/{node,npm,npx}.v22-orig`。
- npm/npx 包装脚本会设置默认缓存目录：
  `npm_config_cache=/var/tmp/nodedist/.npm-cache`（可被用户环境变量覆盖）。

验证：

```sh
node -v                    # v24.22.1
npm --version              # 11.19.1
npx --version              # 11.19.1
```

---

## 9. 验证清单（改动后建议全跑一遍）

```sh
export PATH=/accounts/1000/shared/misc/chnak/bin:/usr/bin:/bin:/usr/sbin:/sbin
export LD_LIBRARY_PATH=/var/tmp/nodedist/lib

node -v
npm --version

# 1) npm run / npx / npm exec（验证 libuv fcntl 修复）
cd /var/tmp/npmtest && npm run env | sed -n '1,6p'
npx --no-install semver 1.2.3
npm exec --no -- semver 1.2.3
npm exec --no -- node -e "console.log('spawn ok')"

# 2) 空目录初始化与安装（验证 V8 栈扫描修复）
rm -rf /var/tmp/npminit2 && mkdir -p /var/tmp/npminit2 && cd /var/tmp/npminit2
npm init -y
npm install is-number@7.0.0
node -e "console.log(require('is-number')(4))"

# 3) GC 压力测试
node --expose-gc -e '
let keep=[];
for (let i=0;i<300;i++){
  for (let j=0;j<20000;j++) keep.push({j,s:"x"+j});
  if (i%3===0) global.gc();
  keep.length=0;
}
console.log("gc stress ok");
'
```

期望：全部退出码 0，无 SIGSEGV / SIGTRAP。

---

## 10. 日常增量重建流程（速查）

```text
改的是什么？                    需要做什么
─────────────────────────────────────────────────────────────
deps/uv/**                     1) build_uv_qnx.sh
                               2) 部署 libuv.so.1（不用重链 node）
                               3) 重启 node 进程即可

deps/v8/** 或 src/**           1) make -j3 BUILDTYPE=Release node
                               2) strip 新 node → 部署 node.bin
                               3) 跑第 9 节验证

重新跑了 ./configure          1) patch_host_mk.py（必须！）
                               2) build_uv_qnx.sh（如需要）
                               3) make -j3 BUILDTYPE=Release node

只改了测试脚本/包装脚本        直接部署到设备对应目录即可
```

### 10.2 只改 V8 base 文件时，避免全量连锁重编（手工链接）

改 `deps/v8/src/base/**`（含 `platform-posix.cc`、`flags.cc` 的默认值）会让 host 侧
`v8_libbase` 重编 → `torque` 工具重链 → torque 生成物时间戳更新 → **整个 V8 连锁重编**
（`v8_compiler` / `v8_base_without_compiler` / `v8_initializers`，通常 40–90 分钟）。

如果只改了上述少量文件，可以只编译对应目标再手工链接：

```bash
cd /root/nodebuild/node-v24.22.1/out

# 1) 只重编 v8_libbase（target + host）
make -j3 BUILDTYPE=Release \
  /root/nodebuild/node-v24.22.1/out/Release/obj.target/tools/v8_gypfiles/libv8_libbase.a \
  /root/nodebuild/node-v24.22.1/out/Release/obj.host/tools/v8_gypfiles/libv8_libbase.a

# 2) 若改了 flags 默认值，单独重编 flags.o
make -j3 BUILDTYPE=Release \
  /root/nodebuild/node-v24.22.1/out/Release/obj.target/v8_base_without_compiler/deps/v8/src/flags/flags.o

# 3) 手工执行 node 的链接命令
#    从一次 `make -n` 的输出里抓取 "LINK(target) .../node" 后面那行 qnx-clang++ 命令，
#    存成 /tmp/link_node.sh 后执行：
bash /tmp/link_node.sh

# 4) strip 部署
cp -f out/Release/node /mnt/d/BB10/wslbuild/deploy/node.bin.final
llvm-strip-18 --strip-all /mnt/d/BB10/wslbuild/deploy/node.bin.final
```

`libv8_base_without_compiler.a` 是 **thin archive**（`llvm-ar ... T`），归档里存的是 `.o`
路径；重编 `.o` 后**不需要重新打包**归档，直接链接即可。

注意：不要为了“跳过重编”去批量 `touch` 对象再 `make`——gyp 的 `FORCE_DO_CMD` 会让
`--debug`/`-n` 的输出出现大量假 CXX，且任意一次 stamp 刷新都会再次触发重编，很容易把
时间戳搞乱。要么让 make 正常跑完，要么用上面的手工链接。

### 10.1 中途重启电脑后如何继续

编译是增量的，重启只会损失正在编的少量文件。重启后执行：

```bash
MSYS_NO_PATHCONV=1 wsl -d BB10Build -- bash /mnt/d/BB10/wslbuild/newdistro/resume_after_reboot.sh
```

脚本会：
1. 删除最后 90 秒内生成的 `.o`（防止关机时被截断的对象导致链接失败）；
2. 重新执行 `patch_host_mk.py`（幂等，确认 host 补丁还在）；
3. `make -j3 BUILDTYPE=Release node` 继续编译；
4. 成功后自动 strip 生成 `deploy/node.bin.stackfix`。

> SSH 依赖的 `bb10mt` qconnDoor 进程也会随重启消失，需要重新启动它（见 7.1）。

---

## 11. 常见错误速查

| 现象 | 原因 / 解决 |
|---|---|
| `ld: cannot find -luv`（LINK(host)） | host 工具是 `-m32`，且被注入 libuv。执行 `patch_host_mk.py`（重新 configure 后必做）。 |
| `undefined reference to __once_proxy` 等 | 没有链接 `qnxshim/shim.o`（用包装器链接即可自动包含）。 |
| `undefined reference to __emutls_get_address` | 编译时漏了 `-femulated-tls`。 |
| 设备上 `node: cannot execute` | 文件没有 `chmod 755`，或 `LD_LIBRARY_PATH` 没指向 `/var/tmp/nodedist/lib`。 |
| `spawn ... ESRCH` | libuv 的 fcntl 补丁没生效（部署了旧的 `libuv.so.1`）。 |
| GC 时 SIGSEGV / `IteratePointersInStack` | V8 栈顶补丁没生效（部署了旧的 `node.bin`）。 |
| `Fatal error ... unreachable code` + SIGTRAP | **Maglev 取模代码生成 bug**（见 5.5b）。确认部署的 `node.bin` 含「Maglev 默认关闭」补丁；`node --no-maglev ...` 可快速验证。 |
| `npm init` / `npm install` 立即崩 | 先查 Maglev（5.5b），再查栈顶补丁（5.5）。 |
| TTY 下 `unknown symbol: ptsname` / `ldd:FATAL` | libuv 引用了 QNX libc 未导出的 `ptsname`（5.6）；部署含 `patch_uv_ptsname_qnx.py` 的 `libuv.so.1`。 |
| 设备上 `head: cannot execute` | 默认 PATH 太精简，使用 `/accounts/1000/shared/misc/chnak/bin:/usr/bin:/bin`。 |
| 终端里 `node -v` 是 v22 | `chnak/bin/node` 包装脚本被还原了；重新执行 `install_chnak_wrappers.sh`。 |
| ssh `no matching host key type` | 加上 `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa`。 |
| ssh `Permission denied` | 确认 qconnDoor 正在运行、使用 `devuser` 和 `bb10_rsa4096` 私钥。 |
| WSL 里 `/mnt/d` 路径失效 | Windows 端调用 wsl 时加 `MSYS_NO_PATHCONV=1`。 |

---

## 12. 注意事项（务必遵守）

1. **不要刷机。** 本机已 root（root_v3 / 10.3.3.3216），只做软件层面的编译与部署。
2. **不要把设备密码写进任何文件**（包括本 README、脚本、记忆文件）。
3. **不要重新对 `DBBTool.exe` 做二进制字符串提取**（此前已确认风险高，需明确许可）。
4. **SSH 依赖 qconnDoor 常驻进程**；重启它之前先停旧的，避免端口冲突。
5. **大文件一律放 D 盘或 WSL 虚拟磁盘**，C 盘空间很小。
6. **不要在 Windows 侧 `cd` 进解压出来的第三方目录运行解释器**；脚本一律放
   `D:\BB10\wslbuild\...`，通过 `wsl -d BB10Build -- bash /mnt/d/...` 执行。
7. **`-femulated-tls` 不能丢**；`qnxshim/shim.o` 不能漏。
8. **重新 configure 后必须重跑 `patch_host_mk.py`**。
9. 安装新 `node.bin` 前先备份为 `node.bin.pre-stackfix`（或其它带日期后缀的名字），
   出问题可快速回滚：
   ```sh
   cp -f /var/tmp/nodedist/bin/node.bin.pre-stackfix /var/tmp/nodedist/bin/node.bin
   ```
10. 设备上 `/var/tmp` 可能不持久，重启后检查 `/var/tmp/nodedist` 是否存在；
    备份建议同时放一份到 `/accounts/1000/shared/misc/` 下。

---

## 13. 相关脚本索引

### 构建/补丁（`D:\BB10\wslbuild\newdistro\`）

| 脚本 | 作用 |
|---|---|
| `install_toolchain.sh` | 安装 `qnx-clang` 包装器、兼容头、链接桩 |
| `install_shim.sh` | 编译/安装 `qnxshim/shim.o` |
| `get_gcc13.sh` / `get_gcc9_headers.sh` | 获取 GCC 13 / 9.3 头文件 |
| `build_uv_qnx.sh` | 单独编译 libuv → `/root/nodebuild/uv-qnx/lib/libuv.so.1` |
| `build_npm_stage.sh` | 打包 npm 运行时（去掉 test/docs） |
| `patch_v8_qnx6.py` | V8 host/target OS 判定修正 |
| `patch_v8_stackstart.py` | 旧版栈顶修复（msync 页探测），已被 pmap 版取代 |
| `patch_v8_stackstart_pmap.py` | **V8 QNX 栈顶计算修复（`/proc/self/pmap` 的 `{stack}` 映射 + msync 兜底）** |
| `patch_final.py` | **Maglev 默认关闭 + 去掉诊断 + 写入最终栈顶分支** |
| `patch_diag_ra.py` | 诊断用：打印 `V8_Fatal` 调用返回地址 / 栈顶值（排查 UNREACHABLE 时用） |
| `patch_stack_probe.py` | 诊断用：msync 版栈顶打印（已弃用） |
| `build_final.sh` / `link_final.sh` | 只重编 flags/libbase + 手工链接，产出 `deploy/node.bin.final` |
| `build_thread_stackmap.sh` | 编译并部署 `thread_stackmap`（验证线程栈在 pmap 中的样子） |
| `msync_probe.c` | 验证 QNX 上 `msync` 对未映射页返回 ENOMEM |
| `patch_uv_core_qnx.py` | **libuv fcntl 返回值修正** |
| `patch_uv_ptsname_qnx.py` | **libuv TTY：避开 QNX libc 未导出的 `ptsname`（5.6）** |
| `patch_uv_qnx6.py` | libuv `dirent.d_name` 柔性数组修正 |
| `audit_symbols.sh` / `audit2.sh` | 全量对比 node+libuv 未定义符号与运行库导出（发现 `ptsname` 缺失） |
| `patch_host_mk.py` | **删除 host 工具链接行里的 `-luv`** |
| `patch_openssl_qnx.py` / `patch_cares_qnx.py` | OpenSSL / cares 兼容修正 |
| `patch_node_qnx*.py` / `patch_js2c_qnx.py` | Node 自身 QNX 兼容修正 |
| `copy_node.sh` | 复制 + strip 生成部署用 `node.bin.stackfix` |

### 部署/验证（`D:\BB10\wslbuild\deploy\`）

| 文件 | 作用 |
|---|---|
| `install_final.sh` | **当前正式安装脚本**：备份为 `node.bin.pre-final`，安装 `node.bin.final` 并跑全套验证 |
| `install_node_stackfix.sh` | 旧安装脚本（栈修复版），保留作参考 |
| `install_uvfix.sh` | 备份并安装修复后的 `libuv.so.1`，随后跑 npm/npx 测试 |
| `install_libuv_ptsname.sh` | **安装去掉 `ptsname` 引用的 `libuv.so.1`**（备份 `libuv.so.1.pre-ptsname`） |
| `test_tty_full.sh` | **真实 TTY（`ssh -t`）下的全套验证** |
| `install_chnak_wrappers.sh` | 安装优先 v24 的 `chnak/bin/{node,npm,npx}` 包装脚本 |
| `test_final.sh` | 设备端：版本 + 栈调试 + G 模式 + 300 轮 GC 压力 + Maglev 对照 |
| `test_maglev.sh` | 设备端：验证 `--no-maglev` / `--jitless` 能绕过崩溃 |
| `gc_stress.sh` | GC 压力测试 |
| `final_npm_test.sh` / `verify_final.sh` | 综合验证脚本 |

---

## 14. 当前状态（2026-10-24，已完成）

> **2026-10-26 更新**：ICU 版 Node 已编译成功（`deploy/node.bin.icu`），待设备部署验证；
> 重启电脑后的操作步骤见根目录 **`NEXT-STEPS.md`**。

设备 `/var/tmp/nodedist/bin/node.bin` = **最终版**（51,440,468 B，对应本地
`deploy/node.bin.final`；未 strip 的符号版在 `out/Release/node`，可用于崩溃定位）。

- ✅ Node v24.22.1 编译、部署成功；`node -v` / `npm -v` / `npx -v` 正常（11.19.1）。
- ✅ libuv fcntl 修复已部署：`npm run`、`npm exec`、子进程 spawn 正常。
- ✅ V8 栈顶修复已改为 `/proc/self/pmap` 的 `{stack}` 映射（`patch_v8_stackstart_pmap.py`），
  `QNX_STACK_DEBUG=1` 可验证（实测 `sp=7ff04910 top=7ff05000`）。
- ✅ **Maglev 默认关闭**（`patch_final.py`）：这是 `npm init -y` / 空目录 `npm install` /
  GC 压力测试崩溃的真正根因（`Uint32Mod` → `AcquireVfp` UNREACHABLE）。`--maglev` 手动开启仍会崩。
- ✅ 设备端全套验证通过：
  - `npm init -y`（空目录）→ `INIT_RC=0`
  - `npm install is-number@7.0.0` → `INSTALL_RC=0`，`require('is-number')(4) === true`
  - 300 轮 GC 压力 → `gc stress ok`
  - `npm run env`、`npm exec --no -- node -e ...` → 正常
- ✅ **TTY 修复已部署**：`libuv.so.1` 去掉 `ptsname` 引用（`patch_uv_ptsname_qnx.py`），
  设备终端 / `ssh -t` 下 `node -v`、`npm --version`、`npm init -y`、`npm install`、
  `npm exec`、GC 压力全部通过（`/dev/ttyp0`）。
- 备份（设备）：
  - `node.bin.pre-final`（上一版栈修复）、`node.bin.pre-stackfix`（更早的原始版）
  - `libuv.so.1.pre-ptsname`（上一版 libuv）、`libuv.so.1.pre-qnxfix`（更早）
- 已知限制：`npx --no-install semver` 需本地已装 semver，否则 npm 报「missing packages」，
  这不是崩溃，属正常提示。
