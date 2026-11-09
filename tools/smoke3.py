import asm6502
for src in ["ORG $0200\nstart: LDA #$41\n", "start: LDA #$41\n"]:
    mem, lb = asm6502.assemble(src)
    print(repr(src[:20]), "labels:", lb, "addrs:", sorted(mem))
