import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\opcodes.py"
t = io.open(p, encoding="utf-8").read()
anchor = '    (u"INX", u"imp", 0xE8), (u"DEX", u"imp", 0xCA),'
add = ('    (u"CPX", u"imm", 0xE0), (u"CPX", u"zp", 0xE4), (u"CPX", u"abs", 0xEC),\n'
       '    (u"CPY", u"imm", 0xC0), (u"CPY", u"zp", 0xC4), (u"CPY", u"abs", 0xCC),\n')
assert anchor in t
t = t.replace(anchor, add + anchor, 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("CPX/CPY добавлены в OPCODES")
