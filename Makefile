OBJDIR := obj
BINDIR := bin
SRCDIR := rt
TESTDIR:= test

NASM ?= nasm
OBJCOPY ?= objcopy

BITS ?= $(shell getconf LONG_BIT)

# -mpreferred-stack-boundary=3 messes up the stack and kills SSE!
#COPTFLAGS=-Os -fvisibility=hidden -fwhole-program -fno-plt \
#  -ffast-math -funsafe-math-optimizations -fno-stack-protector -fomit-frame-pointer \
#  -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables

COPTFLAGS=-Os -fno-plt -fno-stack-protector -fno-stack-check -fno-unwind-tables \
  -fno-asynchronous-unwind-tables -fomit-frame-pointer -ffast-math -no-pie \
  -fno-pic -fno-PIE -ffunction-sections -fdata-sections -fno-plt \
  -fmerge-all-constants -mno-fancy-math-387 -mno-ieee-fp
CXXOPTFLAGS=$(COPTFLAGS) -fno-exceptions \
  -fno-rtti -fno-enforce-eh-specs -fnothrow-opt -fno-use-cxa-get-exception-ptr \
  -fno-implicit-templates -fno-threadsafe-statics -fno-use-cxa-atexit

CFLAGS=-g -Wall -Wextra -Wpedantic -std=gnu11 -nostartfiles -fno-PIC $(COPTFLAGS) #-DUSE_DL_FINI
CXXFLAGS=-g -Wall -Wextra -Wpedantic -std=c++11 $(CXXOPTFLAGS) -nostartfiles -fno-PIC

CFLAGS   += -m$(BITS) $(shell pkg-config --cflags sdl2)
CXXFLAGS += -m$(BITS) $(shell pkg-config --cflags sdl2)

ifeq ($(BITS),32)
# I think prescott is basically nocona but 32-bit only, althought I'm not sure
# if this one is optimal
CFLAGS += -march=prescott
else
# I've heard nocona gets slightly smaller binaries than core2
CFLAGS += -march=nocona
endif

LIBS = $(filter-out -pthread,$(shell pkg-config --libs sdl2)) -lX11 -lm -lc #-lGL

PWD ?= .

SMOLFLAGS = --smolrt "$(PWD)/rt" --smolld "$(PWD)/ld" \
    --verbose -g #--keeptmp
# -fuse-dnload-loader -fskip-zero-value -fuse-nx -fskip-entries -fuse-dt-debug
# -fuse-dl-fini -fno-start-arg -funsafe-dynamic

PYTHON3 ?= python3

all: $(BINDIR)/hello-crt $(BINDIR)/sdl-crt $(BINDIR)/flag $(BINDIR)/hello-_start

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

$(BINDIR)/%.dbg $(BINDIR)/%: $(OBJDIR)/%.o $(BINDIR)/
	$(PYTHON3) ./smold.py --debugout "$@.dbg" $(SMOLFLAGS) --ldflags=-Wl,-Map=$(BINDIR)/$*.map $(LIBS) "$<" "$@"
	$(PYTHON3) ./smoltrunc.py "$@" "$(OBJDIR)/$(notdir $@)" && mv "$(OBJDIR)/$(notdir $@)" "$@" && chmod +x "$@"

$(BINDIR)/%-crt.dbg $(BINDIR)/%-crt: $(OBJDIR)/%.lto.o $(OBJDIR)/crt1.lto.o $(BINDIR)/
	$(PYTHON3) ./smold.py --debugout "$@.dbg" $(SMOLFLAGS) --ldflags=-Wl,-Map=$(BINDIR)/$*-crt.map $(LIBS) "$<" $(OBJDIR)/crt1.lto.o "$@"
	$(PYTHON3) ./smoltrunc.py "$@" "$(OBJDIR)/$(notdir $@)" && mv "$(OBJDIR)/$(notdir $@)" "$@" && chmod +x "$@"

.PHONY: all clean

