import sys

p = "/root/nodebuild/node-v24.22.1/deps/uv/src/unix/process.c"
src = open(p).read()

helper = r'''
#include <stdio.h>
static void uvdbg(const char *m, long a, long b) {
  int fd = open("/tmp/uvdbg.log", O_WRONLY | O_APPEND | O_CREAT, 0666);
  if (fd >= 0) {
    char buf[256];
    int n = snprintf(buf, sizeof(buf), "%s a=%ld b=%ld errno=%d\n", m, a, b, errno);
    if (n > 0) (void) write(fd, buf, (size_t) n);
    close(fd);
  }
}

static int uv__process_init_stdio('''
anchor = "static int uv__process_init_stdio("
assert src.count(anchor) == 1
src = src.replace(anchor, helper, 1)

# a) child start
old = """  sigset_t signewset;
  int close_fd;
  int use_fd;
  int fd;
  int n;
"""
assert src.count(old) == 1
src = src.replace(old, old + '  uvdbg("child_start", stdio_count, error_fd);\n', 1)

# b) after signal reset loop
old = """  if (options->flags & UV_PROCESS_DETACHED)
    setsid();
"""
assert src.count(old) == 1
src = src.replace(old, '  uvdbg("sig_done", n, 0);\n' + old, 1)

# c) fd loop marker
old = """    close_fd = -1;
    use_fd = pipes[fd][1];
"""
assert src.count(old) == 1
src = src.replace(old, old + '    uvdbg("fd_loop", fd, use_fd);\n', 1)

# d) cloexec markers
old = """      if (close_fd == -1) {
        n = uv__cloexec(use_fd, 0);
        if (n)
          uv__write_int(error_fd, n);
      }
"""
assert src.count(old) == 1
new = """      if (close_fd == -1) {
        uvdbg("cloexec_pre", use_fd, 0);
        n = uv__cloexec(use_fd, 0);
        uvdbg("cloexec_post", n, errno);
        if (n)
          uv__write_int(error_fd, n);
      }
"""
src = src.replace(old, new, 1)

# e) chdir markers
old = """  if (options->cwd != NULL && chdir(options->cwd))
    uv__write_errno(error_fd);
"""
assert src.count(old) == 1
new = """  uvdbg("pre_chdir", 0, 0);
  if (options->cwd != NULL && chdir(options->cwd)) {
    uvdbg("chdir_fail", 0, errno);
    uv__write_errno(error_fd);
  }
"""
src = src.replace(old, new, 1)

# f) exec markers
old = """#ifdef __MVS__
  execvpe(options->file, options->args, environ);
#else
  execvp(options->file, options->args);
#endif

  uv__write_errno(error_fd);
"""
assert src.count(old) == 1
new = """  uvdbg("pre_exec", 0, 0);
#ifdef __MVS__
  execvpe(options->file, options->args, environ);
#else
  execvp(options->file, options->args);
#endif

  uvdbg("exec_fail", 0, errno);
  uv__write_errno(error_fd);
"""
src = src.replace(old, new, 1)

# g) parent return marker
old = """  uv__close_nocheckstdio(signal_pipe[0]);

  return err;
"""
assert src.count(old) == 1
src = src.replace(old, '  uv__close_nocheckstdio(signal_pipe[0]);\n  uvdbg("spawn_ret", err, 0);\n\n  return err;\n', 1)

open(p, "w").write(src)
print("patched", p)
