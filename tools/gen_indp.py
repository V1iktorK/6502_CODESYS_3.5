# -*- coding: utf-8 -*-
"""gen_indp.py -- stupen SL_INDPA: adres starshego bajta vektora s perenosom.

Na 6502 kosvennyy perehod (JMP ($xxFF)) beret MLADSHIY bajt po $xxFF, a
STARSHIY -- po $xx00 (perenos vnutri stranicy NE proishodit, eto dokumentirovannyy
bag protsessora). Poetomu adres starshego bajta:

    HIA := (PTR AND $FF00) OR ((PTR + 1) AND $00FF)

Vychislyaetsya otdelnoy stupenyu, potomu chto indeks massiva dolzhen byt
PEREMENNOY, a chitat" peremennuyu, zapisannuyu v tom zhe POU, nelzya
(pravilo 2.5 -- vernetsya staroe znachenie).
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


def build():
    s = Sheet(u"SL_INDPA: адрес старшего байта вектора")
    s.add_comment(u"HIA := (PTR AND $FF00) OR ((PTR+1) AND $00FF)")
    ptr = s.ref(u"PTR", 0)
    p1 = s.blk(u"ADD", [(u"IN1", s.ref(u"PTR", 0)),
                        (u"IN2", s.const(u"WORD#1", 1))], 2)
    a1 = s.blk(u"AND", [(u"IN1", s.ref(u"PTR", 0)),
                        (u"IN2", s.const(u"WORD#16#FF00", 2))], 3)
    a2 = s.blk(u"AND", [(u"IN1", p1), (u"IN2", s.const(u"WORD#16#00FF", 3))], 4)
    s.assign(CPU + u".HIA", s.blk(u"OR", [(u"IN1", a1), (u"IN2", a2)], 5), 6)
    return s


def main():
    print(u"=== gen_indp ===")
    x = pou_xml(u"SL_INDPA", u"functionBlock",
                interface(inputs=[(u"PTR", u"WORD")]), [build()],
                comment=u"адрес старшего байта вектора")
    p = os.path.join(OUT, u"SL_INDPA.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_INDPA  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
