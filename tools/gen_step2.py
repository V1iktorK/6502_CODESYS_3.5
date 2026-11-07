# -*- coding: utf-8 -*-
"""
gen_step2.py -- sleduyushchie malye listy (5-6 blokov kazhdyy).

Rabotaet stabilno pri 3..13 blokah (FB_Fetch, SL_IND, AR*, SEL1). Poetomu
kalkulyator i vybor rezhem na kak mozhno bolee melkie listy:

  SL_SELECT  vybor effektivnogo adresa: vhody ADDR_MODE + 7 kandidatov -> EFF
             (formа dokazannogo SEL1)
  SL_IND2    kosvennye adresa SAM: vhody OP1, X, Y -> C_IZX, C_IZY
             (chislenie ukazatelya + chtenie Mem -- kak FB_Fetch)
  SL_C1A     C_IMM, C_ZP, C_ZPX, C_ZPY   (6 blokov)
  SL_C1B     C_ABS, C_ABX, C_ABY         (5 blokov)

Poryadok proverki: SL_SELECT, SL_IND2, SL_C1A, SL_C1B.
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
W0, W1 = G.W0, G.W1

CAND = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX", u"C_ABY"]
CODES = [1, 2, 3, 4, 5, 6, 7]


def sl_select():
    s = Sheet(u"SL_SELECT: выбор эффективного адреса")
    modev = s.ref(u"ADDR_MODE", 0)
    parts = []
    for nm, code in zip(CAND, CODES):
        g = s.blk(u"EQ", [(u"IN1", modev), (u"IN2", s.const(u"BYTE#%d" % code, 1))], 1)
        parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(W0, 2)),
                                    (u"IN1", s.ref(nm, 2))], 2))
    cur = parts[0]
    col = 4
    for p in parts[1:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], col)
        col += 1
    s.assign(u"EFF", cur, 8)
    return s, []


def sl_ind2():
    s = Sheet(u"SL_IND2: косвенные адреса")
    op1 = s.ref(u"OP1", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 1)
    zp1 = s.blk(u"ADD", [(u"IN1", zp), (u"IN2", s.const(u"BYTE#1", 1))], 2)
    zpy1 = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(u"BYTE#1", 1))], 2)
    lo = s.ref(MEM + u".Mem[ZP0]", 3)
    hi = s.ref(MEM + u".Mem[ZP1]", 3)
    s.assign(u"ZP0", zp, 3)
    s.assign(u"ZP1", zp1, 3)
    s.assign(u"C_IZX", s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 5, width=110), 6)

    lo2 = s.ref(MEM + u".Mem[OP1]", 3)
    hi2 = s.ref(MEM + u".Mem[ZPY1]", 4)
    s.assign(u"ZPY1", zpy1, 4)
    s.assign(u"C_IZY", s.blk(u"ADD", [(u"IN1", s.blk(u"F_Join16", [(u"LO", lo2), (u"HI", hi2)],
                                                   5, width=110)),
                                     (u"IN2", s.ref(u"YW", 5))], 6), 7)
    return s, [(u"ZP0", u"WORD"), (u"ZP1", u"WORD"), (u"ZPY1", u"WORD")]


def sl_c1a():
    s = Sheet(u"SL_C1A: адреса нулевой страницы и немедленный")
    op1 = s.ref(u"OP1", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 1, width=140)
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 1)
    zpy = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", y)], 1)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 2, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 2, width=140)
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 2))], 2)
    for nm, src in ((u"C_IMM", imm_w), (u"C_ZP", zpw), (u"C_ZPX", zpxw), (u"C_ZPY", zpyw)):
        s.assign(nm, src, 4)
    return s, []


def sl_c1b():
    s = Sheet(u"SL_C1B: абсолютные адреса и индексация")
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    AB = s.blk(u"F_Join16", [(u"LO", op1), (u"HI", op2)], 1, width=110)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 2, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 2, width=120)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 3)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 3)
    for nm, src in ((u"C_ABS", AB), (u"C_ABX", abx), (u"C_ABY", aby)):
        s.assign(nm, src, 5)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_step2 ===")

    s, L = sl_select()
    write(u"SL_SELECT", pou_xml(u"SL_SELECT", u"functionBlock",
                                interface(inputs=[(u"ADDR_MODE", u"BYTE")] +
                                                [(n, u"WORD") for n in CAND],
                                          outputs=[(u"EFF", u"WORD")], locals_=L),
                                [s], u"выбор адреса"))

    s, L = sl_ind2()
    write(u"SL_IND2", pou_xml(u"SL_IND2", u"functionBlock",
                              interface(inputs=[(u"OP1", u"BYTE"), (u"X", u"BYTE"),
                                                (u"Y", u"BYTE"), (u"YW", u"WORD")],
                                        outputs=[(u"C_IZX", u"WORD"), (u"C_IZY", u"WORD")],
                                        locals_=L),
                              [s], u"косвенные адреса"))

    s, L = sl_c1a()
    write(u"SL_C1A", pou_xml(u"SL_C1A", u"functionBlock",
                             interface(inputs=[(u"OP1", u"BYTE"), (u"X", u"BYTE"),
                                               (u"Y", u"BYTE"), (u"PCs", u"WORD")],
                                       outputs=[(n, u"WORD") for n in
                                                (u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY")],
                                       locals_=L),
                             [s], u"нулевая страница"))

    s, L = sl_c1b()
    write(u"SL_C1B", pou_xml(u"SL_C1B", u"functionBlock",
                             interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"),
                                               (u"X", u"BYTE"), (u"Y", u"BYTE")],
                                       outputs=[(n, u"WORD") for n in
                                                (u"C_ABS", u"C_ABX", u"C_ABY")],
                                       locals_=L),
                             [s], u"абсолютные адреса"))
    print(u"готово")


if __name__ == "__main__":
    main()
