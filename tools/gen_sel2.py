# -*- coding: utf-8 -*-
"""
gen_sel2.py -- dva voprosa odnim opytom.

1) Glavnoe: rabotaet li list "CHISTYY VYBOR" -- EQ + SEL + OR po 11 WORD-vhodam,
   bez arifmetiki. Eto klyuch k arhitekture "odno semеystvo na list".
   (Ranee P2_SL_SELECT ne bil dostignut: do nego zavis P1.)

2) Pochemu zavis P1_SL_CALC, esli AR11 s temi zhe 11 z HIVYMI vyhodami sozdaetsya?
   Edinstvennoe razlichie: v P1 odin i tot zhe vyhod AB prisvaivalsya PYATI
   vyhodnym kontaktam. Proveryaem:
     AD1 -- 11 raznyh setey        (kontrol)
     AD2 -- AB povtoryaetsya 5 raz  (kak v P1)

Poryadok: glavnoe snachala, podozritelnoe poslednim.
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
W0, W1 = G.W0, G.W1

CAND = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX", u"C_ABY",
        u"C_IZX", u"C_IZY", u"C_IND", u"C_STK"]
CODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def build_select():
    s = Sheet(u"SL_SELECT: выбор адреса по режиму")
    modev = s.ref(u"ADDR_MODE", 0)
    parts = []
    for nm, code in zip(CAND, CODES):
        g = s.blk(u"EQ", [(u"IN1", modev), (u"IN2", s.const(u"BYTE#%d" % code, 2))], 2)
        parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(W0, 4)),
                                    (u"IN1", s.ref(nm, 4))], 4))
    cur = parts[0]
    col = 6
    for p in parts[1:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], col)
        col += 1
    s.assign(u"EFF", cur, 12)
    return s, []


def calc_base(s):
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
    return [imm_w, zpw, zpxw, zpyw, AB, abx, aby, AB, AB, AB, AB]


def build_ad(distinct):
    s = Sheet(u"SL_CALC: %s" % (u"разные сети" if distinct else u"повтор источника"))
    nets = calc_base(s)
    if distinct:
        extra = s.blk(u"ADD", [(u"IN1", s.ref(u"PC2", 0)), (u"IN2", s.const(W1, 10))], 11)
        nets = [nets[0], nets[1], nets[2], nets[3], nets[4], nets[5], nets[6],
                extra, extra, extra, extra]
    for nm, src in zip(CAND, nets):
        s.assign(nm, src, 12)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


INPUTS = [(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
          (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD")]


def main():
    print(u"=== gen_sel2 ===")
    s, L = build_select()
    write(u"SEL1", pou_xml(u"SEL1", u"functionBlock",
                           interface(inputs=[(u"ADDR_MODE", u"BYTE")] +
                                           [(n, u"WORD") for n in CAND],
                                     outputs=[(u"EFF", u"WORD")], locals_=L),
                           [s], u"лист выбора адреса"))

    for distinct, name in ((True, u"AD1"), (False, u"AD2")):
        s, L = build_ad(distinct)
        write(name, pou_xml(name, u"functionBlock",
                            interface(inputs=INPUTS, outputs=[(n, u"WORD") for n in CAND],
                                      locals_=L),
                            [s], u"калькулятор (%s)" % (u"разные" if distinct else u"повтор")))
    print(u"готово")


if __name__ == "__main__":
    main()
