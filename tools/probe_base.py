# -*- coding: utf-8 -*-
"""
probe_base.py -- reshayushchaya proverka: rabotaet li BAZOVAYA shema (526 blokov)
v TEKUSHCHEY srede.

Smyisl: vse urovni yadra (571..779 blokov) otvergayutsya, a FB_Decoder6502
(524 bloka) sozdaetsya. Nuzhno ponyat, gde granica:
  * esli PRG_6502 (526 blokov, vyborka + deshifrator) SOZDASTSYA ->
    vinovata dobavlennaya chast vyborki (SHR/WORD_TO_BYTE, PCL/PCH);
  * esli NET -> moy prezhniy vyvod "526 rabotayut" ustarel.

Dopolnitelno proveryaem PRG_CORE_L2 (571 blok) dlya sravneniya v toy zhe sessii.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_base.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_BASE START ===")
import scriptengine

# --- chto est v papke ---
log(u"--- доступные схемы ---")
try:
    for n in sorted(os.listdir(PLCOPEN)):
        if n.startswith((u"PRG_", u"FB_CPU")):
            log(u"  %-22s %8d байт" % (n, os.path.getsize(os.path.join(PLCOPEN, n))))
except Exception:
    log(traceback.format_exc())

BASE = os.path.join(BUILD, u"base_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"base_bs.project"):
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

TESTS = [u"PRG_6502", u"PRG_CORE_L2"]
res = []
for name in TESTS:
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    if not os.path.exists(p):
        log(u"  %-16s НЕТ ФАЙЛА" % name)
        continue
    try:
        app.import_xml(p, False)
    except Exception:
        log(u"  %-16s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        res.append((name, u"ИСКЛЮЧЕНИЕ"))
        continue
    got = name in children()
    log(u"  %-16s -> %s" % (name, u"СОЗДАН" if got else u"НЕ СОЗДАН"))
    res.append((name, u"СОЗДАН" if got else u"НЕ СОЗДАН"))

log(u"")
log(u"ИТОГ: %s" % u"; ".join([u"%s = %s" % (n, s) for n, s in res]))
log(u"")
log(u"Толкование:")
log(u"  PRG_6502 СОЗДАН, PRG_CORE_L2 НЕТ -> виновата добавленная часть выборки (SHR/WORD_TO_BYTE, PCL/PCH)")
log(u"  оба НЕ СОЗДАНЫ -> прежний вывод '526 блоков работают' устарел, режем ниже 524")
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_BASE END ===")
try:
    system.exit()
except Exception:
    pass
