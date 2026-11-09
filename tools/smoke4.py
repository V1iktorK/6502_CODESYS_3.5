import asm6502
SRC = """
ORG $0200
start:  LDX #$00
loop:   LDA msg,X
        BEQ done
        STA $F000
        INX
        JMP loop
done:   HLT
msg:    DB $43,$50,$2F,$4D,$20,$4F,$4B,$00
"""
mem, lb = asm6502.assemble(SRC)
print("labels:", {k: "%04X" % v for k, v in lb.items()})
print("bytes:", " ".join("%02X" % mem[a] for a in sorted(mem)))
print("по адресу msg:", "%02X" % mem[lb["msg"]] if lb["msg"] in mem else "нет байта")
print("по адресу done:", "%02X" % mem[lb["done"]] if lb["done"] in mem else "нет байта")
