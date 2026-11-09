# -*- coding: utf-8 -*-
"""gen_indw.py -- stupen SL_INDW: apparatnyy bag stranicy dlya JMP ($xxFF).

Na 6502 pri kosvennom perehode cherez adres s mladshim bajtom $FF starshiy
bajt vektora beretsya po $xx00 (perenos vnutri stranicy NE proishodit).

    esli (C_ABS AND $FF) = $FF  ->  C_IND := Mem[C_ABS] + Mem[C_ABS AND $FF00]*256

Vygodnoe mesto: sLOY FB_CPU_Select (vsego dva vyzova). On idet POSLE sloya
adresacii (tam uzhe est C_ABS) i DO selektora EFF (kotoryy chitaet C_IND),
poetoму novaya POU ne rasshiryaet ni yadro, ni slozhnuyu cepochku adresacii --
imenno takie rasshireniya davali regressiyu.
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
MEM = u"GVL_MEM"


def build():
    s = Sheet(u"SL_INDW: страничный перенос вектора")
    s.add_comment(u"для JMP ($xxFF) старший байт берётся из $xx00")
    wrap = s.blk(u"EQ", [(u"IN1", s.blk(u"AND", [(u"IN1", s.ref(CPU + u".C_ABS", 0)),
                                                 (u"IN2", s.const(u"WORD#16#00FF", 1))], 1)),
                         (u"IN2", s.const(u"WORD#16#00FF", 1))], 2)
    s.assign(u"PAGEW", s.blk(u"AND", [(u"IN1", s.ref(CPU + u".C_ABS", 2)),
                                      (u"IN2", s.const(u"WORD#16#FF00", 2))], 3), 4)
    lo = s.ref(u"%s.Mem[C_ABS]" % MEM, 4)
    hi = s.ref(u"%s.Mem[PAGEW]" % MEM, 4)
    v = s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 6, width=110)
    s.assign(CPU + u".C_IND",
             s.blk(u"SEL", [(u"G", wrap), (u"IN0", s.ref(CPU + u".C_IND", 6)),
                            (u"IN1", v)], 8), 9)
    return s


def main():
    print(u"=== gen_indw ===")
    x = pou_xml(u"SL_INDW", u"functionBlock", interface(locals_=[(u"PAGEW", u"WORD")]),
                [build()], comment=u"страничный перенос")
    p = os.path.join(OUT, u"SL_INDW.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_INDW  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
