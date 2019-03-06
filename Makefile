OBJDIR := obj
BINDIR := bin
SRCDIR := src
LDDIR  := ld
TESTDIR:= test

BITS ?= $(shell getconf LONG_BIT)

# -mpreferred-stack-boundary=3 messes up the stack and kills SSE!
# -fno-plt
COPTFLAGS=-Os -fvisibility=hidden -fwhole-program -fno-plt \
  -ffast-math -funsafe-math-optimizations -fno-stack-protector -fomit-frame-pointer \
  -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables
CXXOPTFLAGS=$(COPTFLAGS) \
  -fno-rtti -fno-enforce-eh-specs -fnothrow-opt -fno-use-cxa-get-exception-ptr \
  -fno-implicit-templates -fno-threadsafe-statics -fno-use-cxa-atexit

CFLAGS=-Wall -Wextra -Wpedantic -std=gnu11 -nostartfiles -fno-PIC $(COPTFLAGS)
CXXFLAGS=-Wall -Wextra -Wpedantic -std=c++11 $(CXXOPTFLAGS) -nostartfiles -fno-PIC

ASFLAGS=-I $(SRCDIR)/
ifeq ($(BITS),32)
LDFLAGS=-m elf_i386
ASFLAGS += -f elf32
else
LDFLAGS=-m elf_x86_64
ASFLAGS += -f elf64
endif
LDFLAGS_=$(LDFLAGS) -T $(LDDIR)/link.ld --oformat=binary

CFLAGS   += -m$(BITS) $(shell pkg-config --cflags sdl2)
CXXFLAGS += -m$(BITS) $(shell pkg-config --cflags sdl2)

LIBS=-lc

ASFLAGS += -DUSE_INTERP -DALIGN_STACK -DUSE_DT_DEBUG -DNO_START_ARG

NASM    ?= nasm
PYTHON3 ?= python3

all: $(BINDIR)/hello-crt $(BINDIR)/sdl-crt $(BINDIR)/flag $(BINDIR)/hello-_start

LIBS += $(filter-out -pthread,$(shell pkg-config --libs sdl2)) -lX11 #-lGL

clean:
	@$(RM) -vrf $(OBJDIR) $(BINDIR)

%/:
	@mkdir -vp "$@"

.SECONDARY:

$(OBJDIR)/%.o: $(SRCDIR)/%.c $(OBJDIR)/
	$(CC) $(CFLAGS) -c "$<" -o "$@"
$(OBJDIR)/%.o: $(TESTDIR)/%.c $(OBJDIR)/
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(OBJDIR)/%.start.o: $(OBJDIR)/%.o $(OBJDIR)/crt1.o
	$(LD) $(LDFLAGS) -r -o "$@" $^

$(OBJDIR)/symbols.%.asm: $(OBJDIR)/%.o
	$(PYTHON3) ./smol.py $(SMOLFLAGS) $(LIBS) "$<" "$@"

$(OBJDIR)/stub.%.o: $(OBJDIR)/symbols.%.asm $(SRCDIR)/header32.asm \
        $(SRCDIR)/loader32.asm
	$(NASM) $(ASFLAGS) $< -o $@

$(OBJDIR)/stub.%.start.o: $(OBJDIR)/symbols.%.start.asm $(SRCDIR)/header32.asm \
        $(SRCDIR)/loader32.asm
	$(NASM) $(ASFLAGS) $< -o $@

$(BINDIR)/%: $(OBJDIR)/%.o $(OBJDIR)/stub.%.o $(BINDIR)/
	$(LD) -Map=$(BINDIR)/$*.map $(LDFLAGS_) $(OBJDIR)/$*.o $(OBJDIR)/stub.$*.o -o "$@"

$(BINDIR)/%-crt: $(OBJDIR)/%.start.o $(OBJDIR)/stub.%.start.o $(BINDIR)/
	$(LD) -Map=$(BINDIR)/$*-crt.map $(LDFLAGS_) $(OBJDIR)/$*.start.o $(OBJDIR)/stub.$*.start.o -o "$@"

.PHONY: all clean

