
#include <stddef.h>

extern int main(int argc, char* argv[]);

extern int __libc_start_main(int (*main)(int, char**),
        int argc, char** argv,
        void (*init)(void), void(*fini)(void),
        void (*rtld_fini)(void),
        void* stack) __attribute__((__noreturn__));

__attribute__((__externally_visible__, __section__(".text.startup._start"),
            __noreturn__, __used__
#ifdef __x86_64__
        , __naked__
#endif
))
int _start(void* stack) {
    // TODO: _dl_fini etc.
    int argc=*(size_t*)stack;
    char** argv=(void*)(&((size_t*)stack)[1]);

// avoid problems when -fno-plt is enabled
#ifdef __x86_64__
    asm volatile("xor  %%ecx, %%ecx\n"
                 "push %%rcx\n"
                 "push %%rcx\n"
                 "pop  %%r8\n"
                 "pop  %%r9\n"
                 "call *__libc_start_main@GOTPCREL(%%rip)\n"
            :
            :"S"(argc), "D" (main), "d" (argv)
            :);
#else
    __libc_start_main(main, argc, argv, NULL, NULL, NULL, (void*)stack);
#endif

    __builtin_unreachable();
}

