# -*- coding: utf-8 -*-
"""
probe_fanout.py -- GIPOTEZA: privodit k otkazu/VISHANIYU import, kogda VYHOD BLOKA
pitает DVA i bolee vhodov drugih blokov (vetvlenie svyazi).

Pochemu eto silnaya gipoteza -- ona ob#yasnyaet VSЕ nablyudeniya:
  * FB_Decoder6502 (547 blokov) -- derevo: vyhod kazhdogo bloka idet rovno
    v odin vhod sleduyushchego (fan-out = 1). Sozdaetsya.
  * sintez 4000 MOVEs -- kazhdaya peremennaya pitаet odin blok. Sozdaetsya.
  * vse 11 mikrokонstrukcij i 5 zondov -- fan-out 1. Sozdavalis.
  * FB_AddrMode: element #48 = ADD(AB, xw), gde AB (id 2509) uzhe pitаet vtoroy
    blok (aby). Imenno na nem import visnet.
  * yadro: tochka otkaza -- OR 2681, vhodyashchiy v SEL 2670, u kotorogo uzhe
    byli potrebiteli. Fan-out >= 2.

Opyty:
  F1  fan-out 1 (kontrol)         W3 := ADD(W1, W2)
  F2  fan-out 2                   W3 := ADD(W1, W2); W4 := ADD(W3, W1); W5 := ADD(W3, W2)
  F3  fan-out 3                   ot W3 tri potrebitelya
  F4  fan-out 2 cherez peremennuyu (obhod) -- kazhdyy potrebitel chitaet imya
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_fanout.log")
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
log(u"=== PROBE_FANOUT START ===")

CASES = []


def case(name, builder, locs):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    CASES.append((name, fbd.pou_xml(name, u"program", fbd.interface(locals_=locs), [s],
                                   comment=u"probe")))


def b_fan1(s):
    a = s.blk(u"ADD", [(u"IN1", s.ref(u"W1", 0)), (u"IN2", s.ref(u"W2", 0))], 1)
    s.assign(u"W3", a, 2)


def b_fan2(s):
    a = s.blk(u"ADD", [(u"IN1", s.ref(u"W1", 0)), (u"IN2", s.ref(u"W2", 0))], 1)
    s.assign(u"W3", a, 2)
    b = s.blk(u"ADD", [(u"IN1", a), (u"IN2", s.ref(u"W1", 0))], 2)
    s.assign(u"W4", b, 3)
    c = s.blk(u"ADD", [(u"IN1", a), (u"IN2", s.ref(u"W2", 0))], 2)
    s.assign(u"W5", c, 3)


def b_fan3(s):
    a = s.blk(u"ADD", [(u"IN1", s.ref(u"W1", 0)), (u"IN2", s.ref(u"W2", 0))], 1)
    s.assign(u"W3", a, 2)
    for k, nm in ((1, u"W4"), (2, u"W5"), (3, u"W6")):
        b = s.blk(u"ADD", [(u"IN1", a), (u"IN2", s.const(u"WORD#%d" % k, 2))], 2)
        s.assign(nm, b, 3)


def b_fan2_broken(s):
    """Тот же fan-out 2, но каждый потребитель берёт ЗНАЧЕНИЕ ПО ИМЕНИ."""
    a = s.blk(u"ADD", [(u"IN1", s.ref(u"W1", 0)), (u"IN2", s.ref(u"W2", 0))], 1)
    s.assign(u"W3", a, 2)
    b = s.blk(u"ADD", [(u"IN1", s.ref(u"W3", 0)), (u"IN2", s.ref(u"W1", 0))], 3)
    s.assign(u"W4", b, 4)
    c = s.blk(u"ADD", [(u"IN1", s.ref(u"W3", 0)), (u"IN2", s.ref(u"W2", 0))], 3)
    s.assign(u"W5", c, 4)


V = [(u"W1", u"WORD"), (u"W2", u"WORD"), (u"W3", u"WORD"),
     (u"W4", u"WORD"), (u"W5", u"WORD"), (u"W6", u"WORD")]

case(u"F1_FAN1", b_fan1, V)
case(u"F2_FAN2", b_fan2, V)
case(u"F3_FAN3", b_fan3, V)
case(u"F4_FAN2_BYNAME", b_fan2_broken, V)

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"fan_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"fan_bs.project"):
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
    log(u"  %-16s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))

log(u"")
log(u"Ожидание при подтверждении гипотезы: F1 и F4 СОЗДАН, F2 и F3 -- НЕ СОЗДАН / зависание.")
log(u"=== PROBE_FANOUT END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
