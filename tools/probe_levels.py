# -*- coding: utf-8 -*-
"""
probe_levels.py -- izmeryaem POROG OB'EMA: kakoj uroven yadra eshche sozdaetsya.

Importiruem PRG_CORE_L2..L10 v odin proekt i smotrim, kakiye POU poyavilis.
Eto daet tochnuyu granicu (vblokah) i pozvolyaet razbit yadro na chasti nizhe
poroga, ne narushaya TZ.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_levels.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_LEVELS START ===")
import scriptengine

BASE = os.path.join(BUILD, u"base_lvl.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"base_lvl.project"):
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


def children():
    names = set()
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.add(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        log(traceback.format_exc())
    return names


# GVL и зависимости
try:
    g = app.create_gvl(u"GVL_CPU")
    g.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_VAR\n")
    g2 = app.create_gvl(u"GVL_MEM")
    g2.textual_declaration.replace(u"VAR_GLOBAL\n\tMem : ARRAY[0..65535] OF BYTE;\nEND_VAR\n")
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

BLOCKS = {2: 571, 3: 627, 4: 654, 5: 667, 6: 698, 7: 712, 8: 739, 9: 768, 10: 779}
ok, bad = [], []
for lvl in sorted(BLOCKS):
    name = u"PRG_CORE_L%d" % lvl
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    if not os.path.exists(p):
        log(u"  %-14s НЕТ ФАЙЛА" % name)
        continue
    try:
        app.import_xml(p, False)
    except Exception:
        log(u"  %-14s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        bad.append(lvl)
        continue
    got = name in children()
    log(u"  %-14s (%3d блоков) -> %s" % (name, BLOCKS[lvl], u"СОЗДАН" if got else u"НЕ СОЗДАН"))
    (ok if got else bad).append(lvl)

log(u"")
log(u"СОЗДАНЫ уровни    : %s" % (u", ".join([u"L%d(%d блоков)" % (l, BLOCKS[l]) for l in ok]) or u"(нет)"))
log(u"НЕ СОЗДАНЫ уровни : %s" % (u", ".join([u"L%d(%d блоков)" % (l, BLOCKS[l]) for l in bad]) or u"(нет)"))
if ok and bad:
    log(u"ПОРОГ: между %d и %d блоками" % (BLOCKS[max(ok)], BLOCKS[min(bad)]))
elif not ok:
    log(u"ПОРОГ ниже 571 блока -- режем мельче")
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_LEVELS END ===")
try:
    system.exit()
except Exception:
    pass
