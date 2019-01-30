
#include <stdlib.h>
#include <stdio.h>

const char *f = "foo";

int main(int argc, char* argv[]) {
    printf("hello world %s\n", f);
    printf("argc=%d\n", argc);
    printf("argv=%p\n", (void*)argv);
    for (int i = 0; i < argc; ++i)
        printf("argv[%d](%p)=%s\n", i, (void*)argv[i], argv[i]);
    exit(42);
}

