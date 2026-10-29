/* Root display-service helper: put only VT1 in graphics/text mode. */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/kd.h>
#include <linux/vt.h>
int main(int argc, char **argv)
{
	if (argc != 2 ||
	    (strcmp(argv[1], "graphics") && strcmp(argv[1], "text")))
		return 2;
	alarm(5);
	int fd = open("/dev/tty1", O_RDWR | O_NOCTTY | O_CLOEXEC);
	if (fd < 0) {
		perror("tty1");
		return 1;
	}
	int mode = !strcmp(argv[1], "graphics") ? KD_GRAPHICS : KD_TEXT;
	if (ioctl(fd, VT_ACTIVATE, 1) < 0 || ioctl(fd, VT_WAITACTIVE, 1) < 0 ||
	    ioctl(fd, KDSETMODE, mode) < 0) {
		perror("VT1");
		close(fd);
		return 1;
	}
	close(fd);
	return 0;
}
