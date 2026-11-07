# -*- coding: utf-8 -*-
"""
probe_rest.py -- proveryaem VSE POU krome FB_AddrMode i FB_CPU_Core.

Cel: ponyat, tolko li FB_AddrMode privodit k zavisaniyu. Esli ostalnye sem
sozdayutsya i kompiliruyutsya, znachit restrukturirovat nuzhno tolko adresaciyu
i kompoziciyu.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_rest.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")

ORDER = [u"F_UnpackByte", u"F_PackByte", u"F_Join16", u"F_Split16", u"F_Add16",
         u"FB_Fetch", u"FB_Decoder6502", u"FB_ALU6502", u"FB_Flags",
         u"FB_PC_Update", u"FB_WriteBack"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_REST START ===")
import scriptengine

BASE = os.path.join(BUILD, u"rest_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"rest_bs.project"):
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
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_VAR\n")
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
if os.path.exists(BASE) and proj is not None:
    try:
        proj.save()
        log(u"проект сохранён")
    except Exception:
        log(u"save: %s" % traceback.format_exc().strip().splitlines()[-1])
log(u"=== PROBE_REST END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
