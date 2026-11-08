# -*- coding: utf-8 -*-
"""
gen_select.py -- stupen SL_SELECT12: effektivnyy adres EFF po rezhimu adresacii.

    EFF := OR po k ( (ADDR_MODE=k) ? KANDIDAT_k : 0 )

Kody rezhimov (opcodes.MODES): 0 imp, 1 imm, 2 zp, 3 zpx, 4 zpy, 5 abs,
6 abx, 7 aby, 8 izx, 9 izy, 10 ind, 11 rel, 12 stk.

Ran'she eta stupen bila ruchnoy XML-pravkoy bez generatora, i rezhim 10 (ind,
to est JMP ($xxxx)) ne imel kandidata: EFF poluchalsya 0, i JMP (ind) uhodil
na adres 0 -- test T090/T091. Teper stupen generiruetsya i karta rezhimov
yavno zadanа.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
CPU = u"GVL_CPU"

# (kod rezhima, imya vhoda-kandidata)
MAP = [(0, u"C_IMM"), (1, u"C_IMM"), (2, u"C_ZP"), (3, u"C_ZPX"),
       (4, u"C_ZPY"), (5, u"C_ABS"), (6, u"C_ABX"), (7, u"C_ABY"),
       (8, u"C_IZX"), (9, u"C_IZY"), (10, u"C_IND"), (11, u"C_REL"),
       (12, u"C_STK")]
IN_NAMES = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX",
            u"C_ABY", u"C_IZX", u"C_IZY", u"C_IND", u"C_REL", u"C_STK"]


def ortree(s, ids, col):
    """Дерево обычных блоков OR (для BYTE/WORD; or_tree_bool годится только
    для BOOL — он собран на SEL и даёт ошибки типов на байтах и словах)."""
    ids = [i for i in ids if i is not None]
    if not ids:
        return s.const(u"WORD#0", col)
    cur, c = list(ids), col
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur) - 1, 2):
            nxt.append(s.blk(u"OR", [(u"IN1", cur[j]), (u"IN2", cur[j + 1])], c))
        if len(cur) % 2:
            nxt.append(cur[-1])
        cur, c = nxt, c + 1
    return cur[0]

def build():
    s = Sheet(u"SL_SELECT12: эффективный адрес по режиму адресации")
    s.add_comment(u"EFF := кандидат, выбранный кодом ADDR_MODE")
    parts = []
    for code, nm in MAP:
        g = s.blk(u"EQ", [(u"IN1", s.ref(u"ADDR_MODE", 0)),
                          (u"IN2", s.const(u"BYTE#%d" % code, 0))], 2)
        parts.append(s.blk(u"SEL", [(u"G", g),
                                    (u"IN0", s.const(u"WORD#0", 3)),
                                    (u"IN1", s.ref(nm, 3))], 3))
    s.assign(u"EFF", ortree(s, parts, 6), 8)
    return s


def main():
    print(u"=== gen_select ===")
    x = pou_xml(u"SL_SELECT12", u"functionBlock",
                interface(inputs=[(u"ADDR_MODE", u"BYTE")] +
                          [(n, u"WORD") for n in IN_NAMES],
                          outputs=[(u"EFF", u"WORD")]), [build()],
                comment=u"эффективный адрес")
    p = os.path.join(OUT, u"SL_SELECT12.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_SELECT12  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
