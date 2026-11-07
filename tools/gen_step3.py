# -*- coding: utf-8 -*-
"""
gen_step3.py -- ostalnye malye listy adresacii i PC.

Podtverzhdeno: listy v 5..24 bloka s odnorodnoy logikoy sozdayutsya stabilno
(SL_SELECT 24 bloka, SL_IND2, SL_C1A, SL_C1B, FB_Fetch, SL_IND, AR*).

  SL_REL0   OP1 -> OFFB   (znakovoe rasshirenie bajta smeshcheniya; BYTE)
  SL_REL1   OFFB, PC2 -> C_REL  (slovnoe smeshchenie)
  SL_INDP   PTR -> C_IND  (chtenie vektora po ukazatelyu)
  SL_STK1   SP -> SPM1, SPP1, SPP2, SPP3 (smezhnye znacheniya ukazatelya steka)
  SL_STK2   SP..SPP3 -> STK_A0..A2, STK_R0..R2 (adresa $0100+SP)
  SL_BRANCH COND, FZ, FC -> TAKE (uslovie vetvleniya)
  SL_PCSEL  PC_MODE + 7 kandidatov -> PC_NEW (formа SL_SELECT)
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
B0, B1, B80 = G.B0, G.B1, G.B80
W0, W1 = G.W0, G.W1


def sl_rel0():
    s = Sheet(u"SL_REL0: знаковое расширение смещения")
    op1 = s.ref(u"OP1", 0)
    sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 1))], 1)
    off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", op1),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 2))], 2))], 3)
    s.assign(u"OFFB", off, 5)
    return s, []


def sl_rel1():
    s = Sheet(u"SL_REL1: адрес перехода")
    offb = s.ref(u"OFFB", 0)
    pc2 = s.ref(u"PC2", 0)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", offb)], 1, width=140)),
                          (u"IN2", s.const(u"WORD#16#FF00", 1))], 2)
    s.assign(u"C_REL", s.blk(u"ADD", [(u"IN1", pc2), (u"IN2", offw)], 3), 5)
    return s, []


def sl_indp():
    s = Sheet(u"SL_INDP: вектор по указателю")
    ptr = s.ref(u"PTR", 0)
    ptr1 = s.blk(u"ADD", [(u"IN1", ptr), (u"IN2", s.const(W1, 1))], 1)
    s.assign(u"PTR1", ptr1, 2)
    lo = s.ref(MEM + u".Mem[PTR]", 3)
    hi = s.ref(MEM + u".Mem[PTR1]", 3)
    s.assign(u"C_IND", s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], 5, width=110), 6)
    return s, [(u"PTR1", u"WORD")]


def sl_stk1():
    s = Sheet(u"SL_STK1: соседние значения указателя стека")
    sp = s.ref(u"SP", 0)
    s.assign(u"SPM1", s.blk(u"SUB", [(u"IN1", sp), (u"IN2", s.const(B1, 1))], 1), 2)
    s.assign(u"SPP1", s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(B1, 1))], 1), 2)
    s.assign(u"SPP2", s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#2", 1))], 2), 3)
    s.assign(u"SPP3", s.blk(u"ADD", [(u"IN1", sp), (u"IN2", s.const(u"BYTE#3", 2))], 2), 3)
    return s, []


def sl_stk2():
    s = Sheet(u"SL_STK2: адреса стека $0100+SP")
    sp = s.ref(u"SP", 0)
    spm1 = s.ref(u"SPM1", 0)
    spp1 = s.ref(u"SPP1", 0)
    spp2 = s.ref(u"SPP2", 0)
    spp3 = s.ref(u"SPP3", 0)
    # (общая константа убрана: при шести потребителях CODESYS её не типизирует)

    def j(lo):
        return s.blk(u"F_Join16", [(u"LO", lo), (u"HI", s.const(B1, 2))], 2, width=110)

    s.assign(u"STK_A0", j(sp), 4)
    s.assign(u"STK_A1", j(spm1), 4)
    s.assign(u"STK_A2", j(spp1), 4)
    s.assign(u"STK_R0", j(spp1), 5)
    s.assign(u"STK_R1", j(spp2), 5)
    s.assign(u"STK_R2", j(spp3), 5)
    return s, []


def sl_branch():
    s = Sheet(u"SL_BRANCH: условие перехода")
    cond = s.ref(u"COND", 0)
    fz = s.ref(u"FZ", 0)
    fc = s.ref(u"FC", 0)
    e0 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(B0, 1))], 1)
    e1 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(B1, 1))], 1)
    e2 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#2", 1))], 1)
    e3 = s.blk(u"EQ", [(u"IN1", cond), (u"IN2", s.const(u"BYTE#3", 1))], 1)
    nz = s.blk(u"NOT", [(u"IN", fz)], 2)
    nc = s.blk(u"NOT", [(u"IN", fc)], 2)
    a0 = s.blk(u"AND", [(u"IN1", e0), (u"IN2", fz)], 2)
    a1 = s.blk(u"AND", [(u"IN1", e1), (u"IN2", nz)], 2)
    a2 = s.blk(u"AND", [(u"IN1", e2), (u"IN2", fc)], 2)
    a3 = s.blk(u"AND", [(u"IN1", e3), (u"IN2", nc)], 2)
    b01 = s.blk(u"OR", [(u"IN1", a0), (u"IN2", a1)], 4)
    b23 = s.blk(u"OR", [(u"IN1", a2), (u"IN2", a3)], 4)
    s.assign(u"TAKE", s.blk(u"OR", [(u"IN1", b01), (u"IN2", b23)], 6), 7)
    return s, []


PC_CAND = [u"P_ADV", u"P_EFF", u"P_BACK", u"P_BRN", u"P_KEEP", u"P_JRET", u"P_BRK"]
PC_CODES = [0, 1, 2, 3, 4, 5, 6]


def sl_pcsel():
    s = Sheet(u"SL_PCSEL: выбор нового PC")
    modev = s.ref(u"PC_MODE", 0)
    parts = []
    for nm, code in zip(PC_CAND, PC_CODES):
        g = s.blk(u"EQ", [(u"IN1", modev), (u"IN2", s.const(u"BYTE#%d" % code, 1))], 1)
        parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(W0, 2)),
                                    (u"IN1", s.ref(nm, 2))], 2))
    cur = parts[0]
    col = 4
    for p in parts[1:]:
        cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], col)
        col += 1
    s.assign(u"PC_NEW", cur, 8)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-11s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_step3 ===")

    s, L = sl_rel0()
    write(u"SL_REL0", pou_xml(u"SL_REL0", u"functionBlock",
                              interface(inputs=[(u"OP1", u"BYTE")],
                                        outputs=[(u"OFFB", u"BYTE")], locals_=L),
                              [s], u"знаковое расширение"))

    s, L = sl_rel1()
    write(u"SL_REL1", pou_xml(u"SL_REL1", u"functionBlock",
                              interface(inputs=[(u"OFFB", u"BYTE"), (u"PC2", u"WORD")],
                                        outputs=[(u"C_REL", u"WORD")], locals_=L),
                              [s], u"адрес перехода"))

    s, L = sl_indp()
    write(u"SL_INDP", pou_xml(u"SL_INDP", u"functionBlock",
                              interface(inputs=[(u"PTR", u"WORD")],
                                        outputs=[(u"C_IND", u"WORD")], locals_=L),
                              [s], u"вектор по указателю"))

    s, L = sl_stk1()
    write(u"SL_STK1", pou_xml(u"SL_STK1", u"functionBlock",
                              interface(inputs=[(u"SP", u"BYTE")],
                                        outputs=[(n, u"BYTE") for n in
                                                 (u"SPM1", u"SPP1", u"SPP2", u"SPP3")],
                                        locals_=L),
                              [s], u"указатель стека"))

    s, L = sl_stk2()
    write(u"SL_STK2", pou_xml(u"SL_STK2", u"functionBlock",
                              interface(inputs=[(u"SP", u"BYTE"), (u"SPM1", u"BYTE"),
                                                (u"SPP1", u"BYTE"), (u"SPP2", u"BYTE"),
                                                (u"SPP3", u"BYTE")],
                                        outputs=[(n, u"WORD") for n in
                                                 (u"STK_A0", u"STK_A1", u"STK_A2",
                                                  u"STK_R0", u"STK_R1", u"STK_R2")],
                                        locals_=L),
                              [s], u"адреса стека"))

    s, L = sl_branch()
    write(u"SL_BRANCH", pou_xml(u"SL_BRANCH", u"functionBlock",
                                interface(inputs=[(u"COND", u"BYTE"), (u"FZ", u"BOOL"),
                                                  (u"FC", u"BOOL")],
                                          outputs=[(u"TAKE", u"BOOL")], locals_=L),
                                [s], u"условие перехода"))

    s, L = sl_pcsel()
    write(u"SL_PCSEL", pou_xml(u"SL_PCSEL", u"functionBlock",
                               interface(inputs=[(u"PC_MODE", u"BYTE")] +
                                               [(n, u"WORD") for n in PC_CAND],
                                         outputs=[(u"BRN_TGT", u"WORD")], locals_=L),
                               [s], u"выбор PC"))
    print(u"готово")


if __name__ == "__main__":
    main()
