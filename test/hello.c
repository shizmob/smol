
#include <stdlib.h>
#include <stdio.h>

const char *f = "foo";

int main(int argc, char* argv[]) {
    printf("hello world %s\n", f);
    printf("argc=%d\n", argc);
    for (int i = 0; i < argc; ++i) printf("argv[%d]=%s\n", i, argv[i]);
    exit(42);
}

