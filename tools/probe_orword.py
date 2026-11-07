# -*- coding: utf-8 -*-
"""
probe_orword.py -- reshayushchiy opyt: OR po WORD ot vyhodov blokov.

Chto izvestno:
  derevo iz 11 SEL s KONSTANTAMI i OR po BYTE -- rabotaet (dekoder, 430 SEL);
  OR po BOOL -- rabotaet (derevya OR v dekodere);
  odinochnyy SEL s peremennymi vhodami -- rabotaet (C_ADD_SEL);
  derevo iz 2 SEL s PEREMENNYMI vhodami + OR po WORD -- ЗАВИСАНИЕ (TR2).

Gipoteza: operator OR (unверсальный ANY_BIT) ne vyvodit tip, kogda operandy --
vyhody universalnyh blokov, a ne konstanty. V rezhime --noUI eto prevrashchaetsya
v nevidimoe modalnoe okno i vechnoe ozhidanie.

Opyty:
  X1 cepochka iz 4 vlozhennyh SEL (bez OR)     <-- predlagaemaya zмена
  X2 OR dvuh SEL s peremennymi vhodami         <-- podozrenie, poetomu posledniy
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_orword.log")
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
log(u"=== PROBE_ORWORD START ===")

CASES = []
LOCS = [(u"W1", u"WORD"), (u"W2", u"WORD"), (u"W3", u"WORD"), (u"W4", u"WORD"),
        (u"W5", u"WORD"), (u"W6", u"WORD"), (u"G1", u"BOOL"), (u"G2", u"BOOL"),
        (u"G3", u"BOOL"), (u"G4", u"BOOL")]


def b_chain(s):
    """Цепочка вложенных SEL вместо OR-дерева."""
    cur = s.const(u"WORD#0", 10)
    for k, g in ((4, u"G4"), (3, u"G3"), (2, u"G2"), (1, u"G1")):
        cur = s.blk(u"SEL", [(u"G", s.ref(g, 10)),
                             (u"IN0", cur),
                             (u"IN1", s.ref(u"W%d" % k, 10))], 10)
    s.assign(u"W5", cur, 12)


def b_or_of_sels(s):
    """Два SEL с переменными входами, объединённые OR."""
    a = s.blk(u"SEL", [(u"G", s.ref(u"G1", 10)),
                       (u"IN0", s.const(u"WORD#0", 10)),
                       (u"IN1", s.ref(u"W1", 10))], 10)
    b = s.blk(u"SEL", [(u"G", s.ref(u"G2", 10)),
                       (u"IN0", s.const(u"WORD#0", 10)),
                       (u"IN1", s.ref(u"W2", 10))], 10)
    s.assign(u"W5", s.blk(u"OR", [(u"IN1", a), (u"IN2", b)], 12), 13)


def case(name, builder):
    s = fbd.Sheet(u"", order_start=1)
    builder(s)
    CASES.append((name, fbd.pou_xml(name, u"program",
                                   fbd.interface(locals_=LOCS), [s], comment=u"probe")))


case(u"X1_CHAIN", b_chain)
case(u"X2_OR_SELS", b_or_of_sels)

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"or_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"or_bs.project"):
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

log(u"=== PROBE_ORWORD END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
