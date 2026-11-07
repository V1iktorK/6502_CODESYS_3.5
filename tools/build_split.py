# -*- coding: utf-8 -*-
"""
build_split.py -- sobrat realnyy proekt iz PROVERENNYH POU i skompilirovat.

Vhodit tolko to, chto dokazanno importiruetsya i kompiliruetsya:
  GVL_CPU, GVL_MEM
  F_UnpackByte, F_PackByte, F_Join16, F_Split16, F_Add16
  FB_Fetch, FB_Decoder6502, FB_ALU6502, FB_Flags, SL_IND

Rezultat: build/CPM6502_CPU_base.project (0 oshibok, 0 preduprezhdeniy).
Eto bazа dlya sleduyushchih shagov: adresaciya i PC dobavlyayutsya k nei po mere
toGo, kak ih listy prohodyat import.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "build_split.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")
OUTPROJ = os.path.join(ROOT, "build", u"CPM6502_CPU_base.project")

ORDER = [u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
         u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags", u"SL_IND"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== BUILD_SPLIT START ===")
import scriptengine

BASE = os.path.join(BUILD, u"bsplit.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"bsplit.project"):
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
        u"VAR_GLOBAL\n"
        u"\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\n"
        u"\tOP : BYTE;\n\tOP1 : BYTE;\n\tOP2 : BYTE;\n"
        u"\tPC1 : WORD;\n\tPC2 : WORD;\n"
        u"\tPCL : BYTE;\n\tPCH : BYTE;\n"
        u"\tEFF : WORD;\n\tWDATA : BYTE;\n"
        u"\tALU_R : BYTE;\n\tP_NEW : BYTE;\n"
        u"\tPC_NEW : WORD;\n\tSP_NEW : BYTE;\n"
        u"END_VAR\n")
    log(u"GVL созданы")
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
bad = []
for name in ORDER:
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    if not os.path.exists(p):
        log(u"  %-16s НЕТ ФАЙЛА" % name)
        bad.append(name)
        continue
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"  %-16s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))
    if not ok:
        bad.append(name)

log(u"")
log(u"--- сборка ---")
try:
    app.build()
except Exception:
    log(u"  исключение: %s" % traceback.format_exc().strip().splitlines()[-1])
for c in system.get_message_categories():
    try:
        msgs = system.get_messages(c)
    except Exception:
        continue
    for m in msgs:
        try:
            log(u"  %s" % (m,))
        except Exception:
            pass

log(u"не создано: %d (%s)" % (len(bad), u", ".join(bad) if bad else u"нет"))

if proj is not None and not bad:
    try:
        if not os.path.isdir(os.path.dirname(OUTPROJ)):
            os.makedirs(os.path.dirname(OUTPROJ))
        proj.save_as(OUTPROJ)
        log(u"проект сохранён: %s" % OUTPROJ)
    except Exception:
        log(u"save_as: %s" % traceback.format_exc().strip().splitlines()[-1])

log(u"=== BUILD_SPLIT END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
