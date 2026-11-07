# -*- coding: utf-8 -*-
"""
gen_base2.py -- SL_BASE2: kandidaty adresov v DISCPLINE KOLONOK rabochego AR11.

Chto izvestno:
  AR11  (13 blokov, 11 vyhodov) -- СОЗДАН; bloki v kolonkah 3..10, vyhody v 12,
        vhody v 0, odna obshchaya konstanta WORD#1.
  SL_BASE (15 blokov)           -- ЗАВИСАНИЕ; vyhody v kolonke 9, konstanty
        popali v te zhe kolonki, chto i bloki.
  SL_IND                        -- СОЗДАН.

Probуem povtorit geometriyu AR11:
  * vhody -- kolonka 0;
  * bloki -- kolonki 3..8;
  * odna OBSHCHAYA konstanta WORD#1 (sozdaetsya odin raz i peredaetsya po id);
  * vyhody -- otdelnaya dalnyaya kolonka 10;
  * kazhdyy vyhod prisvaivaetsya rovno odin raz.
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

OUTNAMES = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX", u"C_ABY",
            u"P_IZX0", u"P_IZX1", u"P_IZY0", u"P_IZY1"]


def build():
    s = Sheet(u"SL_BASE2: кандидаты адресов")
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)
    one = s.const(W1, 0)          # одна общая константа на весь лист

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
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", one)], 6)
    p_izx0 = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 7, width=140)
    p_izx1 = s.blk(u"ADD", [(u"IN1", p_izx0), (u"IN2", one)], 7)
    p_izy0 = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 8, width=140)
    p_izy1 = s.blk(u"ADD", [(u"IN1", p_izy0), (u"IN2", one)], 8)

    for nm, src in zip(OUTNAMES,
                       (imm_w, zpw, zpxw, zpyw, AB, abx, aby,
                        p_izx0, p_izx1, p_izy0, p_izy1)):
        s.assign(nm, src, 10)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_base2 ===")
    s, L = build()
    write(u"SL_BASE2", pou_xml(u"SL_BASE2", u"functionBlock",
                               interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                                 (u"X", u"BYTE"), (u"Y", u"BYTE"),
                                                 (u"PCs", u"WORD")],
                                         outputs=[(n, u"WORD") for n in OUTNAMES],
                                         locals_=L),
                               [s], u"кандидаты адресов"))
    print(u"готово")


if __name__ == "__main__":
    main()
