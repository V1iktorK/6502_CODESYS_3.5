# -*- coding: utf-8 -*-
"""
gen_wdata.py -- stupen SL_WDATA2: otkuda brat operand WDATA.

Pravilo MOS 6502: dlya neposredstvennoy adresacii (ADDR_MODE=1) operand --
eto vtoroy bayt komandy (OP1), dlya vseh ostalnyh rezhimov -- yacheyka
pamyati po effektivnomu adresu (Mem[EFF]).

Ranshe eta stupen bila sdelana ruchnoy XML-pravkoy i vney selektor byl
PEREVERNUT: pri ADDR_MODE=1 chitalis Mem[EFF], inache OP1. Iz-za etogo
LDA zp / LDA abs davali musor. Teper stupen generiruetsya zanovo, i
soglashenie SEL odno na ves proekt: G=TRUE -> IN1.
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
CPU = u"GVL_CPU"


def build():
    s = Sheet(u"SL_WDATA2: операнд (непосредственный или из памяти)")
    s.add_comment(u"WDATA := (ADDR_MODE = 1) ? OP1 : Mem[EFF]")
    am = s.ref(u"ADDR_MODE", 0)
    imm = s.blk(u"EQ", [(u"IN1", am), (u"IN2", s.const(u"BYTE#1", 1))], 2)
    mem_rd = s.ref(MEM + u".Mem[EFF]", 2)
    op1 = s.ref(u"OP1", 0)
    # SEL: G=TRUE берёт IN1 -> для непосредственной адресации IN1 = OP1
    wd = s.blk(u"SEL", [(u"G", imm), (u"IN0", mem_rd), (u"IN1", op1)], 4)
    s.assign(CPU + u".WDATA", wd, 6)
    return s


def main():
    print(u"=== gen_wdata ===")
    s = build()
    x = pou_xml(u"SL_WDATA2", u"functionBlock",
                interface(inputs=[(u"ADDR_MODE", u"BYTE"), (u"EFF", u"WORD"),
                                  (u"OP1", u"BYTE")]), [s],
                comment=u"операнд команды")
    p = os.path.join(OUT, u"SL_WDATA2.xml")
    f = io.open(p, "wb")
    f.write(x.encode("utf-8"))
    f.close()
    print(u"  SL_WDATA2        %8d байт" % os.path.getsize(p))


if __name__ == "__main__":
    main()
