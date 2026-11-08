# -*- coding: utf-8 -*-
"""
gen_stwrite.py -- stupen SL_STWRITE: fakticheskaya zapis v pamyat.

Pochemu otdelnyy POU: sloy FB_CPU_Store tolko VYCHISLYAET WR0/WRD0/WR_EN0
(i porty 1 i 2). Chtenie etih zhe yacheek v tom zhe POU, gde oni zapisany,
daet STAROE znachenie (pravilo 2.5) -- poetoму zapis v pamyat' vyhnositsya
v sleduyuschuyu stupen'. Ona chitaet tolko to, chto zapisal predyduschiy POU
v etom zhe skane, i eto rabotaet (proverено na konveyere shagov).

    Mem[WR0] := WR_EN0 ? WRD0 : Mem[WR0]   -- obydhchnaya zapis / stek
    Mem[WR1] := WR_EN1 ? WRD1 : Mem[WR1]   -- JSR/BRK: PCL ili PCH
    Mem[WR2] := WR_EN2 ? WRD2 : Mem[WR2]   -- BRK: PCL
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
MEM = u"GVL_MEM"


def build():
    s = Sheet(u"SL_STWRITE: запись трёх портов в память")
    s.add_comment(u"Mem[WRn] := WR_ENn ? WRDn : Mem[WRn]")
    for k, col in ((0, 1), (1, 3), (2, 5)):
        addr = u"%s.Mem[%s.WR%d]" % (MEM, CPU, k)
        cur = s.ref(addr, col)
        new = s.ref(u"%s.WRD%d" % (CPU, k), col)
        en = s.ref(u"%s.WR_EN%d" % (CPU, k), col)
        s.assign(addr, s.blk(u"SEL", [(u"G", en), (u"IN0", cur), (u"IN1", new)],
                             col + 1), col + 2)
    return s


def main():
    print(u"=== gen_stwrite ===")
    x = pou_xml(u"SL_STWRITE", u"functionBlock", interface(), [build()],
                comment=u"запись в память")
    p = os.path.join(OUT, u"SL_STWRITE.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_STWRITE  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
