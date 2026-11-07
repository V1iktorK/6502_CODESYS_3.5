# -*- coding: utf-8 -*-
"""
gen_diag2.py -- proverka SEL v RUNTIME.

Deshifrator: BOOL-signaly verny (LD_A=TRUE), a vse BYTE-signaly nulevye,
hotya oni stroyatsya cherez SEL+OR. Provеryaem sam SEL:
  C_IMM := SEL(G=TRUE, IN0=BYTE#0, IN1=BYTE#1)   -- konstanty
  C_STK := SEL(G=TRUE, IN0=BYTE#0, IN1=OPs)      -- peremennaya
  C_ABY := OR(BYTE#16#04, BYTE#16#08)            -- OR konstant
  C_REL := BYTE_TO_WORD(OPs)                     -- kontrol't tipov
Chtenie -- v test_diag.py (spisok znacheniy rasshiren).
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
    print(u"=== gen_diag2 ===")
    s = Sheet(u"PLC_PRG: проверка SEL в рантайме")
    s.add_comment(u"Проверяем SEL по константам и по переменной, OR и преобразование")
    t = s.const(u"TRUE", 0)
    s.assign(u"GVL_CPU.C_IMM",
             s.blk(u"SEL", [(u"G", t), (u"IN0", s.const(u"BYTE#0", 1)),
                            (u"IN1", s.const(u"BYTE#1", 1))], 2), 4)
    s.assign(u"GVL_CPU.C_STK",
             s.blk(u"SEL", [(u"G", s.ref(u"TRUE", 0)),
                            (u"IN0", s.const(u"BYTE#0", 3)),
                            (u"IN1", s.ref(u"GVL_CPU.OPs", 3))], 4), 6)
    s.assign(u"GVL_CPU.C_ABY",
             s.blk(u"OR", [(u"IN1", s.const(u"BYTE#16#04", 5)),
                           (u"IN2", s.const(u"BYTE#16#08", 5))], 6), 8)
    s.assign(u"GVL_CPU.C_REL",
             s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"GVL_CPU.OPs", 7))], 8, width=140), 10)
    xml = pou_xml(u"PLC_PRG", u"program", interface(locals_=[]), [s],
                  u"проверка SEL")
    p = os.path.join(OUT, u"PRG_DIAG.xml")
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  PRG_DIAG %d байт" % os.path.getsize(p))


if __name__ == "__main__":
    main()
