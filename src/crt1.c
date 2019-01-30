
#include <stddef.h>

extern int main(int argc, char* argv[]);
extern int __libc_start_main(int (*main)(int, char**),
        int argc, char** argv,
        void (*init)(void), void(*fini)(void),
        void (*rtld_fini)(void),
        void* stack) __attribute__((__noreturn__));

__attribute__((__externally_visible__, __section__(".text.startup._start"),
            __noreturn__))
int _start(void* stack) {
    // TODO: _dl_fini etc.
    int argc=*(size_t*)stack;
    char** argv=(void*)(&((size_t*)stack)[1]);

    __libc_start_main(main, argc, argv, NULL, NULL, NULL, (void*)stack);

    __builtin_unreachable();
}

