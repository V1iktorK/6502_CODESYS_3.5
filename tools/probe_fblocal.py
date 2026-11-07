# -*- coding: utf-8 -*-
"""
probe_fblocal.py -- proverka: v FUNCTION_BLOCK chtenie Mem[<lokalnaya peremennaya>]
privodit k zavisaniyu.

Sravnenie uspekhov i provalov:
  FB_Fetch      (functionBlock) -- chitaet Mem[PCs] / Mem[PC1] / Mem[PC2], gde
                                   PCs -- VHOD, a PC1/PC2 -- VYHODY.        СОЗДАН
  FB_AddrMode   (functionBlock) -- chitaet Mem[IZX_PTR], gde IZX_PTR -- LOKAL.  ЗАВИСАНИЕ
  FB_PC_Update  (functionBlock) -- chitaet Mem[STK_R0], gde STK_R0 -- LOKAL.    ЗАВИСАНИЕ
  H_LOCAL_IDX   (program)       -- chitaet Mem[W1], gde W1 -- LOKAL.           СОЗДАН

Edinstvennoe neproverennoe razlichie -- TIP POU: program ili functionBlock.
Opyty:
  L1  program:       W := BYTE_TO_WORD(A);  B := Mem[W]
  L2  functionBlock: to zhe samoe          <-- podozrenie, poetomu posledniy
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_fblocal.log")
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
log(u"=== PROBE_FBLOCAL START ===")

CASES = []


def body():
    s = fbd.Sheet(u"", order_start=1)
    w = s.blk(u"BYTE_TO_WORD", [(u"IN", s.ref(u"A", 0))], 1, width=140)
    s.assign(u"W", w, 2)
    s.assign(u"B", s.ref(u"Mem[W]", 3), 4)
    return s


def add(name, kind):
    s = body()
    if kind == u"program":
        iface = fbd.interface(locals_=[(u"A", u"BYTE"), (u"W", u"WORD"), (u"B", u"BYTE")])
    else:
        iface = fbd.interface(inputs=[(u"A", u"BYTE")], outputs=[(u"B", u"BYTE")],
                              locals_=[(u"W", u"WORD")])
    CASES.append((name, fbd.pou_xml(name, kind, iface, [s], comment=u"probe")))


add(u"L1_PROGRAM", u"program")
add(u"L2_FB", u"functionBlock")

for name, xml in CASES:
    write(os.path.join(PLCOPEN, u"%s.xml" % name), xml)
log(u"сгенерировано: %d" % len(CASES))

BASE = os.path.join(BUILD, u"fb_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"fb_bs.project"):
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
    log(u"GVL_MEM создан")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])


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

log(u"=== PROBE_FBLOCAL END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
