"""QNX fix: fcntl(F_SETFD/F_SETFL) returns the previous flags on success.

libuv's uv__cloexec()/_nonblock_fcntl() treat any non-zero return as failure,
which turns a successful F_SETFD (returning the old FD_CLOEXEC bit => 1) into
UV_ESRCH with a stale errno. This broke child_process spawns with stdio
'inherit' (and therefore every npm lifecycle script / npx / npm exec).
"""
p = "/root/nodebuild/node-v24.22.1/deps/uv/src/unix/core.c"
s = open(p).read()

old_setfl = """  do
    r = fcntl(fd, F_SETFL, flags);
  while (r == -1 && errno == EINTR);

  if (r)
    return UV__ERR(errno);
"""
new_setfl = """  do
    r = fcntl(fd, F_SETFL, flags);
  while (r == -1 && errno == EINTR);

  /* QNX returns the previous flags on success, not 0. */
  if (r == -1)
    return UV__ERR(errno);
"""
assert s.count(old_setfl) == 1, "F_SETFL site not found"
s = s.replace(old_setfl, new_setfl, 1)

old_setfd = """  do
    r = fcntl(fd, F_SETFD, flags);
  while (r == -1 && errno == EINTR);

  if (r)
    return UV__ERR(errno);
"""
new_setfd = """  do
    r = fcntl(fd, F_SETFD, flags);
  while (r == -1 && errno == EINTR);

  /* QNX returns the previous flags on success, not 0. */
  if (r == -1)
    return UV__ERR(errno);
"""
assert s.count(old_setfd) == 1, "F_SETFD site not found"
s = s.replace(old_setfd, new_setfd, 1)

open(p, "w").write(s)
print("patched core.c")
