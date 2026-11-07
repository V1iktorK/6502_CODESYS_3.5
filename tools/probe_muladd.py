# -*- coding: utf-8 -*-
"""
probe_muladd.py -- proverka svyazki MUL -> ADD.

Differencialnyy opyt na prefikse FB_AddrMode:
  потребление 2506 (BYTE_TO_WORD)   -> СОЗДАН
  потребление 2505 (BYTE_TO_WORD)   -> СОЗДАН
  потребление 2508 (MUL)            -> СОЗДАН
  потребление 2509 (ADD(2508,2505)) -> ЗАВИСАНИЕ

To est problema voznikает pri potreblenii bloka ADD, u kotorogo vhod -- vyhod MUL.
Sintezicheskie opyty (poryadok: bezopasnye snachala, podozritelnye v konce):
  S1 контроль ADD(W2,W3)
  S2 ADD(B2W(B2), WORD#256)          -- ADD s vhodom-konversiey, bez MUL
  S3 MUL(W5,W6) -> potreblenie        -- MUL potreblyaetsya napryamuyu
  S4 MUL(W5,W6) -> ADD              <-- podozrenie
  S5 MUL(B2W(B2), WORD#256) -> ADD  <-- podozrenie (kak v FB_AddrMode)
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_muladd.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


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
log(u"=== PROBE_MULADD START ===")

CASES = []


def case(name, builder):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    locs = [(u"W1", u"WORD"), (u"W2", u"WORD"), (u"W3", u"WORD"), (u"W4", u"WORD"),
            (u"W5", u"WORD"), (u"W6", u"WORD"), (u"W7", u"WORD"),
            (u"B2", u"BYTE"), (u"B3", u"BYTE")]
    CASES.append((name, fbd.pou_xml(name, u"program", fbd.interface(locals_=locs), [s],
                                    comment=u"probe")))


def b_ctrl(s):
    a = s.blk(u"ADD", [(u"IN1", s.ref(u"W2", 0)), (u"IN2", s.ref(u"W3", 0))], 1)
    s.assign(u"W1", a, 2)


def b_add_b2w(s):
    a = s.blk(u"ADD", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"B2", 0))], 0)),
                       (u"IN2", s.const(u"WORD#256", 0))], 1)
    s.assign(u"W1", a, 2)


def b_mul_only(s):
    a = s.blk(u"MUL", [(u"IN1", s.ref(u"W5", 0)), (u"IN2", s.ref(u"W6", 0))], 1)
    s.assign(u"W1", a, 2)


def b_mul_add(s):
    m = s.blk(u"MUL", [(u"IN1", s.ref(u"W5", 0)), (u"IN2", s.ref(u"W6", 0))], 1)
    s.assign(u"W1", m, 2)
    a = s.blk(u"ADD", [(u"IN1", m), (u"IN2", s.ref(u"W7", 0))], 2)
    s.assign(u"W4", a, 3)


def b_mul_b2w_add(s):
    m = s.blk(u"MUL", [(u"IN1", s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"B2", 0))], 0)),
                       (u"IN2", s.const(u"WORD#256", 0))], 1)
    s.assign(u"W1", m, 2)
    a = s.blk(u"ADD", [(u"IN1", m), (u"IN2", s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"B3", 0))], 0))], 2)
    s.assign(u"W4", a, 3)


case(u"S1_CTRL", b_ctrl)
case(u"S2_ADD_B2W", b_add_b2w)
case(u"S3_MUL_ONLY", b_mul_only)
case(u"S4_MUL_ADD", b_mul_add)
case(u"S5_MUL_B2W_ADD", b_mul_b2w_add)

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"ma_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"ma_bs.project"):
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
    log(u"  %-18s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))

log(u"=== PROBE_MULADD END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
