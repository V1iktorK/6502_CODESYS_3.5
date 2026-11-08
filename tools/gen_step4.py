# -*- coding: utf-8 -*-
"""
gen_step4.py -- ekvivalentnye formy dlya dvuh otklonennyh listov.

Otkлонeny:
  SL_REL0  -- GE(BYTE) + SEL(BYTE) + ADD(BYTE)   -> OFFB
  SL_BRANCH-- EQ + NOT + AND + OR (BOOL)

Probуem drugie formy:
  SL_REL_A  GT(OP1, $7F) -> SEL(WORD $FF00 / $0000) + B2W + ADD   (sravnenie -> WORD-выбор)
  SL_REL_B  LT(OP1, $80) -> SEL(WORD $0000 / $FF00) + B2W + ADD
  SL_BRN_A  cepochka SEL vmesto AND/OR, s NOT
  SL_BRN_B  cepochka SEL, vyrazhenie "ne" cherez XOR s TRUE
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
W0 = G.W0


def rel_a():
    s = Sheet(u"SL_REL_A: знаковое расширение через WORD-выбор")
    op1 = s.ref(u"OP1", 0)
    sgn = s.blk(u"GT", [(u"IN1", op1), (u"IN2", s.const(u"BYTE#16#7F", 1))], 1)
    # CODESYS: G=TRUE берёт IN1. Поэтому отрицательное смещение (OP1 >= $80)
    # должно давать маску $FF00, а положительное -- ноль. Раньше было наоборот,
    # и переход вперёд уезжал на $FFxx (PC=$0107 вместо $0207).
    msk = s.blk(u"SEL", [(u"G", sgn), (u"IN0", s.const(W0, 2)),
                         (u"IN1", s.const(u"WORD#16#FF00", 2))], 2)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 2, width=140)),
                          (u"IN2", msk)], 3)
    s.assign(u"OFFW", offw, 5)
    return s, []


def rel_b():
    s = Sheet(u"SL_REL_B: знаковое расширение через LT")
    op1 = s.ref(u"OP1", 0)
    sgn = s.blk(u"LT", [(u"IN1", op1), (u"IN2", s.const(u"BYTE#16#80", 1))], 1)
    # см. комментарий в rel_a: при G=TRUE берётся IN1
    msk = s.blk(u"SEL", [(u"G", sgn), (u"IN0", s.const(u"WORD#16#FF00", 2)),
                         (u"IN1", s.const(W0, 2))], 2)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 2, width=140)),
                          (u"IN2", msk)], 3)
    s.assign(u"OFFW", offw, 5)
    return s, []


def brn(use_xor):
    s = Sheet(u"SL_BRN: условие перехода (SEL-цепочка)")
    cond = s.ref(u"COND", 0)
    fz = s.ref(u"FZ", 0)
    fc = s.ref(u"FC", 0)
    e0 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(B0, 1))], 1)
    e1 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(B1, 1))], 1)
    e2 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#2", 1))], 1)
    e3 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#3", 1))], 1)
    if use_xor:
        nz = s.blk(u"XOR", [(u"IN1", fz), (u"IN2", s.const(T, 2))], 2)
        nc = s.blk(u"XOR", [(u"IN1", fc), (u"IN2", s.const(T, 2))], 2)
    else:
        nz = s.blk(u"NOT", [(u"IN", fz)], 2)
        nc = s.blk(u"NOT", [(u"IN", fc)], 2)
    t3 = s.blk(u"SEL", [(u"G", e3), (u"IN0", nc), (u"IN1", s.const(F, 3))], 3)
    t2 = s.blk(u"SEL", [(u"G", e2), (u"IN0", fc), (u"IN1", t3)], 4)
    t1 = s.blk(u"SEL", [(u"G", e1), (u"IN0", nz), (u"IN1", t2)], 5)
    ta = s.blk(u"SEL", [(u"G", e0), (u"IN0", fz), (u"IN1", t1)], 6)
    s.assign(u"TAKE", ta, 8)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_step4 ===")
    s, L = rel_a()
    write(u"SL_RELA", pou_xml(u"SL_RELA", u"functionBlock",
                              interface(inputs=[(u"OP1", u"BYTE")],
                                        outputs=[(u"OFFW", u"WORD")], locals_=L),
                              [s], u"расширение A"))
    s, L = rel_b()
    write(u"SL_RELB", pou_xml(u"SL_RELB", u"functionBlock",
                              interface(inputs=[(u"OP1", u"BYTE")],
                                        outputs=[(u"OFFW", u"WORD")], locals_=L),
                              [s], u"расширение B"))
    s, L = brn(False)
    write(u"SL_BRNA", pou_xml(u"SL_BRNA", u"functionBlock",
                              interface(inputs=[(u"COND", u"BYTE"), (u"FZ", u"BOOL"),
                                                (u"FC", u"BOOL")],
                                        outputs=[(u"TAKE", u"BOOL")], locals_=L),
                              [s], u"условие A"))
    s, L = brn(True)
    write(u"SL_BRNB", pou_xml(u"SL_BRNB", u"functionBlock",
                              interface(inputs=[(u"COND", u"BYTE"), (u"FZ", u"BOOL"),
                                                (u"FC", u"BOOL")],
                                        outputs=[(u"TAKE", u"BOOL")], locals_=L),
                              [s], u"условие B"))
    print(u"готово")


if __name__ == "__main__":
    main()
