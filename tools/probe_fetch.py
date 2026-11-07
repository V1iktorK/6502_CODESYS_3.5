# -*- coding: utf-8 -*-
"""
probe_fetch.py -- pilot dekompozicii: importiruemy FB_Fetch i FB_CorePilot
(kompoziciya cherez EKZEMPLYAR s podklyucheniem kontaktami) i SOBIRAEM proekt.
Chtoby schitat pilot uspeshnym, nuzhno: oba POU sozdany I kompilyaciya bez oshibok.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_fetch.log")
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
log(u"=== PROBE_FETCH START ===")
import scriptengine

BASE = os.path.join(BUILD, u"fetch_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"fetch_bs.project"):
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
log(u"--- импорт ---")
for name in (u"FB_Fetch", u"FB_CorePilot"):
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    if not os.path.exists(p):
        log(u"  %-14s НЕТ ФАЙЛА" % name)
        continue
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"  %-14s -> %s%s" % (name, u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                              (u"  (искл: %s)" % exc) if exc else u""))

log(u"")
log(u"--- сообщения ---")
try:
    for c in system.get_message_categories():
        try:
            msgs = system.get_messages(c)
        except Exception:
            continue
        for m in msgs:
            try:
                log(u"  %s" % (m,))
            except Exception:
                log(u"  <нечитаемое>")
except Exception:
    log(u"  нет категорий")

log(u"")
log(u"--- сборка ---")
try:
    app.build()
except Exception:
    log(u"  исключение: %s" % traceback.format_exc().strip().splitlines()[-1])
log(u"--- сообщения сборки ---")
errs = 0
try:
    for c in system.get_message_categories():
        try:
            msgs = system.get_messages(c)
        except Exception:
            continue
        for m in msgs:
            try:
                t = u"%s" % (m,)
            except Exception:
                t = u"<нечитаемое>"
            log(u"  %s" % t)
            low = t.lower()
            if u"ошиб" in low or u"error" in low:
                errs += 1
except Exception:
    log(u"  нет категорий")
log(u"строк с ошибками: %d" % errs)

log(u"=== PROBE_FETCH END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
