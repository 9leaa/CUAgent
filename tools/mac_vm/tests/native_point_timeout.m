// Exercise the actual production timeout handler without accessing any desktop.
#define main diagnostic_main
#include "../native_point_probe.m"
#undef main
int main(void) {
    signal(SIGALRM, deadline);
    alarm(3);
    for (;;) pause();
}
