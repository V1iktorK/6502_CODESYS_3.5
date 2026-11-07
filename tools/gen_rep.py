# -*- coding: utf-8 -*-
"""
gen_rep.py -- chistyy opyt: odin vyhod bloka na N vyhodnyh kontaktov.

Nablyudeniya (3 iz 3 soglasuyutsya):
  AR11  -- 11 ZHIVYH, no RAZNYH setey          СОЗДАН
  SEL1  -- vybor, kazhdyy istochnik odin raz   СОЗДАН
  P1    -- odin vyhod AB prisvaivalsya 5 raz   ЗАВИСАНИЕ
  AD1   -- odin vyhod extra 4 raza             ЗАВИСАНИЕ

Gipoteza: povtornoe prisvoenie ODNOGO vyhoda bloka neskolkim IMENAM-peremennym
lomaet import (v rabotayushchih listah kazhdyy vyhod prisvaivaetsya rovno odin raz).

Variants (odinakovyy interfeys, odinakovye bloki; menyaetsya tolko chislo povtorov):
  RP0 -- povtorov 0 (vse 11 raznye)   <-- kontrol
  RP1 -- povtorov 1 (AB dva raza)
  RP2 -- povtorov 4 (AB pyat raz)
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


def build(repeats):
    s = Sheet(u"SL_CALC: повторов %d" % repeats)
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
    ind = s.blk(u"ADD", [(u"IN1", aby), (u"IN2", zpxw)], 9)

    # 11 raznyh setey
    nets = [imm_w, zpw, zpxw, zpyw, AB, abx, aby, izx, izy, ind, pc2]
    # podmenyaem poslednie "repeats" setey na povtor AB
    for i in range(repeats):
        nets[len(nets) - 1 - i] = AB
    for nm, src in zip(CAND, nets):
        s.assign(nm, src, 12)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-8s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_rep ===")
    for reps in (0, 1, 4):
        s, L = build(reps)
        write(u"RP%d" % reps, pou_xml(u"RP%d" % reps, u"functionBlock",
                                      interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                                        (u"X", u"BYTE"), (u"Y", u"BYTE"),
                                                        (u"PCs", u"WORD"), (u"PC2", u"WORD")],
                                                outputs=[(n, u"WORD") for n in CAND],
                                                locals_=L),
                                      [s], u"повторов %d" % reps))
    print(u"готово")


if __name__ == "__main__":
    main()
