# -*- coding: utf-8 -*-
"""
gen_prep.py -- stupen SL_PREP: signaly deshifratora i razresheniya takta.

Pochemu otdelnyy POU: v liste yadra FB_CPU_Core eti velichiny zapisyvalis'
obychnymi prisvoeniyami, a sleduyuschie sloi (FB_CPU_Store i dr.) chitali ih
v TOM ZHE skane. CODESYS ne garantiruet, chto prisvoeniya vypolnyatsya ran'she
vyzovov blokov, poetoму sloi videli znacheniya proshlogo skana: naprimer
SP_MODE=0, iz-za chego v stek ne popadalo nichego.

Zdes vse velichiny schitayutsya iz tablits (GVL_TABLE), kotorye zapisal
deshifrator (predyduschiy POU), i vydayutsya v GVL dlya posleduyuschih sloev.

    ADDR_MODE..COND := GVL_TABLE.<sig>[OPs]
    SP_MODE         := Enable ? GVL_TABLE.SP_MODE[OPs] : 0
    LD_*_E, WR_MEM_E:= LD_* AND Enable
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
CPU = u"GVL_CPU"
TBL = u"GVL_TABLE"

BYTE_SIG = (u"ADDR_MODE", u"LEN", u"SRC", u"ALU_A", u"ALU_B",
            u"PC_MODE", u"COND")
GATES = (u"LD_A", u"LD_X", u"LD_Y", u"LD_P", u"LD_SP", u"WR_MEM")


def build():
    s = Sheet(u"SL_PREP: сигналы дешифратора и разрешения такта")
    s.add_comment(u"Байтовые сигналы — из таблиц GVL_TABLE по коду операции OPs")
    en = s.ref(u"Enable", 0)
    ops = s.ref(CPU + u".OPs", 0)
    col = 1
    for sig in BYTE_SIG:
        s.assign(CPU + u"." + sig,
                 s.ref(u"%s.%s[%s.OPs]" % (TBL, sig, CPU), col), col + 1)
        col += 2
    # SP_MODE обнуляется, когда такт не разрешён: иначе стек продолжал бы
    # толкаться каждый скан (SP_MODE не зависит от PC).
    s.assign(CPU + u".SP_MODE",
             s.blk(u"SEL", [(u"G", s.ref(u"Enable", 1)),
                            (u"IN0", s.const(u"BYTE#0", 1)),
                            (u"IN1", s.ref(u"%s.SP_MODE[%s.OPs]" % (TBL, CPU), 2))], 3), 4)
    for sig in GATES:
        s.assign(CPU + u"." + sig + u"_E",
                 s.blk(u"AND", [(u"IN1", s.ref(CPU + u"." + sig, col)),
                                (u"IN2", s.ref(u"Enable", col))], col + 1), col + 2)
        col += 2
    return s


def main():
    print(u"=== gen_prep ===")
    x = pou_xml(u"SL_PREP", u"functionBlock",
                interface(inputs=[(u"Enable", u"BOOL")]), [build()],
                comment=u"сигналы дешифратора")
    p = os.path.join(OUT, u"SL_PREP.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_PREP  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
