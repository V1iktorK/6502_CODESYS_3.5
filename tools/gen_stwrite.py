# -*- coding: utf-8 -*-
"""gen_stwrite.py -- stupen SL_STWRITE: zapis' treh portov v pamyat'.

    Mem[ADR0] := EN0 ? DAT0 : Mem[ADR0]

POCHEMU ADRES -- VHODNOY PIN, A NE GVL-PEREMENNAYA (proverено eksperimentalno):
    GVL_MEM.Mem[1024]  := ...        -- rabotaet (adres-konstanta)
    GVL_MEM.Mem[GVL_CPU.WR0] := ...  -- NE rabotaet (indeks iz GVL)
    GVL_MEM.Mem[ADR0]  := ...        -- rabotaet, esli ADR0 -- peremennaya POU
To est' zapis' v massiv po indeksu iz GLOBALNOY peremennoy molcha teryaetsya
(konspekt 2.4), a po indeksu-vhodu POU -- prohodit.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")
MEM = u"GVL_MEM"


def build():
    s = Sheet(u"SL_STWRITE: запись трёх портов в память")
    s.add_comment(u"Mem[ADRn] := ENn ? DATn : Mem[ADRn]")
    for k, col in ((0, 1), (1, 3), (2, 5)):
        addr = u"%s.Mem[ADR%d]" % (MEM, k)
        s.assign(addr, s.blk(u"SEL", [(u"G", s.ref(u"EN%d" % k, col)),
                                      (u"IN0", s.ref(addr, col)),
                                      (u"IN1", s.ref(u"DAT%d" % k, col))], col + 1),
                 col + 2)
    return s


def main():
    print(u"=== gen_stwrite ===")
    ins = []
    for k in range(3):
        ins += [(u"ADR%d" % k, u"WORD"), (u"DAT%d" % k, u"BYTE"), (u"EN%d" % k, u"BOOL")]
    x = pou_xml(u"SL_STWRITE", u"functionBlock", interface(inputs=ins), [build()],
                comment=u"запись в память")
    p = os.path.join(OUT, u"SL_STWRITE.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_STWRITE  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
