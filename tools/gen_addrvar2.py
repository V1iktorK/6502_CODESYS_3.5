# -*- coding: utf-8 -*-
"""
gen_addrvar2.py -- LESTNICA ot trivиального k polnomu (konstruktivnyy metod).

Delta-otladka udaleniem ne dala minimuma: variant AV0_MINIMAL (~26 KB) tozhe
veшает. Poetomu idem s drugoy storony -- nachinaem s shemy iz 4 blokov i
dobavlyaem uzly po odnomu, chtoby poymat PERVUYU dobavku, lomayushchuyu import.

  AV10  bazа: EFF := F_Join16(OP1,OP2); WDATA := OP1; REL_DEST := 0; BRK_VEC := 0
  AV11  + 13 sravneniy ADDR_MODE (nizhe nikem ne ispolzuyutsya)
  AV12  + arifmetika adresov (zp/zpy/zpxw/zpyw/xw/yw/abx/aby), poka ne podklyuchena
  AV13  + relative (sgn/off/offw/relw) -> REL_DEST := relw
  AV14  + kosvennye cepochki (izx, izy) s chteniem pamyati, poka ne podklyucheny
  AV15  AV12 + derevo SEL/ORT -> EFF (bez relative i kosvennyh)
  AV16  polnaya (izvestno, chto veшает) -- posledniy
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
CPU, MEM = G.CPU, G.MEM
B0, B1, B80 = G.B0, G.B1, G.B80
W0, W1 = G.W0, G.W1
MODES = G.MODES
EQv, SELb, ORT = G.EQv, G.SELb, G.ORT


def base(s):
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    AB = s.blk(u"F_Join16", [(u"LO", op1), (u"HI", op2)], 4, width=110)
    s.assign(u"EFF", AB, 6)
    s.assign(u"WDATA", op1, 6)
    s.assign(u"REL_DEST", s.const(W0, 6), 6)
    s.assign(u"BRK_VEC", s.const(W0, 6), 6)
    return dict(op1=op1, op2=op2, x=s.ref(u"X", 0), y=s.ref(u"Y", 0),
                pcs=s.ref(u"PCs", 0), pc2=s.ref(u"PC2", 0),
                modev=s.ref(u"ADDR_MODE", 0), AB=AB)


def add_modes(s, d):
    mg = {}
    for m in MODES:
        mg[m] = EQv(s, d["modev"], u"BYTE#%d" % G.MODE_CODE[m], 1)
    return mg


def add_arith(s, d):
    zp = s.blk(u"ADD", [(u"IN1", d["op1"]), (u"IN2", d["x"])], 3)
    zpy = s.blk(u"ADD", [(u"IN1", d["op1"]), (u"IN2", d["y"])], 3)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", d["op1"])], 4, width=140)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 4, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 4, width=140)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", d["x"])], 5, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", d["y"])], 5, width=120)
    abx = s.blk(u"ADD", [(u"IN1", d["AB"]), (u"IN2", xw)], 6)
    aby = s.blk(u"ADD", [(u"IN1", d["AB"]), (u"IN2", yw)], 6)
    d.update(zp=zp, zpy=zpy, zpw=zpw, zpxw=zpxw, zpyw=zpyw, xw=xw, yw=yw,
             abx=abx, aby=aby)


def add_relative(s, d):
    op1 = d["op1"]
    sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 6))], 6)
    off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", op1),
                         (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 7))], 7))], 8)
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 8, width=140)),
                          (u"IN2", s.const(u"WORD#16#FF00", 8))], 9)
    relw = s.blk(u"ADD", [(u"IN1", d["pc2"]), (u"IN2", offw)], 10)
    s.assign(u"REL_DEST", relw, 12)


def add_indirect(s, d):
    s.assign(u"IZX_PTR", s.blk(u"BYTE_TO_WORD", [(u"IN", d["zp"])], 5, width=140), 6)
    s.assign(u"IZX_PTR1", s.blk(u"ADD", [(u"IN1", s.ref(u"IZX_PTR", 6)),
                                         (u"IN2", s.const(W1, 6))], 6), 7)
    izx_lo = s.ref(MEM + u".Mem[IZX_PTR]", 7)
    izx_hi = s.ref(MEM + u".Mem[IZX_PTR1]", 7)
    izx = s.blk(u"F_Join16", [(u"LO", izx_lo), (u"HI", izx_hi)], 8, width=110)
    s.assign(u"IZY_PTR", s.blk(u"BYTE_TO_WORD", [(u"IN", d["op1"])], 5, width=140), 6)
    s.assign(u"IZY_PTR1", s.blk(u"ADD", [(u"IN1", s.ref(u"IZY_PTR", 6)),
                                         (u"IN2", s.const(W1, 6))], 6), 7)
    izy_lo = s.ref(MEM + u".Mem[IZY_PTR]", 7)
    izy_hi = s.ref(MEM + u".Mem[IZY_PTR1]", 8)
    izy = s.blk(u"ADD", [(u"IN1", s.blk(u"F_Join16", [(u"LO", izy_lo), (u"HI", izy_hi)], 8, width=110)),
                         (u"IN2", d["yw"])], 9)
    d.update(izx=izx, izy=izy)


def add_tree(s, d, mg):
    imm_w = s.blk(u"ADD", [(u"IN1", d["pcs"]), (u"IN2", s.const(W1, 9))], 10)
    cands = [(mg[u"imm"], imm_w), (mg[u"zp"], d["zpw"]), (mg[u"zpx"], d["zpxw"]),
             (mg[u"zpy"], d["zpyw"]), (mg[u"abs"], d["AB"]), (mg[u"abx"], d["abx"]),
             (mg[u"aby"], d["aby"]), (mg[u"izx"], d.get(u"izx", d["AB"])),
             (mg[u"izy"], d.get(u"izy", d["AB"])), (mg[u"ind"], d.get(u"izx", d["AB"])),
             (mg[u"stk"], d["AB"])]
    wp = [SELb(s, g, s.const(W0, 11), c, 11) for g, c in cands]
    ef = ORT(s, wp, 13)
    s.assign(u"EFF", ef, 15)


def build(level):
    s = Sheet(u"FB_AddrMode: вариант %d" % level)
    d = base(s)
    mg = None
    if level >= 11:
        mg = add_modes(s, d)
    if level >= 12 or level == 16:
        add_arith(s, d)
    if level == 13:
        add_relative(s, d)
    if level == 14:
        add_indirect(s, d)
    if level == 15:
        add_tree(s, d, mg)
    if level == 16:
        add_relative(s, d)
        add_indirect(s, d)
        add_tree(s, d, mg)
        mem_rd = s.ref(MEM + u".Mem[EFF]", 16)
        s.assign(u"WDATA", SELb(s, mg[u"imm"], mem_rd, d["op1"], 17), 18)
        brk_lo = s.ref(MEM + u".Mem[WORD#16#FFFE]", 16)
        brk_hi = s.ref(MEM + u".Mem[WORD#16#FFFF]", 17)
        s.assign(u"BRK_VEC", s.blk(u"F_Join16", [(u"LO", brk_lo), (u"HI", brk_hi)], 18, width=110), 19)

    L = []
    if level == 14 or level == 16:
        L = [(u"IZX_PTR", u"WORD"), (u"IZX_PTR1", u"WORD"),
             (u"IZY_PTR", u"WORD"), (u"IZY_PTR1", u"WORD")]
    return s, L


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-12s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_addrvar2 ===")
    for lvl in (10, 11, 12, 13, 14, 15, 16):
        s, L = build(lvl)
        xml = pou_xml(u"AW%d" % lvl, u"functionBlock",
                      interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                                        (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD"),
                                        (u"ADDR_MODE", u"BYTE")],
                                outputs=[(u"EFF", u"WORD"), (u"WDATA", u"BYTE"),
                                         (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD")],
                                locals_=L),
                      [s], u"ступень %d" % lvl)
        write(u"AW%d" % lvl, xml)
    print(u"готово")


if __name__ == "__main__":
    main()
