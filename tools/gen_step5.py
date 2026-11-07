# -*- coding: utf-8 -*-
"""
gen_step5.py -- tri formy dlya usloviya perehoda (SL_BRANCH otklonen).

Zadacha: TAKE = (COND=0 & FZ) | (COND=1 & !FZ) | (COND=2 & FC) | (COND=3 & !FC)

  SL_BRND  OR iz SEL  (maksimalno blizko k dekoderu: EQ + SEL + OR, bez NOT/AND)
  SL_BRNC  cepochka SEL, otricanie cherez SEL(y,FALSE,TRUE)
  SL_BRNB  cepochka SEL, otricanie cherez XOR s TRUE
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
B0, B1 = G.B0, G.B1
T, F = G.T, G.F


def eqs(s):
    cond = s.ref(u"COND", 0)
    r = []
    for k in range(4):
        r.append(s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#%d" % k, 1))], 1))
    return r


def brnd():
    s = Sheet(u"SL_BRND: условие через OR из SEL")
    e = eqs(s)
    fz = s.ref(u"FZ", 0)
    fc = s.ref(u"FC", 0)
    nz = s.blk(u"SEL", [(u"G", fz), (u"IN0", s.const(F, 2)), (u"IN1", s.const(T, 2))], 2)
    nc = s.blk(u"SEL", [(u"G", fc), (u"IN0", s.const(F, 2)), (u"IN1", s.const(T, 2))], 2)
    p0 = s.blk(u"SEL", [(u"G", e[0]), (u"IN0", fz), (u"IN1", s.const(F, 3))], 3)
    p1 = s.blk(u"SEL", [(u"G", e[1]), (u"IN0", nz), (u"IN1", s.const(F, 3))], 3)
    p2 = s.blk(u"SEL", [(u"G", e[2]), (u"IN0", fc), (u"IN1", s.const(F, 3))], 3)
    p3 = s.blk(u"SEL", [(u"G", e[3]), (u"IN0", nc), (u"IN1", s.const(F, 3))], 3)
    o01 = s.blk(u"OR", [(u"IN1", p0), (u"IN2", p1)], 5)
    o23 = s.blk(u"OR", [(u"IN1", p2), (u"IN2", p3)], 5)
    s.assign(u"TAKE", s.blk(u"OR", [(u"IN1", o01), (u"IN2", o23)], 6), 7)
    return s, []


def brn(use_xor, name):
    s = Sheet(u"%s: условие через цепочку SEL" % name)
    e = eqs(s)
    fz = s.ref(u"FZ", 0)
    fc = s.ref(u"FC", 0)
    if use_xor:
        nz = s.blk(u"XOR", [(u"IN1", fz), (u"IN2", s.const(T, 2))], 2)
        nc = s.blk(u"XOR", [(u"IN1", fc), (u"IN2", s.const(T, 2))], 2)
    else:
        nz = s.blk(u"SEL", [(u"G", fz), (u"IN0", s.const(F, 2)), (u"IN1", s.const(T, 2))], 2)
        nc = s.blk(u"SEL", [(u"G", fc), (u"IN0", s.const(F, 2)), (u"IN1", s.const(T, 2))], 2)
    t3 = s.blk(u"SEL", [(u"G", e[3]), (u"IN0", nc), (u"IN1", s.const(F, 3))], 3)
    t2 = s.blk(u"SEL", [(u"G", e[2]), (u"IN0", fc), (u"IN1", t3)], 4)
    t1 = s.blk(u"SEL", [(u"G", e[1]), (u"IN0", nz), (u"IN1", t2)], 5)
    ta = s.blk(u"SEL", [(u"G", e[0]), (u"IN0", fz), (u"IN1", t1)], 6)
    s.assign(u"TAKE", ta, 8)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


INPUTS = [(u"COND", u"BYTE"), (u"FZ", u"BOOL"), (u"FC", u"BOOL")]
OUTPUTS = [(u"TAKE", u"BOOL")]


def main():
    print(u"=== gen_step5 ===")
    s, L = brnd()
    write(u"SL_BRND", pou_xml(u"SL_BRND", u"functionBlock",
                              interface(inputs=INPUTS, outputs=OUTPUTS, locals_=L),
                              [s], u"условие D"))
    s, L = brn(False, u"SL_BRNC")
    write(u"SL_BRNC", pou_xml(u"SL_BRNC", u"functionBlock",
                              interface(inputs=INPUTS, outputs=OUTPUTS, locals_=L),
                              [s], u"условие C"))
    s, L = brn(True, u"SL_BRNB")
    write(u"SL_BRNB", pou_xml(u"SL_BRNB", u"functionBlock",
                              interface(inputs=INPUTS, outputs=OUTPUTS, locals_=L),
                              [s], u"условие B"))
    print(u"готово")


if __name__ == "__main__":
    main()
