# -*- coding: utf-8 -*-
"""
gen_family.py -- proverka arhitektury "ODNO SEMEYSTVO OPERACIY NA LIST".

Vyvod iz delty: lyuboy list, gde sochetayutsya sravneniyas (EQ/GE), vybor (SEL/OR)
i arifmetika (ADD/BYTE_TO_WORD/F_Join16), zavisает na importe. A listy s odnim
semеystvom sozdayutsya:
  * FB_Decoder6502 -- tolko EQ + OR (BOOLEAN) i SEL po BYTE-konstantam;
  * FB_Fetch       -- tolko ADD/SHR/WORD_TO_BYTE;
  * FB_ALU6502     -- tolko arifmetika i bitovye operacii.

Predpolagaemaya arhitektura adresacii:
  SL_CALC   -- CHISTAYA arifmetika: vhody OP1..PC2, vyhody 11 adresov-kandidatov
  SL_SELECT -- CHISTYY vybor: vhody ADDR_MODE + 11 adresov, vyhod EFF

Opyty:
  P1 SL_CALC   (arifmetika bez sravneniy i SEL)
  P2 SL_SELECT (sravneniya i vybor bez arifmetiki) -- posledniy
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_family.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")

W0, W1 = u"WORD#0", u"WORD#1"
B0 = u"BYTE#0"

CAND = [u"C_IMM", u"C_ZP", u"C_ZPX", u"C_ZPY", u"C_ABS", u"C_ABX", u"C_ABY",
        u"C_IZX", u"C_IZY", u"C_IND", u"C_STK"]
CODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def write(path, text):
    o = io.open(path, "wb")
    o.write(text.encode("utf-8"))
    o.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_FAMILY START ===")

CASES = []

# ---------------- P1: только арифметика
s = fbd.Sheet(u"SL_CALC: кандидаты адресов")
op1 = s.ref(u"OP1", 0)
op2 = s.ref(u"OP2", 0)
x = s.ref(u"X", 0)
y = s.ref(u"Y", 0)
pcs = s.ref(u"PCs", 0)
pc2 = s.ref(u"PC2", 0)
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
outs = [imm_w, zpw, zpxw, zpyw, AB, abx, aby, AB, AB, AB, AB]
for nm, src in zip(CAND, outs):
    s.assign(nm, src, 12)
CASES.append((u"P1_SL_CALC", fbd.pou_xml(
    u"SL_CALC", u"functionBlock",
    fbd.interface(inputs=[(u"OP1", u"BYTE"), (u"OP2", u"BYTE"), (u"X", u"BYTE"),
                          (u"Y", u"BYTE"), (u"PCs", u"WORD"), (u"PC2", u"WORD")],
                  outputs=[(n, u"WORD") for n in CAND]),
    [s], comment=u"калькулятор адресов")))

# ---------------- P2: только сравнения и выбор
s = fbd.Sheet(u"SL_SELECT: выбор адреса по режиму")
modev = s.ref(u"ADDR_MODE", 0)
parts = []
for nm, code in zip(CAND, CODES):
    g = s.blk(u"EQ", [(u"IN1", modev), (u"IN2", s.const(u"BYTE#%d" % code, 2))], 2)
    parts.append(s.blk(u"SEL", [(u"G", g), (u"IN0", s.const(W0, 4)),
                                (u"IN1", s.ref(nm, 4))], 4))
cur = parts[0]
col = 6
for p in parts[1:]:
    cur = s.blk(u"OR", [(u"IN1", cur), (u"IN2", p)], col)
    col += 1
s.assign(u"EFF", cur, 12)
CASES.append((u"P2_SL_SELECT", fbd.pou_xml(
    u"SL_SELECT", u"functionBlock",
    fbd.interface(inputs=[(u"ADDR_MODE", u"BYTE")] + [(n, u"WORD") for n in CAND],
                  outputs=[(u"EFF", u"WORD")]),
    [s], comment=u"выбор адреса")))

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"fam_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"fam_bs.project"):
        try:
            os.remove(os.path.join(BUILD, junk))
        except Exception:
            pass
_s = io.open(TPL, "rb")
_d = _s.read()
_s.close()
_o = io.open(BASE, "wb")
_o.write(_d)
_o.close()

import scriptengine
proj = app = None
try:
    proj = projects.open(BASE)
    app = proj.active_application
    log(u"проект открыт")
except Exception:
    log(traceback.format_exc())


def names():
    out = set()
    try:
        for ch in app.get_children():
            try:
                out.add(ch.get_name())
            except Exception:
                s = str(ch)
                if u"Name=" in s:
                    out.add(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        pass
    return out


log(u"")
for name, _x in CASES:
    log(u"  ПЕРЕД ИМПОРТОМ %s" % name)
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"  %-14s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))

log(u"=== PROBE_FAMILY END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
