# -*- coding: utf-8 -*-
"""
gen_diag.py -- diagnostika deshifratora: PLC_PRG podaet konstantu $A9.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")


def main():
    print(u"=== gen_diag ===")
    s = Sheet(u"PLC_PRG: диагностика дешифратора")
    s.add_comment(u"На дешифратор подаётся константа $A9 (LDA #imm)")
    s.blk(u"FB_Decoder6502", [(u"Op", s.const(u"BYTE#16#A9", 0))], 2, width=170,
          inst=u"Dec")
    xml = pou_xml(u"PLC_PRG", u"program",
                  interface(locals_=[(u"Dec", u"FB_Decoder6502")]),
                  [s], u"диагностика дешифратора")
    p = os.path.join(OUT, u"PRG_DIAG.xml")
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  PRG_DIAG %d байт" % os.path.getsize(p))


if __name__ == "__main__":
    main()
