# -*- coding: utf-8 -*-
"""
patch_polarity_fix.py -- ispravlenie POLYARNOSTI SEL posle opyta.

Ustanovleno eksperimentalno (tools/test_byte.py): v CODESYS
    SEL(G, IN0, IN1)  ->  pri G=TRUE rezultat = IN1, pri G=FALSE = IN0.
Znachit:
  * zapis registra dolzhna byt' SEL(gate, TEKUSCHEE, NOVOE);
  * operand komandy pri imm:        SEL(imm, PAMYAT, OP1);
  * cel' vetvleniya:                SEL(TAKE, PC2, C_REL);
  * PC:                             SEL(TRUE, PC, ps).

Ranne (patch_pol / patch_wire) ya perestavil vhody, schitaya obratnoe, i tem
samoL slomal rabotayuschiy kod. Vozvrashchaem vernyy poryadok.
"""
import io
import ast

GT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
GC = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_cpu_split.py"
G8 = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_step8.py"

# ---------------------------------------------------------------- 1. регистры
t = io.open(GT, "rb").read().decode("utf-8")
old = (u'        # при G=TRUE (запись разрешена) выбирается IN0, поэтоmu IN0 = новое\n'
       u'        sel = s.blk(u"SEL", [(u"G", R(s, gate, 6)), (u"IN0", wr_v),')
     u'\n'
       u'                             (u"IN1", cur_v)], 6)')
new = (u'        # SEL(G, IN0, IN1): pri G=TRUE beretsya IN1 -> IN1 = novoe znachenie\n'
       u'        sel = s.blk(u"SEL", [(u"G", gsrc), (u"IN0", cur_v),\n'
       u'                             (u"IN1", wr_v)], 6)')
if old in t:
    t = t.replace(old, new, 1)
    print(u"регистры: IN0=текущее, IN1=новое")
else:
    # vozmozhno, uzhe est' gsrc v IN0
    old2 = (u'        sel = s.blk(u"SEL", [(u"G", gsrc), (u"IN0", wr_v),\n'
            u'                             (u"IN1", cur_v)], 6)')
    new2 = (u'        sel = s.blk(u"SEL", [(u"G", gsrc), (u"IN0", cur_v),\n'
            u'                             (u"IN1", wr_v)], 6)')
    if old2 in t:
        t = t.replace(old2, new2, 1)
        print(u"регистры: порядок восстановлен (вариант 2)")
    else:
        print(u"НЕ найден блок записи регистров")
io.open(GT, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GT, encoding="utf-8").read())

# ---------------------------------------------------------------- 2. WDATA
t = io.open(GC, "rb").read().decode("utf-8")
old = (u'    # при imm (G=TRUE) нужен OP1, иначе операнд из памяти по EFF\n'
       u'    s.assign(u"WDATA", s.blk(u"SEL", [(u"G", imm), (u"IN0", op1), (u"IN1", mem)], 3), 5)')
new = (u'    # SEL(G, IN0, IN1): pri G=TRUE берётся IN1 -> IN1 = OP1 (режим imm)\n'
       u'    s.assign(u"WDATA", s.blk(u"SEL", [(u"G", imm), (u"IN0", mem), (u"IN1", op1)], 3), 5)')
if old in t:
    t = t.replace(old, new, 1)
    print(u"WDATA: IN1 = OP1")
else:
    print(u"НЕ найден блок WDATA")
io.open(GC, "wb").write(t.encode("utf-8"))
ast.parse(io.open(GC, encoding="utf-8").read())

# ---------------------------------------------------------------- 3. цель перехода
t = io.open(G8, "rb").read().decode("utf-8")
old = (u'    # при G=TRUE (ветвление разрешено) берётся цель перехода\n'
       u'    s.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", crel), (u"IN1", pc2)], 2), 4)')
new = (u'    # SEL(G, IN0, IN1): pri G=TRUE берётся IN1 -> цель перехода\n'
       u'    s.assign(u"OUT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)')
if old in t:
    t = t.replace(old, new, 1)
    print(u"цель перехода: IN1 = C_REL")
else:
    print(u"НЕ найдена цель перехода")
io.open(G8, "wb").write(t.encode("utf-8"))
ast.parse(io.open(G8, encoding="utf-8").read())

print(u"готово")
