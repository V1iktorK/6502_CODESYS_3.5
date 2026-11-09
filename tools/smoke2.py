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
print("labels:", lb)
print("n:", len(mem))
for line in asm6502.to_hex(mem):
    print(line)
