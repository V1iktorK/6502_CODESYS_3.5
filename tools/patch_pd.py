# -*- coding: utf-8 -*-
"""patch_pd.py -- ispravit format-stroku v patch_decoder.py."""
import io, ast

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\patch_decoder.py"
t = io.open(P, "rb").read().decode("utf-8")
old = (u"            % (new_id, 20000 + 40 * len(added), 20000 + 40 * len(added)))")
new = (u"            % (new_id, 20000 + 40 * len(added), 20000 + 40 * len(added), sig))")
if old in t:
    t = t.replace(old, new)
    io.open(P, "wb").write(t.encode("utf-8"))
    print(u"исправлено")
else:
    print(u"НЕ найдено")
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис OK")
