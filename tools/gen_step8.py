# -*- coding: utf-8 -*-
"""
gen_step8.py -- poslednie pyat listov pered kompoziciey.

  SL_SELECT11  11 kandidatov + ADDR_MODE -> EFF   (formа dokazannogo SEL1)
  SL_YW        Y -> YW                            (BYTE_TO_WORD)
  SL_STK4      SPM2 -> STK_A3                     (tretiy bajt zapisi steka)
  SL_BRN2      PC2, C_REL, TAKE -> BRN_TGT        (cel vetvleniya)
  SL_BRK       -> BRKV                            (vektor BRK $FFFE/$FFFF)
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
W0 = G.W0
B1 = G.B1

CAND = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX", u"C_ABY",
        u"C_IZX", u"C_IZY", u"C_IND", u"C_STK"]
CODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def sl_select11():
    s = Sheet(u"SL_SELECT11: выбор эффективного адреса")
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
    s.assign(u"EFF", cur, 9)
    return s, []


def sl_yw():
    s = Sheet(u"SL_YW: расширение Y")
    y = s.ref(u"Y", 0)
    s.assign(u"YW", s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 1, width=140), 3)
    return s, []


def sl_stk4():
    s = Sheet(u"SL_STK4: третий адрес записи стека")
    spm2 = s.ref(u"SPM2", 0)
    one = s.const(B1, 0)
    s.assign(u"STK_A3", s.blk(u"F_Join16", [(u"LO", spm2), (u"HI", one)], 2, width=110), 4)
    return s, []


def sl_brn2():
    s = Sheet(u"SL_BRN2: цель перехода")
    pc2 = s.ref(u"PC2", 0)
    crel = s.ref(u"C_REL", 0)
    take = s.ref(u"TAKE", 0)
    # при G=TRUE (ветвление разрешено) берётся цель перехода
    # при TAKE (G=TRUE) нужна цель перехода C_REL -> она в IN1
    s.assign(u"BRN_TGT", s.blk(u"SEL", [(u"G", take), (u"IN0", pc2), (u"IN1", crel)], 2), 4)
    return s, []


def sl_brk():
    s = Sheet(u"SL_BRK: вектор прерывания")
    lo = s.ref(MEM + u".Mem[WORD#16#FFFE]", 0)
    hi = s.ref(MEM + u".Mem[WORD#16#FFFF]", 1)
    s.assign(u"BRKV", s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 2, width=110), 4)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-12s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_step8 ===")
    s, L = sl_select11()
    write(u"SL_SELECT11", pou_xml(u"SL_SELECT11", u"functionBlock",
                                  interface(inputs=[(u"ADDR_MODE", u"BYTE")] +
                                                  [(n, u"WORD") for n in CAND],
                                            outputs=[(u"EFF", u"WORD")], locals_=L),
                                  [s], u"выбор адреса"))
    s, L = sl_yw()
    write(u"SL_YW", pou_xml(u"SL_YW", u"functionBlock",
                            interface(inputs=[(u"Y", u"BYTE")],
                                      outputs=[(u"YW", u"WORD")], locals_=L),
                            [s], u"расширение Y"))
    s, L = sl_stk4()
    write(u"SL_STK4", pou_xml(u"SL_STK4", u"functionBlock",
                              interface(inputs=[(u"SPM2", u"BYTE")],
                                        outputs=[(u"STK_A3", u"WORD")], locals_=L),
                              [s], u"третий адрес стека"))
    s, L = sl_brn2()
    write(u"SL_BRN2", pou_xml(u"SL_BRN2", u"functionBlock",
                              interface(inputs=[(u"PC2", u"WORD"), (u"C_REL", u"WORD"),
                                                (u"TAKE", u"BOOL")],
                                        outputs=[(u"BRN_TGT", u"WORD")], locals_=L),
                              [s], u"цель перехода"))
    s, L = sl_brk()
    write(u"SL_BRK", pou_xml(u"SL_BRK", u"functionBlock",
                             interface(outputs=[(u"BRKV", u"WORD")], locals_=L),
                             [s], u"вектор прерывания"))
    print(u"готово")


if __name__ == "__main__":
    main()
