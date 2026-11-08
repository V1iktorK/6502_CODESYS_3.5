# -*- coding: utf-8 -*-
"""
gen_step7.py -- poslednie vspomogatelnye listy pered kompoziciey.

  SL_RELC   OFFW, PC2 -> C_REL            (1 ADD)
  SL_ADV    PCs, LEN  -> ADV              (BYTE_TO_WORD + ADD)
  SL_JRET   STK_R0, STK_R1 -> JRET, BACK  (chtenie pamyati + F_Join16 + ADD)
  SL_STK3   SP -> SPM2, SPM3              (SP-2, SP-3)
  SL_SPSEL  SP_MODE + 5 kandidatov -> SP_NEW  (formа SL_SELECT)
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
W0, W1 = G.W0, G.W1

SP_CAND = [u"S_KEEP", u"S_P1", u"S_M1", u"S_M2", u"S_P2", u"S_M3", u"S_P3"]
# Коды SP_MODE из opcodes.py: 0 нет, 1 push1, 2 pull1, 3 push2 (JSR),
# 4 pull2 (RTS), 5 push3 (BRK), 6 pull3 (RTI). Раньше кодов 3 и 4 здесь не было
# вовсе, и при JSR/RTS SP_NEW собирался как 0 (все кандидаты давали 0).
SP_CODES = [0, 1, 2, 3, 4, 5, 6]


def sl_relc():
    s = Sheet(u"SL_RELC: адрес перехода")
    offw = s.ref(u"OFFW", 0)
    pc2 = s.ref(u"PC2", 0)
    s.assign(u"C_REL", s.blk(u"ADD", [(u"IN1", pc2), (u"IN2", offw)], 1), 3)
    return s, []


def sl_adv():
    s = Sheet(u"SL_ADV: адрес следующей команды")
    pcs = s.ref(u"PCs", 0)
    lenv = s.ref(u"LEN", 0)
    w = s.blk(u"BYTE_TO_WORD", [(u"IN", lenv)], 1, width=140)
    s.assign(u"ADV", s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", w)], 2), 4)
    return s, []


def sl_jret():
    s = Sheet(u"SL_JRET: адрес возврата из подпрограммы")
    lo = s.ref(MEM + u".Mem[STK_R0]", 0)
    hi = s.ref(MEM + u".Mem[STK_R1]", 1)
    jret = s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 2, width=110)
    s.assign(u"JRET", jret, 4)
    s.assign(u"BACK", s.blk(u"ADD", [(u"IN1", jret), (u"IN2", s.const(W1, 3))], 3), 5)
    return s, []


def sl_stk3():
    s = Sheet(u"SL_STK3: нижние смещения указателя стека")
    sp = s.ref(u"SP", 0)
    s.assign(u"SPM2", s.blk(u"SUB", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#2", 1))], 1), 2)
    s.assign(u"SPM3", s.blk(u"SUB", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#3", 1))], 1), 2)
    return s, []


def sl_spsel():
    s = Sheet(u"SL_SPSEL: новый указатель стека")
    modev = s.ref(u"SP_MODE", 0)
    parts = []
    for nm, code in zip(SP_CAND, SP_CODES):
        g = s.blk(u"EQ", [(u"IN1", modev), (u"IN2", s.const(u"BYTE#%d" % code, 1))], 1)
        parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(u"BYTE#0", 2)),
                                    (u"IN1", s.ref(nm, 2))], 2))
    cur = parts[0]
    col = 4
    for p in parts[1:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], col)
        col += 1
    s.assign(u"SP_NEW", cur, 8)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-9s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_step7 ===")
    s, L = sl_relc()
    write(u"SL_RELC", pou_xml(u"SL_RELC", u"functionBlock",
                              interface(inputs=[(u"OFFW", u"WORD"), (u"PC2", u"WORD")],
                                        outputs=[(u"C_REL", u"WORD")], locals_=L),
                              [s], u"адрес перехода"))
    s, L = sl_adv()
    write(u"SL_ADV", pou_xml(u"SL_ADV", u"functionBlock",
                             interface(inputs=[(u"PCs", u"WORD"), (u"LEN", u"BYTE")],
                                       outputs=[(u"ADV", u"WORD")], locals_=L),
                             [s], u"следующая команда"))
    s, L = sl_jret()
    write(u"SL_JRET", pou_xml(u"SL_JRET", u"functionBlock",
                              interface(inputs=[(u"STK_R0", u"WORD"), (u"STK_R1", u"WORD")],
                                        outputs=[(u"JRET", u"WORD"), (u"BACK", u"WORD")],
                                        locals_=L),
                              [s], u"адрес возврата"))
    s, L = sl_stk3()
    write(u"SL_STK3", pou_xml(u"SL_STK3", u"functionBlock",
                              interface(inputs=[(u"SP", u"BYTE")],
                                        outputs=[(u"SPM2", u"BYTE"), (u"SPM3", u"BYTE")],
                                        locals_=L),
                              [s], u"нижние смещения"))
    s, L = sl_spsel()
    write(u"SL_SPSEL", pou_xml(u"SL_SPSEL", u"functionBlock",
                               interface(inputs=[(u"SP_MODE", u"BYTE")] +
                                               [(n, u"BYTE") for n in SP_CAND],
                                         outputs=[(u"SP_NEW", u"BYTE")], locals_=L),
                               [s], u"новый указатель стека"))
    print(u"готово")


if __name__ == "__main__":
    main()
