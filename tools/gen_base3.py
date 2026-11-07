# -*- coding: utf-8 -*-
"""
gen_base3.py -- kalkulyator adresov, razrezannyy na DVA malyh lista.

Nablyudeniya:
  * listy v 3..13 blokov (FB_Fetch, SL_IND, AR1..AR11, SEL1) sozdayutsya stabilno;
  * SL_BASE / SL_BASE2 (15 blokov, 11 vyhodov) -- zavisanie ili krah.

Poetomu kalkulyator delitsya po smyslu:
  SL_C1 -- kandidaty adresov: C_IMM C_ZP C_ZPX C_ZPY C_ABS C_ABX C_ABY  (11 blokov)
  SL_C2 -- ukazateli kosvennyh rezhimov: P_IZX0 P_IZX1 P_IZY0 P_IZY1     (4 bloka)

SL_C2 stroitsya i proveryaetsya pervym (on menshe i proshche).
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
W1 = G.W1


def sl_c1():
    s = Sheet(u"SL_C1: кандидаты адресов")
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)

    AB = s.blk(u"F_Join16", [(u"LO", op1), (u"HI", op2)], 3, width=110)
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 4)
    zpy = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", y)], 4)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 4, width=140)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 5, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 5, width=140)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 5, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 5, width=120)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 6)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 6)
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 6))], 6)

    for nm, src in ((u"C_IMM", imm_w), (u"C_ZP", zpw), (u"C_ZPX", zpxw),
                    (u"C_ZPY", zpyw), (u"C_ABS", AB), (u"C_ABX", abx), (u"C_ABY", aby)):
        s.assign(nm, src, 8)
    return s, []


def sl_c2():
    s = Sheet(u"SL_C2: указатели косвенных режимов")
    op1 = s.ref(u"OP1", 0)
    x = s.ref(u"X", 0)
    one = s.const(W1, 0)
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 3)
    p0 = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 4, width=140)
    q0 = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 4, width=140)
    p1 = s.blk(u"ADD", [(u"IN1", p0), (u"IN2", one)], 5)
    q1 = s.blk(u"ADD", [(u"IN1", q0), (u"IN2", one)], 5)
    for nm, src in ((u"P_IZX0", p0), (u"P_IZX1", p1), (u"P_IZY0", q0), (u"P_IZY1", q1)):
        s.assign(nm, src, 7)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-8s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_base3 ===")
    s, L = sl_c2()
    write(u"SL_C2", pou_xml(u"SL_C2", u"functionBlock",
                            interface(inputs=[(u"OP1", u"BYTE"), (u"X", u"BYTE")],
                                      outputs=[(n, u"WORD") for n in
                                               (u"P_IZX0", u"P_IZX1", u"P_IZY0", u"P_IZY1")],
                                      locals_=L),
                            [s], u"указатели"))

    s, L = sl_c1()
    write(u"SL_C1", pou_xml(u"SL_C1", u"functionBlock",
                            interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                              (u"X", u"BYTE"), (u"Y", u"BYTE"),
                                              (u"PCs", u"WORD")],
                                      outputs=[(n, u"WORD") for n in
                                               (u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY",
                                                u"C_ABS", u"C_ABX", u"C_ABY")],
                                      locals_=L),
                            [s], u"кандидаты"))
    print(u"готово")


if __name__ == "__main__":
    main()
