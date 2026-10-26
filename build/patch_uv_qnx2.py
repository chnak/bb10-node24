#!/usr/bin/env python3
p = '/root/nodebuild/node-v24.22.1/deps/uv/src/unix/qnx.c'
s = open(p).read()
orig = s

s = s.replace(
"#define SYSPAGE_ARRAY_ADJ_OFFSET(__type, __ptr, __size) \\\n"
"  ((__ptr) = (__type *)((char *)(__ptr) + (__size)))",
"#define SYSPAGE_ARRAY_ADJ_OFFSET(__type, __ptr, __size) \\\n"
"  ((__ptr) = (__typeof__(__ptr))((char *)(__ptr) + (__size)))")

s = s.replace(
"#if __QNX__ >= 800 || !defined(_SYSPAGE_ENTRY_SIZE)\n"
"#define cpuinfo_val cpuinfo",
"#if __QNX__ >= 800 || __QNX__ < 700\n"
"#define cpuinfo_val cpuinfo")

old = '''int uv_resident_set_memory(size_t* rss) {
  int fd;
  procfs_asinfo asinfo;

  fd = uv__open_cloexec("/proc/self/ctl", O_RDONLY);
  if (fd == -1)
    return UV__ERR(errno);

  if (devctl(fd, DCMD_PROC_ASINFO, &asinfo, sizeof(asinfo), 0) == -1) {
    uv__close(fd);
    return UV__ERR(errno);
  }

  uv__close(fd);
  *rss = asinfo.rss;
  return 0;
}'''

new = '''int uv_resident_set_memory(size_t* rss) {
  int fd;
#if defined(DCMD_PROC_ASINFO)
  procfs_asinfo asinfo;
#else
  /* QNX 6.6 has no ASINFO; private_mem is the closest available figure. */
  procfs_info asinfo;
#endif

  fd = uv__open_cloexec("/proc/self/ctl", O_RDONLY);
  if (fd == -1)
    return UV__ERR(errno);

#if defined(DCMD_PROC_ASINFO)
  if (devctl(fd, DCMD_PROC_ASINFO, &asinfo, sizeof(asinfo), 0) == -1) {
#else
  if (devctl(fd, DCMD_PROC_INFO, &asinfo, sizeof(asinfo), 0) == -1) {
#endif
    uv__close(fd);
    return UV__ERR(errno);
  }

  uv__close(fd);
#if defined(DCMD_PROC_ASINFO)
  *rss = asinfo.rss;
#else
  *rss = (size_t) asinfo.private_mem;
#endif
  return 0;
}'''

assert old in s, 'rss block not found'
s = s.replace(old, new, 1)
assert s != orig
open(p, 'w').write(s)
print('patched qnx.c')
