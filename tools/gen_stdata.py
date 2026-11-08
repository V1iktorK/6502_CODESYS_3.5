# -*- coding: utf-8 -*-
"""
gen_stdata.py -- stupen SL_STDATA: chto imenno kladetsya v stek (port 0).

    STK_D0 := IS_JSR ? PCH : REG_WR

Pochemu otdelnyy POU: sloy FB_CPU_Store ispolzuet STK_D0 kak vhod dlya WRD0,
a zapis" i chtenie odnoi yacheiki v odnom POU daet STAROE znachenie
(pravilo 2.5) -- iz-za etogo PHA tolkala v stek znachenie proshlogo takta.
Stupen idet posle FB_CPU_PcWb (tam poyavlyaetsya REG_WR) i do FB_CPU_Store.
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


def build():
    s = Sheet(u"SL_STDATA: данные порта 0 стека")
    s.add_comment(u"STK_D0 := IS_JSR ? PCH : REG_WR")
    s.assign(CPU + u".STK_D0",
             s.blk(u"SEL", [(u"G", s.ref(CPU + u".IS_JSR", 0)),
                            (u"IN0", s.ref(CPU + u".REG_WR", 1)),
                            (u"IN1", s.ref(CPU + u".PCH", 1))], 2), 3)
    return s


def main():
    print(u"=== gen_stdata ===")
    x = pou_xml(u"SL_STDATA", u"functionBlock", interface(), [build()],
                comment=u"данные стека")
    p = os.path.join(OUT, u"SL_STDATA.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_STDATA  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
