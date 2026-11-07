# -*- coding: utf-8 -*-
"""
gen_tree.py -- lestnica po RAZMERU dereva SEL/OR s istochnikami-peremennymi.

Fakty (lestnica AW10..AW16):
  AW10 baza                          СОЗДАН
  AW11 +13 sravneniy ADDR_MODE       СОЗДАН
  AW12 +arifmetika adresov           СОЗДАН
  AW13 +relative                     НЕ СОЗДАН (bystryy otkaz!)
  AW14 +kosvennye cepochki           СОЗДАН
  AW15 AW12 + derevo SEL/OR          ЗАВИСАНИЕ

Derevo v dekodere (430 SEL) rabotaet, no tam vhody SEL -- KONSTANTY.
V adresacii vhody SEL -- VYHODY BLOKOV. Proveryaem razmer takogo dereva:
  T2, T4, T6, T8, T11  (poryadok vozrastaniya; AW15 ~ T11)
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
W0 = G.W0
MODES = G.MODES
EQv, SELb, ORT = G.EQv, G.SELb, G.ORT


def build(k):
    s = Sheet(u"FB_AddrMode: дерево на %d входов" % k)
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
    imm_w = s.blk(u"ADD", [(u"IN1", pcs), (u"IN2", s.const(G.W1, 9))], 10)

    cands = [(mg[u"imm"], imm_w), (mg[u"zp"], zpw), (mg[u"zpx"], zpxw),
             (mg[u"zpy"], zpyw), (mg[u"abs"], AB), (mg[u"abx"], abx),
             (mg[u"aby"], aby), (mg[u"izx"], AB), (mg[u"izy"], AB),
             (mg[u"ind"], AB), (mg[u"stk"], AB)][:k]
    wp = [SELb(s, g, s.const(W0, 11), c, 11) for g, c in cands]
    ef = ORT(s, wp, 13)
    s.assign(u"EFF", ef, 15)
    s.assign(u"WDATA", op1, 16)
    s.assign(u"REL_DEST", s.const(W0, 16), 16)
    s.assign(u"BRK_VEC", s.const(W0, 16), 16)
    return s, []


def write(name, xml):
    p = os.path.join(OUT, u"%s.xml" % name)
    f = io.open(p, "wb")
    f.write(xml.encode("utf-8"))
    f.close()
    print(u"  %-10s %8d байт" % (name, os.path.getsize(p)))


def main():
    print(u"=== gen_tree ===")
    for k in (2, 4, 6, 8, 11):
        s, L = build(k)
        xml = pou_xml(u"TR%d" % k, u"functionBlock",
                      interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                                        (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD"),
                                        (u"ADDR_MODE", u"BYTE")],
                                outputs=[(u"EFF", u"WORD"), (u"WDATA", u"BYTE"),
                                         (u"REL_DEST", u"WORD"), (u"BRK_VEC", u"WORD")],
                                locals_=L),
                      [s], u"дерево %d" % k)
        write(u"TR%d" % k, xml)
    print(u"готово")


if __name__ == "__main__":
    main()
