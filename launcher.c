// Main executable for Jarvis.app and JarvisListener.app: runs Contents/Resources/run.sh and waits.
// macOS grants the microphone per app binary. A script launcher gets no permission prompt at all;
// a real binary that stays alive as the parent of the Python process does.
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

extern char **environ;

int main(void) {
    char raw[PATH_MAX], exe[PATH_MAX], script[PATH_MAX];
    uint32_t size = sizeof raw;
    if (_NSGetExecutablePath(raw, &size) != 0 || !realpath(raw, exe)) return 1;
    if (snprintf(script, sizeof script, "%s/../Resources/run.sh", dirname(exe)) >= (int)sizeof script) return 1;
    char *argv[] = {"/bin/zsh", script, NULL};
    pid_t pid;
    if (posix_spawn(&pid, "/bin/zsh", NULL, NULL, argv, environ) != 0) return 1;
    int status;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
