OBJDIR := obj
BINDIR := bin
SRCDIR := rt
PYDIR  := src
LDDIR  := ld
TESTDIR:= test

BITS ?= $(shell getconf LONG_BIT)

# -mpreferred-stack-boundary=3 messes up the stack and kills SSE!
#COPTFLAGS=-Os -fvisibility=hidden -fwhole-program -fno-plt \
#  -ffast-math -funsafe-math-optimizations -fno-stack-protector -fomit-frame-pointer \
#  -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables

COPTFLAGS=-Os -fno-plt -fno-stack-protector -fno-stack-check -fno-unwind-tables \
  -fno-asynchronous-unwind-tables -fomit-frame-pointer -ffast-math -no-pie \
  -fno-pic -fno-PIE -m64 -march=core2 -ffunction-sections -fdata-sections -fno-plt
CXXOPTFLAGS=$(COPTFLAGS) -fno-exceptions \
  -fno-rtti -fno-enforce-eh-specs -fnothrow-opt -fno-use-cxa-get-exception-ptr \
  -fno-implicit-templates -fno-threadsafe-statics -fno-use-cxa-atexit

CFLAGS=-Wall -Wextra -Wpedantic -std=gnu11 -nostartfiles -fno-PIC $(COPTFLAGS) #-DUSE_DL_FINI
CXXFLAGS=-Wall -Wextra -Wpedantic -std=c++11 $(CXXOPTFLAGS) -nostartfiles -fno-PIC

ASFLAGS=-I $(SRCDIR)/
LDFLAGS_ :=
ifeq ($(BITS),32)
LDFLAGS += -m32
ASFLAGS += -f elf32
LDFLAGS_ := -m32
else
LDFLAGS += -m64
ASFLAGS += -f elf64
LDFLAGS_ := -m64
endif
LDFLAGS += -nostartfiles -nostdlib
LDFLAGS_ := $(LDFLAGS_) -T $(LDDIR)/link.ld -Wl,--oformat=binary $(LDFLAGS)

CFLAGS   += -m$(BITS) $(shell pkg-config --cflags sdl2)
CXXFLAGS += -m$(BITS) $(shell pkg-config --cflags sdl2)

LIBS=-lc

SMOLFLAGS +=
ASFLAGS   += -DUSE_INTERP -DNO_START_ARG -DUNSAFE_DYNAMIC -DUSE_DNLOAD_LOADER #-DALIGN_STACK
#-DUSE_DNLOAD_LOADER #-DUSE_DT_DEBUG #-DUSE_DL_FINI #-DNO_START_ARG #-DUNSAFE_DYNAMIC

NASM    ?= nasm
PYTHON3 ?= python3

all: $(BINDIR)/hello-crt $(BINDIR)/sdl-crt $(BINDIR)/flag $(BINDIR)/hello-_start

LIBS += $(filter-out -pthread,$(shell pkg-config --libs sdl2)) -lX11 #-lGL

clean:
	@$(RM) -vrf $(OBJDIR) $(BINDIR)

%/:
	@mkdir -vp "$@"

.SECONDARY:

$(OBJDIR)/%.lto.o: $(SRCDIR)/%.c $(OBJDIR)/
	$(CC) -flto $(CFLAGS) -c "$<" -o "$@"
$(OBJDIR)/%.lto.o: $(TESTDIR)/%.c $(OBJDIR)/
	$(CC) -flto $(CFLAGS) -c "$<" -o "$@"

$(OBJDIR)/%.o: $(SRCDIR)/%.c $(OBJDIR)/
	$(CC) $(CFLAGS) -c "$<" -o "$@"
$(OBJDIR)/%.o: $(TESTDIR)/%.c $(OBJDIR)/
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(OBJDIR)/%.start.o: $(OBJDIR)/%.lto.o $(OBJDIR)/crt1.lto.o
	$(CC) $(LDFLAGS) -r -o "$@" $^

$(OBJDIR)/symbols.%.asm: $(OBJDIR)/%.o
	$(PYTHON3) $(PYDIR)/smol.py $(SMOLFLAGS) $(LIBS) "$<" "$@"

$(OBJDIR)/stub.%.o: $(OBJDIR)/symbols.%.asm $(SRCDIR)/header32.asm \
        $(SRCDIR)/loader32.asm
	$(NASM) $(ASFLAGS) $< -o $@

$(OBJDIR)/stub.%.start.o: $(OBJDIR)/symbols.%.start.asm $(SRCDIR)/header32.asm \
        $(SRCDIR)/loader32.asm
	$(NASM) $(ASFLAGS) $< -o $@

$(BINDIR)/%: $(OBJDIR)/%.o $(OBJDIR)/stub.%.o $(BINDIR)/
	$(CC) -Wl,-Map=$(BINDIR)/$*.map $(LDFLAGS_) $(OBJDIR)/$*.o $(OBJDIR)/stub.$*.o -o "$@"
	./rmtrailzero.py "$@" "$(OBJDIR)/$(notdir $@)" && mv "$(OBJDIR)/$(notdir $@)" "$@" && chmod +x "$@"

$(BINDIR)/%-crt: $(OBJDIR)/%.start.o $(OBJDIR)/stub.%.start.o $(BINDIR)/
	$(CC) -Wl,-Map=$(BINDIR)/$*-crt.map $(LDFLAGS_) $(OBJDIR)/$*.start.o $(OBJDIR)/stub.$*.start.o -o "$@"

.PHONY: all clean

