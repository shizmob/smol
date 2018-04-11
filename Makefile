LDRDIR = ldr
OBJDIR = obj
BINDIR = bin
SRCDIR = src
DATADIR = data

COPTFLAGS=-Os -fvisibility=hidden -mpreferred-stack-boundary=2 -fwhole-program \
  -ffast-math -funsafe-math-optimizations -fno-stack-protector -fomit-frame-pointer \
  -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables
CXXOPTFLAGS=$(COPTFLAGS) \
  -fno-rtti -fno-enforce-eh-specs -fnothrow-opt -fno-use-cxa-get-exception-ptr \
  -fno-implicit-templates -fno-threadsafe-statics -fno-use-cxa-atexit

ASFLAGS=-f elf -I $(LDRDIR)/
CFLAGS=-Wall -Wextra -Wpedantic -std=c99 $(COPTFLAGS) -nostartfiles -fno-PIC
CXXFLAGS=-Wall -Wextra -Wpedantic -std=c++11 $(CXXOPTFLAGS) -nostartfiles -fno-PIC
LIBS=-lGL -ldl -lc
LDFLAGS=--oformat=binary -T ldr/link.ld


.PHONY: all
all: $(BINDIR)/test

.PHONY: clean
clean:
	rm -rf $(OBJDIR)/* $(BINDIR)/*


.SECONDARY:

$(OBJDIR)/%.o: $(SRCDIR)/%.c
	$(CC) $(CFLAGS) -c $^ -o $@

$(OBJDIR)/%.o.syms: $(OBJDIR)/%.o
	readelf -s $^ | grep UND | sed 1d | awk '{ print $$8 }' > $@

$(OBJDIR)/symbols.%.s: $(OBJDIR)/%.o.syms
	$(LDRDIR)/mksyms $(LIBS) $$(cat $^) > $@

$(OBJDIR)/header.%.o: $(OBJDIR)/symbols.%.s $(LDRDIR)/header.s $(LDRDIR)/loader.s
	nasm $(ASFLAGS) $< -o $@

$(BINDIR)/%: $(OBJDIR)/%.o $(OBJDIR)/header.%.o
	$(LD) $(LDFLAGS) $^ -o $@
