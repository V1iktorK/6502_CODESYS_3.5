# -*- coding: utf-8 -*-
"""
gen_addrvar3.py -- utochnenie: chto imenno lomaet v sochetanii s arifmetikoy.

Baza -- AW12 (polnaya arifmetika adresov, bez dereva i bez relative): СОЗДАН.
Izvestno: TR2 (= baza + 2 SEL + OR) -- ЗАВИСАНИЕ;
          X2  (2 SEL + OR bez arifmetiki) -- СОЗДАН;
          AW13 (baza + relative)          -- отклонён (bystro, bez zavisaniya).

Opyty:
  Y1  baza + 1 SEL, istochnik = ADD(PCs, WORD#1)      (bез F_Join16)
  Y2  baza + 1 SEL, istochnik = F_Join16(OP1,OP2)     (с F_Join16)
  Y4  baza + relative bez GE/SEL: off := OP1, ostalnoe kak est
  Y3  baza + 2 SEL + OR  (= TR2, ozhidaemoe zavisanie, poetomu posledniy)
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
B0, B80 = G.B0, G.B80
W0, W1 = G.W0, G.W1
MODES = G.MODES
EQv, SELb, ORT = G.EQv, G.SELb, G.ORT


def base(s):
    op1 = s.ref(u"OP1", 0)
    op2 = s.ref(u"OP2", 0)
    x = s.ref(u"X", 0)
    y = s.ref(u"Y", 0)
    pcs = s.ref(u"PCs", 0)
    pc2 = s.ref(u"PC2", 0)
    modev = s.ref(u"ADDR_MODE", 0)
    mg = {}
    for m in MODES:
        mg[m] = EQv(s, modev, u"BYTE#%d" % G.MODE_CODE[m], 1)
    AB = s.blk(u"F_Join16", [(u"LO", op1), (u"HI", op2)], 4, width=110)
    zp = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", x)], 3)
    zpy = s.blk(u"ADD", [(u"IN1", op1), (u"IN2", y)], 3)
    zpw = s.blk(u"BYTE_TO_WORD", [(u"IN", op1)], 4, width=140)
    zpxw = s.blk(u"BYTE_TO_WORD", [(u"IN", zp)], 4, width=140)
    zpyw = s.blk(u"BYTE_TO_WORD", [(u"IN", zpy)], 4, width=140)
    xw = s.blk(u"BYTE_TO_WORD", [(u"IN", x)], 5, width=120)
    yw = s.blk(u"BYTE_TO_WORD", [(u"IN", y)], 5, width=120)
    abx = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", xw)], 6)
    aby = s.blk(u"ADD", [(u"IN1", AB), (u"IN2", yw)], 6)
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(W1, 9))], 10)
    s.assign(u"EFF", AB, 15)
    s.assign(u"WDATA", op1, 16)
    s.assign(u"REL_DEST", s.const(W0, 16), 16)
    s.assign(u"BRK_VEC", s.const(W0, 16), 16)
    return dict(op1=op1, op2=op2, pcs=pcs, pc2=pc2, mg=mg, AB=AB, imm_w=imm_w,
                zpw=zpw, zpxw=zpxw, zpyw=zpyw, abx=abx, aby=aby)


def add_one_sel(s, d, src, extra_locals):
    s.assign(u"EFFX", SELb(s, d["mg"][u"imm"], s.const(W0, 12), src, 12), 13)
    extra_locals.append((u"EFFX", u"WORD"))


def add_two_sels_or(s, d):
    a = SELb(s, d["mg"][u"imm"], s.const(W0, 11), d["imm_w"], 11)
    b = SELb(s, d["mg"][u"zp"], s.const(W0, 11), d["zpw"], 11)
    ef = ORT(s, [a, b], 13)
    s.assign(u"EFF", ef, 15)


def add_relative(s, d, with_ge_sel):
    op1 = d["op1"]
    if with_ge_sel:
        sgn = s.blk(u"GE", [(u"IN1", op1), (u"IN2", s.const(B80, 6))], 6)
        off = s.blk(u"SEL", [(u"G", sgn), (u"IN0", op1),
                             (u"IN1", s.blk(u"ADD", [(u"IN1", op1), (u"IN2", s.const(B80, 7))], 7))], 8)
    else:
        off = op1
    offw = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", off)], 8, width=140)),
                          (u"IN2", s.const(u"WORD#16#FF00", 8))], 9)
    relw = s.blk(u"ADD", [(u"IN1", d["pc2"]), (u"IN2", offw)], 10)
    s.assign(u"REL_DEST", relw, 12)


def build(kind):
    s = Sheet(u"FB_AddrMode: %s" % kind)
    d = base(s)
    L = []
    if kind == u"Y1":
        add_one_sel(s, d, d["imm_w"], L)
    elif kind == u"Y2":
        add_one_sel(s, d, d["AB"], L)
    elif kind == u"Y4":
        add_relative(s, d, False)
    elif kind == u"Y5":
        add_relative(s, d, True)
    elif kind == u"Y3":
        add_two_sels_or(s, d)
    return s, L


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-8s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_addrvar3 ===")
    for kind in (u"Y1", u"Y2", u"Y4", u"Y5", u"Y3"):
        s, L = build(kind)
        xml = pou_xml(u"AD_%s" % kind, u"functionBlock",
                      interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                                        (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD"),
                                        (u"ADDR_MODE", u"BYTE")],
                                outputs=[(u"EFF", u"WORD"), (u"WDATA", u"BYTE"),
                                         (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD")],
                                locals_=L),
                      [s], u"уточнение %s" % kind)
        write(u"AD_%s" % kind, xml)
    print(u"готово")


if __name__ == "__main__":
    main()
