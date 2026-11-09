import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\test_branch.py"
t = io.open(p, encoding="utf-8").read()
a = t.index('SRC = """')
b = t.index('"""', a + 10) + 3
prog = ('SRC = """\nORG $0200\n        LDA #$55\n        JMP next\n'
        '        LDA #$AA\nnext:   STA $0300\n        HLT\n"""')
t = t[:a] + prog + t[b:]
t = t.replace('log(u"Mem[0300] = %s (ожидалось 5)" % v)', 'log(u"Mem[0300] = %s (ожидалось 55)" % v)')
t = t.replace('log(u"T-BRANCH: %s" % (u"PASS" if v == 5 else u"FAIL"))',
              'log(u"T-JMP: %s" % (u"PASS" if v == 0x55 else u"FAIL"))')
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("тест JMP")
