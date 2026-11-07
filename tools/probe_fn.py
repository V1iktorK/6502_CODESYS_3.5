# -*- coding: utf-8 -*-
"""
probe_fn.py -- proverka: privodit li k zavisaniyu VYZOV funkcii F_Join16.

Razlichie po tipam blokov mezhdu POU:
  РАБОЧИЕ  (FB_Fetch, FB_Decoder6502, FB_ALU6502, FB_Flags): net ni F_Join16, ni BYTE_TO_WORD
  ПАДАЮТ   (FB_AddrMode, FB_PC_Update):                    est F_Join16 i BYTE_TO_WORD

F_UnpackByte / F_PackByte vyzyvayutsya v FB_Flags i rabotayut. Znachit delo mozhet
byt v konkretno F_Join16 (WORD -> WORD), a ne v samom principe vyzova funkcii.

Opyty (bezopasnye snachala):
  J0 kontrol  W1 := BYTE_TO_WORD(B2)
  J1 вызов    W1 := F_Join16(B2, B3)     <-- podozrenie
  J2 вызов    W1 := F_Add16(W2, W3)
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_fn.log")
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
log(u"=== PROBE_FN START ===")

CASES = []


def case(name, builder):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    locs = [(u"W1", u"WORD"), (u"W2", u"WORD"), (u"W3", u"WORD"),
            (u"B1", u"BYTE"), (u"B2", u"BYTE"), (u"B3", u"BYTE")]
    CASES.append((name, fbd.pou_xml(name, u"functionBlock",
                                   fbd.interface(outputs=[(u"Out", u"WORD")], locals_=locs),
                                   [s], comment=u"probe")))


def b_ctrl(s):
    s.assign(u"W1", s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"B2", 0))], 1, width=140), 2)


def b_join(s):
    s.assign(u"W1", s.blk(u"F_Join16", [(u"LO", s.ref(u"B2", 0)),
                                        (u"HI", s.ref(u"B3", 0))], 1, width=110), 2)


def b_add16(s):
    s.assign(u"W1", s.blk(u"F_Add16", [(u"IN1", s.ref(u"W2", 0)),
                                       (u"IN2", s.ref(u"W3", 0))], 1, width=110), 2)


case(u"J0_CTRL", b_ctrl)
case(u"J2_ADD16", b_add16)
case(u"J1_JOIN16", b_join)

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"fn_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"fn_bs.project"):
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

for dep in (u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16"):
    p = os.path.join(PLCOPEN, u"%s.xml" % dep)
    if os.path.exists(p):
        try:
            app.import_xml(p, False)
        except Exception:
            pass
log(u"зависимости импортированы")


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
    log(u"  %-12s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))

log(u"=== PROBE_FN END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
