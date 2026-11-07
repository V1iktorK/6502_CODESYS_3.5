# -*- coding: utf-8 -*-
"""
gen_addrvar.py -- VARIANTY FB_AddrMode dlya DELTA-OTLADKI UDALENIEM.

Bisekciya po elementam dala lozhnyy otvet (granica na trivиальной konstante),
poetomu menyaem metod: ne "chto dobavit, chtoby slomalos", a "chto UBRAT, chtoby
zarabotalo". Kazhdyy variant -- polnocennaya shema s chastyu funkcii.

  A0 MINIMAL     rezhimy + AB (F_Join16) + WDATA := Mem[EFF] + vyhody-konstanty
  A2 NO_TREE     bez dereva SEL: EFF := AB
  A3 NO_INDIRECT bez kosvennyh tsepochek (izx/izy); dlya nih bеretsya AB
  A4 NO_JOIN     bez F_Join16: skleit bajty cherez BYTE_TO_WORD + ADD
  A1 NO_MEM      bez chteniya pamyati voobshche (OP1/OP2 vmesto Mem[...])
  A5 FULL        polnaya shema (izvestno, chto veшает) -- poetomu POSLEDNIY
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbd import Sheet, interface, pou_xml, or_tree_bool
from opcodes import OPCODES, MODE_CODE
import gen_cpu_split as G

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
OUT = os.path.join(ROOT, "plcopen")

CPU, MEM = G.CPU, G.MEM
B0, B1, B2, B3 = G.B0, G.B1, G.B2, G.B3
B80 = G.B80
W0, W1 = G.W0, G.W1
T, F = G.T, G.F
MODES = G.MODES
EQv, ANDb, SELb, ORB, ORT, CAT = G.EQv, G.ANDb, G.SELb, G.ORB, G.ORT, G.CAT


def join(s, lo, hi, col, no_join):
    if no_join:
        return s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", hi)], col, width=140)),
                              (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", lo)], col, width=140))], col)
    return s.blk(u"F_Join16", [(u"LO", lo), (u"HI", hi)], col, width=110)


def build(no_tree=False, no_indirect=False, no_mem=False, no_join=False):
    s = Sheet(u"FB_AddrMode: вариант")
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)
    pc2 = s.ref(u"PC2", 0)
    modev = s.ref(u"ADDR_MODE", 0)

    mg = {}
    for m in MODES:
        mg[m] = EQv(s, modev, u"BYTE#%d" % MODE_CODE[m], 1)

    AB = join(s, op1, op2, 4, no_join)

    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 3)
    zpy = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", y)], 3)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 4, width=140)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 4, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 4, width=140)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 5, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 5, width=120)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 6)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 6)

    if no_indirect:
        izx = izy = AB
    else:
        izx_ptr = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 5, width=140)
        izx_ptr1 = s.blk(u"ADD", [(u"IN1", izx_ptr), (u"IN2", s.const(W1, 5))], 6)
        s.assign(u"IZX_PTR", izx_ptr, 6)
        s.assign(u"IZX_PTR1", izx_ptr1, 6)
        izx_lo = s.ref((op1 if no_mem else MEM + u".Mem[IZX_PTR]"), 7)
        izx_hi = s.ref((op2 if no_mem else MEM + u".Mem[IZX_PTR1]"), 7)
        izx = join(s, izx_lo, izx_hi, 8, no_join)

        izy_ptr = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 5, width=140)
        izy_ptr1 = s.blk(u"ADD", [(u"IN1", izy_ptr), (u"IN2", s.const(W1, 5))], 6)
        s.assign(u"IZY_PTR", izy_ptr, 6)
        s.assign(u"IZY_PTR1", izy_ptr1, 6)
        izy_lo = s.ref((op1 if no_mem else MEM + u".Mem[IZY_PTR]"), 7)
        izy_hi = s.ref((op2 if no_mem else MEM + u".Mem[IZY_PTR1]"), 8)
        izy = s.blk(u"ADD", [(u"IN1", join(s, izy_lo, izy_hi, 8, no_join)),
                             (u"IN2", yw)], 9)

    sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 6))], 6)
    off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", op1),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 7))], 7))], 8)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 8, width=140)),
                          (u"IN2", s.const(u"WORD#16#FF00", 8))], 9)
    relw = s.blk(u"ADD", [(u"IN1", pc2), (u"IN2", offw)], 10)

    if no_mem:
        brk_v = s.const(W0, 10)
    else:
        brk_lo = s.ref(MEM + u".Mem[WORD#16#FFFE]", 7)
        brk_hi = s.ref(MEM + u".Mem[WORD#16#FFFF]", 8)
        brk_v = join(s, brk_lo, brk_hi, 10, no_join)

    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 9))], 10)

    if no_tree:
        s.assign(u"EFF", AB, 12)
        eff = AB
    else:
        cands = [(mg[u"imm"], imm_w), (mg[u"zp"], zpw), (mg[u"zpx"], zpxw), (mg[u"zpy"], zpyw),
                 (mg[u"abs"], AB), (mg[u"abx"], abx), (mg[u"aby"], aby),
                 (mg[u"izx"], izx), (mg[u"izy"], izy), (mg[u"ind"], izx), (mg[u"stk"], AB)]
        wp = [SELb(s, g, s.const(W0, 11), c, 11) for g, c in cands]
        eff = ORT(s, wp, 13)
        s.assign(u"EFF", eff if eff is not None else AB, 15)

    if no_mem:
        s.assign(u"WDATA", op1, 17)
    else:
        mem_rd = s.ref(MEM + u".Mem[EFF]", 14)
        s.assign(u"WDATA", SELb(s, mg[u"imm"], mem_rd, op1, 16), 17)

    s.assign(u"REL_DEST", relw, 17)
    s.assign(u"BRK_VEC", brk_v, 17)

    L = []
    if not no_indirect:
        L = [(u"IZX_PTR", u"WORD"), (u"IZX_PTR1", u"WORD"),
             (u"IZY_PTR", u"WORD"), (u"IZY_PTR1", u"WORD")]
    return s, L


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-18s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_addrvar ===")
    variants = [
        (u"AV0_MINIMAL", dict(no_tree=True, no_indirect=True, no_mem=True, no_join=True)),
        (u"AV2_NO_TREE", dict(no_tree=True)),
        (u"AV3_NO_IND", dict(no_indirect=True)),
        (u"AV4_NO_JOIN", dict(no_join=True)),
        (u"AV1_NO_MEM", dict(no_mem=True)),
        (u"AV5_FULL", dict()),
    ]
    for name, kw in variants:
        s, L = build(**kw)
        xml = pou_xml(name, u"functionBlock",
                      interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                                        (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD"),
                                        (u"ADDR_MODE", u"BYTE")],
                                outputs=[(u"EFF", u"WORD"), (u"WDATA", u"BYTE"),
                                         (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD")],
                                locals_=L),
                      [s], u"вариант адресации")
        write(name, xml)
    print(u"готово")


if __name__ == "__main__":
    main()
