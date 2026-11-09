import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\asm6502.py"
t = io.open(p, encoding="utf-8").read()
old = '''        if v < 0x100:
            key = "zpx" if reg == "X" else "zpy"
            if key in tab:
                return [tab[key], v]'''
new = '''        base_is_label = re.match(r"^[A-Za-z_]\\w*$", base) is not None
        if v < 0x100 and not base_is_label:
            key = "zpx" if reg == "X" else "zpy"
            if key in tab:
                return [tab[key], v]'''
assert old in t
t = t.replace(old, new, 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("исправлено (,X-ветка)")
