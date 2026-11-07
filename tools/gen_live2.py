# -*- coding: utf-8 -*-
"""
gen_live2.py -- narashchivanie ot AR11 (DOKAZANNO sozdaetsya) do polnogo kalkulyatora.

Arhitektura "odno semеystvo na list": etot list -- CHISTAYA arifmetika adresov,
vhody OP1/OP2/X/Y/PCs/PC2, vyhody -- 11 adresov-kandidatov. Nichego krome
ADD / BYTE_TO_WORD / F_Join16 / чтения Mem.

Baza -- imenno AR11 (sozdaetsya ustoychivo, proverено dvazhdy). Dalee dobavlyaem
po odnomu uzlu i smotrim, na kakom shage import nachinaet visnut:

  R1 = AR11 (kak est)
  R2 = + izx_ptr / izx_ptr1
  R3 = + chtenie Mem[IZX_PTR], Mem[IZX_PTR1] i F_Join16 -> C_IZX
  R4 = + to zhe dlya izy (Mem[IZY_PTR...], + ADD s yw) -> C_IZY, C_IND
  R5 = + relative (relw) -> novyy vyhod C_REL
  R6 = polnyy kalkulyator (vse vyhody zhivye, kazhdyy odin raz)
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
W0, W1 = G.W0, G.W1

CAND = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX", u"C_ABY",
        u"C_IZX", u"C_IZY", u"C_IND", u"C_REL"]


def build(level):
    s = Sheet(u"SL_CALC: ступень %d" % level)
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)
    pc2 = s.ref(u"PC2", 0)

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
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 9))], 10)

    izx = izy = ind = relw = None
    L = []
    if level >= 2:
        s.assign(u"IZX_PTR", s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 5, width=140), 6)
        s.assign(u"IZX_PTR1", s.blk(u"ADD", [(u"IN1", s.ref(u"IZX_PTR", 6)),
                                             (u"IN2", s.const(W1, 6))], 6), 7)
        L += [(u"IZX_PTR", u"WORD"), (u"IZX_PTR1", u"WORD")]
    if level >= 3:
        lo = s.ref(MEM + u".Mem[IZX_PTR]", 7)
        hi = s.ref(MEM + u".Mem[IZX_PTR1]", 7)
        izx = s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 8, width=110)
    if level >= 4:
        s.assign(u"IZY_PTR", s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 5, width=140), 6)
        s.assign(u"IZY_PTR1", s.blk(u"ADD", [(u"IN1", s.ref(u"IZY_PTR", 6)),
                                             (u"IN2", s.const(W1, 6))], 6), 7)
        lo2 = s.ref(MEM + u".Mem[IZY_PTR]", 7)
        hi2 = s.ref(MEM + u".Mem[IZY_PTR1]", 8)
        izy = s.blk(u"ADD", [(u"IN1", s.blk(u"F_Join16", [(u"LO", lo2), (u"HI", hi2)], 8, width=110)),
                             (u"IN2", yw)], 9)
        ind = s.blk(u"ADD", [(u"IN1", aby), (u"IN2", zpxw)], 9)
        L += [(u"IZY_PTR", u"WORD"), (u"IZY_PTR1", u"WORD")]
    if level >= 5:
        sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 6))], 6)
        off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", op1),
                             (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 7))], 7))], 8)
        offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 8, width=140)),
                              (u"IN2", s.const(u"WORD#16#FF00", 8))], 9)
        relw = s.blk(u"ADD", [(u"IN1", pc2), (u"IN2", offw)], 10)

    zero = s.const(W0, 12)
    nets = [imm_w, zpw, zpxw, zpyw, AB, abx, aby,
            izx if izx is not None else zero,
            izy if izy is not None else zero,
            ind if ind is not None else zero,
            relw if relw is not None else zero]
    for nm, src in zip(CAND, nets):
        s.assign(nm, src, 12)
    return s, L


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-8s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_live2 ===")
    for lvl in (1, 2, 3, 4, 5):
        s, L = build(lvl)
        write(u"CL%d" % lvl, pou_xml(u"CL%d" % lvl, u"functionBlock",
                                     interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                                       (u"X", u"BYTE"), (u"Y", u"BYTE"),
                                                       (u"PCs", u"WORD"), (u"PC2", u"WORD")],
                                               outputs=[(n, u"WORD") for n in CAND],
                                               locals_=L),
                                     [s], u"ступень %d" % lvl))
    print(u"готово")


if __name__ == "__main__":
    main()
