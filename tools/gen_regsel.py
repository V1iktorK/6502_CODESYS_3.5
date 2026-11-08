# -*- coding: utf-8 -*-
"""
gen_regsel.py -- stupen SL_REGSEL: kakoj registr pishetsya (REG_WR).

    REG_WR := (SRC=0 ? A : SRC=1 ? X : SRC=2 ? Y : SRC=3 ? P_NEW :
               SRC=4 ? ALU_R : SRC=5 ? PCL : SRC=6 ? PCH : SRC=7 ? PULL_LO : 0)

Pochemu otdelnyy POU: REG_WR nuzhen srazu neskolkim potrebitelyam (stek,
fayly, zapis' registrov). Esli schitat' ego vnutri sloya, kotoryy potom sam
zhe chitaet rezultat, CODESYS otdast znachenie proshlogo skana (pravilo 2.5),
i naprimer STX (SRC=1) pisal v pamyat' 0, a PHA tolkala starye dannye.
Zdes vse vhody -- vyhodnye velichiny drugih POU, poetoму znachenie svezhee.

Sdelano ploskym ob'edineniem (rovno odno uslovie istinno):
    REG_WR = OR po k ( (SRC=k) ? istochnik_k : 0 )
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

SRCS = [0, 1, 2, 3, 4, 5, 6, 7]
NAMES = [u"A", u"X", u"Y", u"P_NEW", u"ALU_R", u"PCL", u"PCH", u"PULL_LO"]


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
    s = Sheet(u"SL_REGSEL: источник записи регистров")
    s.add_comment(u"REG_WR := источник по коду SRC")
    src = s.ref(CPU + u".SRC", 0)
    parts = []
    for k, nm in zip(SRCS, NAMES):
        g = s.blk(u"EQ", [(u"IN1", s.ref(CPU + u".SRC", 1)),
                          (u"IN2", s.const(u"BYTE#%d" % k, 1))], 2)
        parts.append(s.blk(u"SEL", [(u"G", g),
                                    (u"IN0", s.const(u"BYTE#0", 3)),
                                    (u"IN1", s.ref(CPU + u"." + nm, 3))], 3))
    s.assign(CPU + u".REG_WR", ortree(s, parts, 6), 8)
    return s


def main():
    print(u"=== gen_regsel ===")
    x = pou_xml(u"SL_REGSEL", u"functionBlock", interface(), [build()],
                comment=u"выбор источника записи")
    p = os.path.join(OUT, u"SL_REGSEL.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_REGSEL  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
