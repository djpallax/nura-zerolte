/* KWin NoopSession opens DRM without O_NONBLOCK. An event consumed by another
 * reader can leave drmHandleEvent blocking the GUI thread. Limit this pilot
 * adapter to the explicit KMS path; normal kernel permissions still apply.
 * Apply to KWin only: remove LD_PRELOAD before it launches child processes.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
#undef open64
#undef openat64
__attribute__((constructor)) static void s6_init(void)
{
	unsetenv("LD_PRELOAD");
}
static int s6_flags(const char *path, int flags)
{
	if (path && !strcmp(path, "/dev/dri/card0"))
		return flags | O_NONBLOCK;
	return flags;
}
static int s6_mode_needed(int flags)
{
	return (flags & O_CREAT) || ((flags & O_TMPFILE) == O_TMPFILE);
}
int open(const char *path, int flags, ...)
{
	mode_t mode = 0;
	if (s6_mode_needed(flags)) {
		va_list ap;
		va_start(ap, flags);
		mode = va_arg(ap, mode_t);
		va_end(ap);
	}
	return syscall(SYS_openat, AT_FDCWD, path, s6_flags(path, flags), mode);
}
int openat(int dirfd, const char *path, int flags, ...)
{
	mode_t mode = 0;
	if (s6_mode_needed(flags)) {
		va_list ap;
		va_start(ap, flags);
		mode = va_arg(ap, mode_t);
		va_end(ap);
	}
	return syscall(SYS_openat, dirfd, path, s6_flags(path, flags), mode);
}
int open64(const char *path, int flags, ...) __attribute__((alias("open")));
int openat64(int dirfd, const char *path, int flags, ...)
	__attribute__((alias("openat")));
