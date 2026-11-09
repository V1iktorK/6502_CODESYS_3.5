# -*- coding: utf-8 -*-
import importlib, asm6502
importlib.reload(asm6502)
src = "\n".join([
    "ORG $0200",
    "start:  LDA #$41",
    "        STA $F000",
    "        JMP start",
])
print("SRC:", repr(src))
mem, lb = asm6502.assemble(src)
print("labels:", lb)
print("n bytes:", len(mem))
print("bytes:", " ".join("%02X" % mem[a] for a in sorted(mem)))
