import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\test_io.py"
t = io.open(p, encoding="utf-8").read()
a = t.index('SRC = """')
b = t.index('"""', a + 10) + 3
t = t[:a] + 'SRC = """\nORG $0200\n        LDA #$41\n        STA $F000\n        HLT\n"""' + t[b:]
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("программа: A -> окно -> HLT")
