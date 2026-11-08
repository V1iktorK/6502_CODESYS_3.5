# -*- coding: utf-8 -*-
"""
gen_snap.py -- stupen SL_SNAPSHOT: snimok signalov POSLEDNEGO vypolnennogo takta.

Zachem: posle ostановки yadro pereschityvaet signaly kazhdyy skan, i nayti
znacheniya, kotorye byli V MOMENT komandy, cherez vneshniy opros nevozmozhno.
Stupen v konce kazhdogo takta (kogda Enable=TRUE) perenositsya vse vazhnye
signaly v GVL_CPU.LAST_*, a pri ostanovke oni SOHRANYAYUTSYA.

Eto zhe nuzhno paneli operat: «poslednyaya komanda» -- kod operacii, adres,
chto zapisano v pamyat' i t.d.

    LAST_x := Enable ? x : LAST_x
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

FIELDS = [(u"OPs", u"BYTE"), (u"SP_MODE", u"BYTE"), (u"SRC", u"BYTE"),
          (u"IS_JSR", u"BOOL"), (u"REG_WR", u"BYTE"), (u"WRD0", u"BYTE"),
          (u"WR0", u"WORD"), (u"WR_EN0", u"BOOL"), (u"EFF", u"WORD"),
          (u"P_NEW", u"BYTE"), (u"ALU_R", u"BYTE"), (u"PC", u"WORD")]


def build():
    s = Sheet(u"SL_SNAPSHOT: снимок последнего такта")
    s.add_comment(u"LAST_x := Enable ? x : LAST_x")
    # Сначала сдвигаем историю: PREV := LAST (это такт, который был до текущего).
    for k, (nm, typ) in enumerate(FIELDS):
        col = 1 + k
        s.assign(CPU + u".PREV_" + nm, s.ref(CPU + u".LAST_" + nm, 1), col)
    for k, (nm, typ) in enumerate(FIELDS):
        col = 1 + k
        s.assign(CPU + u".LAST_" + nm,
                 s.blk(u"SEL", [(u"G", s.ref(CPU + u".Enable", 0)),
                                (u"IN0", s.ref(CPU + u".LAST_" + nm, 1)),
                                (u"IN1", s.ref(CPU + u"." + nm, 1))], col), col + 1)
    return s


def main():
    print(u"=== gen_snap ===")
    x = pou_xml(u"SL_SNAPSHOT", u"functionBlock", interface(), [build()],
                comment=u"снимок такта")
    p = os.path.join(OUT, u"SL_SNAPSHOT.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_SNAPSHOT  %8d байт" % os.path.getsize(p))
    print(u"поля: %s" % u", ".join(n for n, _t in FIELDS))


if __name__ == u"__main__":
    main()
