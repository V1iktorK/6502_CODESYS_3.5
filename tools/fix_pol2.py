# -*- coding: utf-8 -*-
"""fix_pol2.py -- prostye odnostrochnye zameny polyarnosti SEL."""
import io
import ast

GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
GC = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_cpu_split.py"
G8 = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_step8.py"

# 1) регистры: IN0 = текущее, IN1 = новое
t = io.open(GT, "rb").read().decode("utf-8")
a = u'        sel = s.blk(u"SEL", [(u"G", gsrc), (u"IN0", wr_v),'
b = u'        sel = s.blk(u"SEL", [(u"G", gsrc), (u"IN0", cur_v),'
c = u'                             (u"IN1", cur_v)], 6)'
d = u'                             (u"IN1", wr_v)], 6)'
n = 0
if a in t:
    t = t.replace(a, b, 1)
    n += 1
if c in t:
    t = t.replace(c, d, 1)
    n += 1
io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())
print(u"gen_top3: замен %d" % n)

# 2) WDATA: IN1 = OP1
t = io.open(GC, "rb").read().decode("utf-8")
a = u's.assign(u"WDATA", s.blk(u"SEL", [(u"G", imm), (u"IN0", op1), (u"IN1", mem)], 3), 5)'
b = u's.assign(u"WDATA", s.blk(u"SEL", [(u"G", imm), (u"IN0", mem), (u"IN1", op1)], 3), 5)'
print(u"gen_cpu_split WDATA: %s" % (u"заменено" if a in t else u"НЕ найдено"))
t = t.replace(a, b, 1)
io.open(GC, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GC, encoding="utf-8").read())

# 3) цель перехода: IN1 = C_REL
t = io.open(G8, "rb").read().decode("utf-8")
a = u's.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", crel), (u"IN1", pc2)], 2), 4)'
b = u's.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)'
print(u"gen_step8 BRN2: %s" % (u"заменено" if a in t else u"НЕ найдено"))
t = t.replace(a, b, 1)
io.open(G8, "wb").write(t.encode("utf-8"))
ast.parse(io.open(G8, encoding="utf-8").read())
print(u"готово")
