import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\test_io.py"
t = io.open(p, encoding="utf-8").read()
a = t.index('SRC = """')
b = t.index('"""', a + 10) + 3
prog = ('SRC = """\nORG $0200\nstart:  LDX #$00\n'
        'loop:   LDA msg,X\n        BEQ done\n        STA $F000\n'
        '        INX\n        JMP loop\ndone:   HLT\n'
        'msg:    DB $43,$50,$2F,$4D,$20,$4F,$4B,$00\n"""')
t = t[:a] + prog + t[b:]
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("программа с циклом восстановлена")
