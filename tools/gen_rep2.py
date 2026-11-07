# -*- coding: utf-8 -*-
"""
gen_rep2.py -- proverka pravila "odin element ne dolzhen pitat neskolko prisvoeniy".

Sravnenie baz:
  AR1..AR11 -- dlya kazhdogo prisvoeniya sozdaetsya SVOY element-konstanta
               (s.const vyzyvaetsya vnтри cikla)                       СОЗДАНЫ
  CL1       -- odna konstanta `zero` pereispolzuetsya 4 raza            ЗАВИСАНИЕ
  CL2..CL5  -- to zhe (baza s obshchey `zero`)                         ЗАВИСАНИЕ

Opyty:
  CF1  kak CL1, no konstanta sozdaetsya ZANOVO dlya kazhdogo prisvoeniya
  CS1  kak CL1 s obshchey konstantoy (kontrol, ozhidaemoe zavisanie, posledniy)
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
        u"C_IZX", u"C_IZY", u"C_IND", u"C_REL"]


def build(shared):
    s = Sheet(u"SL_CALC: %s" % (u"общая константа" if shared else u"своя константа"))
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

    nets = [imm_w, zpw, zpxw, zpyw, AB, abx, aby, None, None, None, None]
    zero = s.const(W0, 12) if shared else None
    for nm, src in zip(CAND, nets):
        s.assign(nm, src if src is not None else (zero if shared else s.const(W0, 12)), 12)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-6s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_rep2 ===")
    for shared, name in ((False, u"CF1"), (True, u"CS1")):
        s, L = build(shared)
        write(name, pou_xml(name, u"functionBlock",
                            interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                              (u"X", u"BYTE"), (u"Y", u"BYTE"),
                                              (u"PCs", u"WORD"), (u"PC2", u"WORD")],
                                      outputs=[(n, u"WORD") for n in CAND], locals_=L),
                            [s], u"общая константа: %s" % shared))
    print(u"готово")


if __name__ == "__main__":
    main()
