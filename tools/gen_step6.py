# -*- coding: utf-8 -*-
"""
gen_step6.py -- dva voprosa.

1) SL_T1 -- ochen malenkiy list: odin SEL s BOOL-vhodami.
   Vse uspeshnye listy ispolzuyut SEL tolko s BYTE/WORD dannymi; vse neudachi
   s usloviem perehoda soderzhat SEL po BOOL. Proveryaem pryamo.

2) SL_BRNE -- uslovie perehoda BEZ SEL: tolko sravneniya i BOOL-operacii,
   otricanie cherez NE(FZ, FALSE) vmesto NOT.
   TAKE = (COND=0 AND FZ) OR (COND=1 AND !FZ) OR (COND=2 AND FC) OR (COND=3 AND !FC)
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml
import gen_cpu_split as G

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
T, F = G.T, G.F


def sl_t1():
    s = Sheet(u"SL_T1: SEL по BOOL")
    g = s.ref(u"A", 0)
    s.assign(u"T1", s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(F, 1)),
                                   (u"IN1", s.const(T, 1))], 1), 3)
    return s, []


def sl_brne():
    s = Sheet(u"SL_BRNE: условие через NE/AND/OR")
    cond = s.ref(u"COND", 0)
    fz = s.ref(u"FZ", 0)
    fc = s.ref(u"FC", 0)
    e0 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#0", 1))], 1)
    e1 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#1", 1))], 1)
    e2 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#2", 1))], 1)
    e3 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#3", 1))], 1)
    nz = s.blk(u"NE", [(u"IN1", fz), (u"IN2", s.const(F, 2))], 2)
    nc = s.blk(u"NE", [(u"IN1", fc), (u"IN2", s.const(F, 2))], 2)
    a0 = s.blk(u"AND", [(u"IN1", e0), (u"IN2", fz)], 2)
    a1 = s.blk(u"AND", [(u"IN1", e1), (u"IN2", nz)], 2)
    a2 = s.blk(u"AND", [(u"IN1", e2), (u"IN2", fc)], 2)
    a3 = s.blk(u"AND", [(u"IN1", e3), (u"IN2", nc)], 2)
    o01 = s.blk(u"OR", [(u"IN1", a0), (u"IN2", a1)], 4)
    o23 = s.blk(u"OR", [(u"IN1", a2), (u"IN2", a3)], 4)
    s.assign(u"TAKE", s.blk(u"OR", [(u"IN1", o01), (u"IN2", o23)], 6), 7)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-9s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_step6 ===")
    s, L = sl_t1()
    write(u"SL_T1", pou_xml(u"SL_T1", u"functionBlock",
                            interface(inputs=[(u"A", u"BOOL")],
                                      outputs=[(u"T1", u"BOOL")], locals_=L),
                            [s], u"SEL по BOOL"))
    s, L = sl_brne()
    write(u"SL_BRNE", pou_xml(u"SL_BRNE", u"functionBlock",
                              interface(inputs=[(u"COND", u"BYTE"), (u"FZ", u"BOOL"),
                                                (u"FC", u"BOOL")],
                                        outputs=[(u"TAKE", u"BOOL")], locals_=L),
                              [s], u"условие NE"))
    print(u"готово")


if __name__ == "__main__":
    main()
