# -*- coding: utf-8 -*-
"""
gen_addr3.py -- adresaciya iz TREH listov, kazhdyy v DOKAZANNO rabochem stile.

Dokazano importiruyutsya:
  * chistaya arifmetika (AR1..AR11, do 15 blokov i 11 zhivyh vyhodov);
  * chtenie pamyati po VHODNOMU adresu (FB_Fetch: Mem[PCs], Mem[PC1], Mem[PC2]);
  * chistyy vybor EQ+SEL+OR po WORD-vhodam (SEL1).

Poetomu adresaciya razrezаetsya tak, chtoby kazhdyy list prinadlezhаl odnomu semеystvu:

  SL_BASE  (arifmetika)      vhody OP1/OP2/X/Y/PCs -> kandidaty adresov
                             i ukazateli kosvennyh rezhimov P_IZX0/P_IZX1/P_IZY0/P_IZY1
  SL_IND   (chtenie pamyati) vhody P_IZX0..P_IZY1 -> C_IZX, C_IZY
                             (adres prishл kontaktom -- kak v FB_Fetch)
  SL_REL   (znakovoe smeshchenie) OP1, PC2 -> C_REL

Opyty (poryadok: naibolee bezopasnye snachala):
  SL_IND, SL_BASE, SL_REL, FB_WriteBack
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
MEM = G.MEM
B80 = G.B80
W1 = G.W1


def sl_base():
    s = Sheet(u"SL_BASE: кандидаты адресов (чистая арифметика)")
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)

    AB = s.blk(u"F_Join16", [(u"LO", op1), (u"HI", op2)], 4, width=110)
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 3)
    zpy = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", y)], 3)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 4, width=140)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 4, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 4, width=140)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 5, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 5, width=120)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 6)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 6)
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 7))], 7)
    p_izx0 = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 6, width=140)
    p_izx1 = s.blk(u"ADD", [(u"IN1", p_izx0), (u"IN2", s.const(W1, 6))], 7)
    p_izy0 = zpw
    p_izy1 = s.blk(u"ADD", [(u"IN1", p_izy0), (u"IN2", s.const(W1, 6))], 7)

    for nm, src in ((u"C_IMM", imm_w), (u"C_ZP", zpw), (u"C_ZPX", zpxw), (u"C_ZPY", zpyw),
                    (u"C_ABS", AB), (u"C_ABX", abx), (u"C_ABY", aby),
                    (u"P_IZX0", p_izx0), (u"P_IZX1", p_izx1),
                    (u"P_IZY0", p_izy0), (u"P_IZY1", p_izy1)):
        s.assign(nm, src, 9)
    return s, []


def sl_ind():
    s = Sheet(u"SL_IND: косвенные адреса через память")
    p0 = s.ref(u"P_IZX0", 0)
    p1 = s.ref(u"P_IZX1", 0)
    q0 = s.ref(u"P_IZY0", 0)
    q1 = s.ref(u"P_IZY1", 0)
    yw = s.ref(u"YW", 0)
    lo = s.ref(MEM + u".Mem[P_IZX0]", 1)
    hi = s.ref(MEM + u".Mem[P_IZX1]", 1)
    s.assign(u"C_IZX", s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 3, width=110), 4)
    lo2 = s.ref(MEM + u".Mem[P_IZY0]", 1)
    hi2 = s.ref(MEM + u".Mem[P_IZY1]", 2)
    s.assign(u"C_IZY", s.blk(u"ADD", [(u"IN1", s.blk(u"F_Join16", [(u"LO", lo2), (u"HI", hi2)],
                                                   3, width=110)),
                                     (u"IN2", yw)], 4), 5)
    del p0, p1, q0, q1
    return s, []


def sl_rel():
    s = Sheet(u"SL_REL: знаковое смещение перехода")
    op1 = s.ref(u"OP1", 0)
    pc2 = s.ref(u"PC2", 0)
    sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 1))], 1)
    off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", op1),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 2))], 2))], 3)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 3, width=140)),
                          (u"IN2", s.const(u"WORD#16#FF00", 3))], 4)
    s.assign(u"C_REL", s.blk(u"ADD", [(u"IN1", pc2), (u"IN2", offw)], 5), 6)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-14s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_addr3 ===")

    s, L = sl_ind()
    write(u"SL_IND", pou_xml(u"SL_IND", u"functionBlock",
                             interface(inputs=[(u"P_IZX0", u"WORD"), (u"P_IZX1", u"WORD"),
                                               (u"P_IZY0", u"WORD"), (u"P_IZY1", u"WORD"),
                                               (u"YW", u"WORD")],
                                       outputs=[(u"C_IZX", u"WORD"), (u"C_IZY", u"WORD")],
                                       locals_=L),
                             [s], u"косвенные адреса"))

    s, L = sl_base()
    write(u"SL_BASE", pou_xml(u"SL_BASE", u"functionBlock",
                              interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                                (u"X", u"BYTE"), (u"Y", u"BYTE"),
                                                (u"PCs", u"WORD")],
                                        outputs=[(n, u"WORD") for n in
                                                 (u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY",
                                                  u"C_ABS", u"C_ABX", u"C_ABY",
                                                  u"P_IZX0", u"P_IZX1", u"P_IZY0", u"P_IZY1")],
                                        locals_=L),
                              [s], u"кандидаты адресов"))

    s, L = sl_rel()
    write(u"SL_REL", pou_xml(u"SL_REL", u"functionBlock",
                             interface(inputs=[(u"OP1", u"BYTE"), (u"PC2", u"WORD")],
                                       outputs=[(u"C_REL", u"WORD")], locals_=L),
                             [s], u"знаковое смещение"))
    print(u"готово")


if __name__ == "__main__":
    main()
