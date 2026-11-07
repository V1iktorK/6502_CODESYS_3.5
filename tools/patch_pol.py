# -*- coding: utf-8 -*-
"""
patch_pol.py -- ispravit POLYARNOST vybora pri zapisi registrov.

`SEL(G, IN0, IN1)` pri G=TRUE beret IN0. V zapisi registrov stoяlo
    SEL(LD_A_E,  A,       REG_WR)
to est pri razreshenii zapisi (LD_A_E=TRUE) vybiralos STAROE znachenie A,
i registr ne menjalsya nikogda. Pravilno:
    SEL(LD_A_E,  REG_WR,  A)        -- pri razreshenii berem REG_WR
To zhe dlya X, Y, P, SP, PC.
"""
import io, ast

P = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502\tools\gen_top3.py"
t = io.open(P, "rb").read().decode("utf-8")

old = (u'        sel = s.blk(u"SEL", [(u"G", R(s, gate, 6)), (u"IN0", cur_v),\n'
       u'                             (u"IN1", wr_v)], 6)')
new = (u'        # при G=TRUE (запись разрешена) выбирается IN0, поэтоmu IN0 = новое\n'
       u'        sel = s.blk(u"SEL", [(u"G", R(s, gate, 6)), (u"IN0", wr_v),\n'
       u'                             (u"IN1", cur_v)], 6)')
if old in t:
    t = t.replace(old, new, 1)
    print(u"полярность записи регистров исправлена")
else:
    print(u"НЕ найден блок записи регистров")

# WDATA: dlya rezhima imm nuzhen operand iz OP1
old2 = (u'    call(s, u"SL_WDATA2", u"Wd",\n'
        u'         [(u"ADDR_MODE", R(s, u"ADDR_MODE")), (u"EFF", R(s, u"EFF")),\n'
        u'          (u"OP1", R(s, u"OP1"))], 3, w=120)')
new2 = (u'    call(s, u"SL_WDATA2", u"Wd",\n'
        u'         [(u"ADDR_MODE", R(s, u"ADDR_MODE")), (u"EFF", R(s, u"EFF")),\n'
        u'          (u"OP1", R(s, u"OP1"))], 3, w=120)\n'
        u'    # (SL_WDATA2 dlya imm bеret OP1 -- sm. shapku modulya)')
if old2 in t:
    t = t.replace(old2, new2, 1)
    print(u"комментарий к WDATA добавлен")

io.open(P, "wb").write(t.encode("utf-8"))
ast.parse(io.open(P, encoding="utf-8").read())
print(u"синтаксис OK")
