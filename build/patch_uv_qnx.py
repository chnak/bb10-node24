#!/usr/bin/env python3
import re, sys
p = '/root/nodebuild/node-v24.22.1/deps/uv/src/unix/fs.c'
s = open(p).read()
orig = s

# 1. uv__fs_to_timespec: drop QNX (no UTIME_NOW/UTIME_OMIT on QNX 6.6)
s = s.replace(
"""    || defined(__sun)                                                         \\
    || defined(__QNX__)
static struct timespec uv__fs_to_timespec(double time) {""",
"""    || defined(__sun)
static struct timespec uv__fs_to_timespec(double time) {""")

# 2. uv__fs_futime: drop QNX -> falls through to ENOSYS
s = s.replace(
"""    || defined(__sun)                                                         \\
    || defined(__QNX__)
  struct timespec ts[2];
  ts[0] = uv__fs_to_timespec(req->atime);
  ts[1] = uv__fs_to_timespec(req->mtime);
  return futimens(req->file, ts);""",
"""    || defined(__sun)
  struct timespec ts[2];
  ts[0] = uv__fs_to_timespec(req->atime);
  ts[1] = uv__fs_to_timespec(req->mtime);
  return futimens(req->file, ts);""")

# 3. uv__fs_utime: drop QNX from timespec list, add utimes fallback
s = s.replace(
"""    || defined(__sun)                                                         \\
    || defined(__QNX__)
  struct timespec ts[2];
  ts[0] = uv__fs_to_timespec(req->atime);
  ts[1] = uv__fs_to_timespec(req->mtime);
  return utimensat(AT_FDCWD, req->path, ts, 0);""",
"""    || defined(__sun)
  struct timespec ts[2];
  ts[0] = uv__fs_to_timespec(req->atime);
  ts[1] = uv__fs_to_timespec(req->mtime);
  return utimensat(AT_FDCWD, req->path, ts, 0);
#elif defined(__QNX__)
  struct timeval tv[2];
  tv[0].tv_sec = (time_t) req->atime;
  tv[0].tv_usec = (suseconds_t) ((req->atime - (double) tv[0].tv_sec) * 1e6);
  tv[1].tv_sec = (time_t) req->mtime;
  tv[1].tv_usec = (suseconds_t) ((req->mtime - (double) tv[1].tv_sec) * 1e6);
  return utimes(req->path, tv);""")

# 4. uv__fs_lutime: drop QNX -> ENOSYS (no lutimes on QNX 6.6)
s = s.replace(
"""    || defined(__sun)                                                         \\
    || defined(__QNX__)
  struct timespec ts[2];
  ts[0] = uv__fs_to_timespec(req->atime);
  ts[1] = uv__fs_to_timespec(req->mtime);
  return utimensat(AT_FDCWD, req->path, ts, AT_SYMLINK_NOFOLLOW);""",
"""    || defined(__sun)
  struct timespec ts[2];
  ts[0] = uv__fs_to_timespec(req->atime);
  ts[1] = uv__fs_to_timespec(req->mtime);
  return utimensat(AT_FDCWD, req->path, ts, AT_SYMLINK_NOFOLLOW);""")

# 5. copyfile: QNX stat fields (st_atime not st_atim)
s = s.replace(
"""#else
  times[0] = src_statsbuf.st_atim;
  times[1] = src_statsbuf.st_mtim;
#endif

  (void) futimens(dstfd, times);""",
"""#elif defined(__QNX__)
  times[0].tv_sec = src_statsbuf.st_atime;
  times[0].tv_nsec = 0;
  times[1].tv_sec = src_statsbuf.st_mtime;
  times[1].tv_nsec = 0;
#else
  times[0] = src_statsbuf.st_atim;
  times[1] = src_statsbuf.st_mtim;
#endif

#if defined(__QNX__)
  {
    struct timeval tv[2];
    tv[0].tv_sec = (time_t) times[0].tv_sec;
    tv[0].tv_usec = 0;
    tv[1].tv_sec = (time_t) times[1].tv_sec;
    tv[1].tv_usec = 0;
    (void) utimes(req->new_path, tv);
  }
#else
  (void) futimens(dstfd, times);
#endif""")

if s == orig:
    print('ERROR: no changes applied')
    sys.exit(1)
open(p, 'w').write(s)
print('patched fs.c')
