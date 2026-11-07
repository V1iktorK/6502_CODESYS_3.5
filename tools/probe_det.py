# -*- coding: utf-8 -*-
"""
probe_det.py -- proverka NEDETERMINIZMA importa.

Protivorechiya v dannyh:
  AR11 (11 zhivyh setey)      -- СОЗДАН (proverено dvazhdy)
  CL1  (7 zhivyh + 4 konst)   -- ЗАВИСАНИЕ
  RP0  (11 raznyh setey)      -- ЗАВИСАНИЕ
  AR1..AR11                   -- vse SOZDANY
Pochti odinakovye shemy vedut sebya po-raznomu. Vozmozhno, import nedeterminirovan
(zavisit ot nakoplennogo sostoyaniya sessii / pamyati).

Plan: odin i tot zhe fayl importiruetsya neskolko raz pod raznymi imenami.
  AR11 -> A1, A2, A3    (ozhidaem: vse СОЗДАН)
  CL1  -> B1, B2        (ozhidaem: vse ЗАВИСАНИЕ)
  AR11 -> A4            (posle "plohogo" importa -- proverka zagryazneniya sessii)

Esli hotya by odno povtorenie menyaet rezultat -- import NEDETERMINIROVAN.
"""
import io
import os
import re
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_det.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_DET START ===")

PLAN = [(u"AR11", u"A1"), (u"AR11", u"A2"), (u"CL1", u"B1"),
        (u"AR11", u"A3"), (u"CL1", u"B2"), (u"AR11", u"A4")]


def make(src, name):
    t = io.open(os.path.join(PLCOPEN, u"%s.xml" % src), "rb").read().decode("utf-8")
    return re.sub(u'<pou name="[^"]*"', u'<pou name="%s"' % name, t, count=1)


def write(s):
    o = io.open(os.path.join(PLCOPEN, u"det_tmp.xml"), "wb")
    o.write(s.encode("utf-8"))
    o.close()


BASE = os.path.join(BUILD, u"det_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"det_bs.project"):
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

try:
    g2 = app.create_gvl(u"GVL_MEM")
    g2.textual_declaration.replace(u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_VAR\n")
    log(u"GVL созданы")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

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
for src, name in PLAN:
    log(u"  ПЕРЕД ИМПОРТОМ %s (из %s.xml)" % (name, src))
    try:
        write(make(src, name))
        app.import_xml(os.path.join(PLCOPEN, u"det_tmp.xml"), False)
    except Exception:
        log(u"  %-4s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        continue
    ok = name in names()
    log(u"  %-4s -> %s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))

log(u"=== PROBE_DET END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
