import io, re
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(p, encoding="utf-8").read()
n = len(re.findall(r"\n        s\.assign\(u\"GVL_CPU\.WRS%d\" % k, ch, col \+ 1\)", t))
t = re.sub(r"\n        s\.assign\(u\"GVL_CPU\.WRS%d\" % k, ch, col \+ 1\)", "", t)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("удалено лишних чтений WRS: %d" % n)
