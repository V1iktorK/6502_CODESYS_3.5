# -*- coding: utf-8 -*-
"""
gen_live.py -- skolko "ZHIVYH" arifmeticheskih vyhodov vyderzhivaet list.

Fakty:
  AW12  (7 vhodov, 4 vyhoda; arithmeticheski ZHIV tolko AB)          СОЗДАН
  P1_SL_CALC (6 vhodov, 11 WORD-vyhodov; zhivy VSE odinnadtsat)      ЗАВИСАНИЕ

Razlichiya: chislo vyhodnyh kontaktov i chislo zhivyh arifmeticheskih setey.
Chtoby razdelit eti faktory, interfeys vo vseh variantah ODINAKOVYY
(6 vhodov + 11 WORD-vyhodov), a menyaetsya tolko kolichestvo zhivyh setey:
ostalnye vyhody poluchayut konstantu WORD#0.

  AR1  живая 1 сеть  (C_ABS := AB)
  AR2  живые 2       (+ C_ZP := zpw)
  AR3  живые 3       (+ C_ZPX)
  AR4  живые 5       (+ C_ZPY, C_ABX)
  AR6  живые 8
  AR9  живые 11      (vse)
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


def build(live):
    s = Sheet(u"SL_CALC: живых сетей %d" % live)
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
    izx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", zpw)], 7)
    izy = s.blk(u"ADD", [(u"IN1", abx), (u"IN2", zpyw)], 8)

    nets = [AB, zpw, zpxw, zpyw, abx, zp, zpy, imm_w, izx, izy, pc2]
    for i, (nm, src) in enumerate(zip(CAND, nets)):
        if i < live:
            s.assign(nm, src, 12)
        else:
            s.assign(nm, s.const(W0, 12), 12)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-8s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_live ===")
    for live in (1, 2, 3, 5, 8, 11):
        s, L = build(live)
        xml = pou_xml(u"AR%d" % live, u"functionBlock",
                      interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                                        (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD")],
                                outputs=[(n, u"WORD") for n in CAND],
                                locals_=L),
                      [s], u"живых сетей %d" % live)
        write(u"AR%d" % live, xml)
    print(u"готово")


if __name__ == "__main__":
    main()
