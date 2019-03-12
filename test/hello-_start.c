#include <stdlib.h>
#include <stdio.h>

/*__attribute__((__section__(".rodata.hello-_start$f")))
static const char *f = "foo";*/

__attribute__((__externally_visible__, __section__(".text.startup._start"),
    __noreturn__
#ifndef __clang__
    , __naked__
#endif
))
int _start(void) {
    //printf("hello world %s\n", f);
    puts("Hello World!");
    asm volatile("int3");//exit(42);
    __builtin_unreachable();
}

