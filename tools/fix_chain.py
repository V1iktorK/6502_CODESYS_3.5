import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\build_full.py"
t = io.open(p, encoding="utf-8").read()
bad = ' (u"Chain9", u"BOOL"), (u"Chain10", u"BOOL"), (u"Chain11", u"BOOL"), (u"Chain12", u"BOOL"), (u"Chain13", u"BOOL"), (u"Chain14", u"BOOL")]'
assert bad in t, "хвост не найден"
t = t.replace(bad, ']', 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("хвост убран")
