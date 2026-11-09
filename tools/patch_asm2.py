import io
p = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\asm6502.py"
t = io.open(p, encoding="utf-8").read()
old = '''    v = _val(a, labels, 2, lenient)
    if "rel" in tab:'''
new = '''    # Символьная метка ВСЕГДА двухбайтовая (abs), даже если в первом проходе
    # её значение ещё неизвестно: иначе для вперёд-объявленной метки выбирался
    # zp-режим (2 байта вместо 3) и все последующие метки съезжали на байт.
    is_label = re.match(r"^[A-Za-z_]\\w*$", a) is not None
    v = _val(a, labels, 2, lenient)
    if is_label and "abs" in tab and "rel" not in tab:
        return [tab["abs"], v & 0xFF, (v >> 8) & 0xFF]
    if "rel" in tab:'''
assert old in t
t = t.replace(old, new, 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("исправлено")
