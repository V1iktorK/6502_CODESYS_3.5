# -*- coding: utf-8 -*-
"""
gen_carry.py -- stupen SL_CARRY: perenos iz ALU ploskoy logikoy.

Pochemu otdelnyy POU: vnutri FB_ALU6502 perenos schitalsya cherez
c1 = (s1 < AX) i c2 = cin AND (s2 < s1). Etie LT-vetvi vlozheny v SEL i v
etom liste CODESYS ih ne dorasschityvaet -- C nikogda ne stanovilsya 1
(ADC/SBC/CMP). Zdes schet idet cherez 16-bitovuyu summu: odin ADD na WORD,
odin GT -- nikakih vlozhennyh SEL.

    sW   = AX + BX + (CIN ? 1 : 0)
    CARRY = sW > 255
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
    s = Sheet(u"SL_CARRY: перенос из суммы двух операндов")
    s.add_comment(u"CARRY := (AX + BX + CIN) > 255")
    ax = s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(CPU + u".ALU_AX", 0))], 1, width=140)
    bx = s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(CPU + u".ALU_BX", 0))], 1, width=140)
    cin = s.blk(u"SEL", [(u"G", s.ref(CPU + u".ALU_CIN", 0)),
                         (u"IN0", s.const(u"WORD#0", 1)),
                         (u"IN1", s.const(u"WORD#1", 1))], 2)
    w1 = s.blk(u"ADD", [(u"IN1", ax), (u"IN2", bx)], 3)
    w2 = s.blk(u"ADD", [(u"IN1", w1), (u"IN2", cin)], 4)
    s.assign(CPU + u".CARRY",
             s.blk(u"GT", [(u"IN1", w2), (u"IN2", s.const(u"WORD#255", 4))], 5), 6)
    return s


def main():
    print(u"=== gen_carry ===")
    x = pou_xml(u"SL_CARRY", u"functionBlock", interface(), [build()],
                comment=u"перенос из АЛУ")
    p = os.path.join(OUT, u"SL_CARRY.xml")
    with io.open(p, "wb") as f:
        f.write(x.encode("utf-8"))
    print(u"  SL_CARRY  %8d байт" % os.path.getsize(p))


if __name__ == u"__main__":
    main()
