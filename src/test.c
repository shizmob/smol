#include <stdlib.h>
#include <stdio.h>

const char *f = "foo";

__attribute__((__externally_visible__, __section__(".text._start"), __noreturn__))
int _start(void) {
    printf("hello world %s\n", f);
    exit(42);
    __builtin_unreachable();
}
