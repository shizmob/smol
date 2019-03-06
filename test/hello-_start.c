#include <stdlib.h>
#include <stdio.h>

const char *f = "foo";

__attribute__((__externally_visible__, __section__(".text.startup._start"),
    __noreturn__
#ifndef __clang__
    , __naked__
#endif
))
int _start(void) {
    puts("Hello World!");//printf("hello world %s\n", f);
    asm volatile("int3");//exit(42);
    __builtin_unreachable();
}

