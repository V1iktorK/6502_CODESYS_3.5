# -*- coding: utf-8 -*-
"""
probe_templates.py -- ishchem shablon s RABOCHIM ustroystvom.

Problema: shablon Templates\\Standard.project soderzhit ustroystvo
PLCWinNT (CoDeSys SP Win V3), iz-za kotorogo kompilyator daet
    C0046: Идентификатор 'IoConfigTaskMap' не задан
Eto oshibka urovnya ustroystva, ne logiki. Metoda add_device v API NET,
poetomu ustroystvo cherez skript ne pomenyat.

Reshenie: najti drugoy shablon, u kotorogo ustroystvo sovremennoe
(naprimer CODESYS Control Win V3), i sobirat proekt na nem.

Rezultat -> log/probe_templates.log
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
LOG = os.path.join(ROOT, "log", "probe_templates.log")
TPL_DIR = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates"
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_TEMPLATES START ===")
import scriptengine

CANDIDATES = [
    u"Empty.project", u"Standard.project",
    u"TemplatePlc200_01.project", u"TemplatePlc210_01.project",
    u"TemplatePlc210_04.project",
]


def kids(obj, depth=0, maxd=3):
    out = []
    if depth > maxd:
        return out
    try:
        for ch in obj.get_children():
            s = str(ch)
            nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else u"?"
            out.append((u"  " * depth + nm, ch))
            out.extend(kids(ch, depth + 1, maxd))
    except Exception:
        pass
    return out


for name in CANDIDATES:
    src = os.path.join(TPL_DIR, name)
    if not os.path.exists(src):
        log(u"--- %s: НЕТ ФАЙЛА" % name)
        continue
    dst = os.path.join(BUILD, u"tpl_%s" % name)
    for junk in os.listdir(BUILD):
        if junk.startswith(u"tpl_%s" % name):
            try:
                os.remove(os.path.join(BUILD, junk))
            except Exception:
                pass
    try:
        _s = io.open(src, "rb")
        _d = _s.read()
        _s.close()
        _o = io.open(dst, "wb")
        _o.write(_d)
        _o.close()
    except Exception:
        log(u"--- %s: копирование не удалось" % name)
        continue

    proj = None
    try:
        proj = projects.open(dst)
    except Exception:
        log(u"--- %s: открыть не удалось: %s"
            % (name, traceback.format_exc().strip().splitlines()[-1]))
        continue

    tree = kids(proj, 0, 3)
    log(u"--- %s ---" % name)
    for t, _ in tree:
        log(u"    %s" % t)
    try:
        app = proj.active_application
        log(u"    active_application = %s" % (u"ЕСТЬ" if app is not None else u"НЕТ"))
    except Exception:
        log(u"    active_application: %s" % traceback.format_exc().strip().splitlines()[-1])
    try:
        # что за устройство на верхнем уровне
        for ch in proj.get_children():
            s = str(ch)
            nm = s.split(u"Name=")[1].split(u",")[0] if u"Name=" in s else u"?"
            if nm not in (u"Project Settings", u"__VisualizationStyle"):
                log(u"    УСТРОЙСТВО-КАНДИДАТ: %s" % nm)
    except Exception:
        pass
    try:
        proj.close()
    except Exception:
        pass

log(u"=== PROBE_TEMPLATES END ===")
try:
    system.exit()
except Exception:
    pass
