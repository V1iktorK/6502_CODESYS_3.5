# -*- coding: utf-8 -*-
"""
probe_volume.py -- pryamoy eksperiment na OB'EM (variаnt A).

Stroim sintezicheskie FBD-POU iz N odnorodnyh blokov MOVE:
    W<k> := MOVE( V<k> )
Nikakoy semantiki yadra net. Esli hotya by odna N sozdaetsya, a drugaya net --
my naideno ogranichenie po kolichestvu. Esli NISKOLKO bolshih N sozdayutsya --
gipoteza "ob'em" oprovergnuta okonchatelno, i delo v soderzhimom yadra.

Dopolnitelno probuem variant B: tot zhe ob'em, no istochnik -- chtenie
massiva Mem[...], kak v yadre.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_volume.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"
PLCOPEN = os.path.join(ROOT, "plcopen")


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


def write(path, text):
    f = io.open(path, "wb")
    f.write(text.encode("utf-8"))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_VOLUME START ===")
import scriptengine

BIGS = [500, 600, 700, 800, 1000]

# ---------------------------------------------------------------- generaciya
made = []
for variant in (u"A", u"B"):
    for n in BIGS:
        name = u"SYN_%s_%d" % (variant, n)
        s = fbd.Sheet(u"", order_start=1)
        locs = []
        for k in range(n):
            src = u"V%d" % k if variant == u"A" else u"Mem[%d]" % k
            if variant == u"A":
                locs.append((u"V%d" % k, u"WORD"))
            a = s.ref(src, 0)
            b = s.blk(u"MOVE", [(u"", a)], 1, width=80)
            s.assign(u"W%d" % k, b, 2)
            locs.append((u"W%d" % k, u"WORD"))
        iface = fbd.interface(locals_=locs)
        xml = fbd.pou_xml(name, u"program", iface, [s], comment=u"volume probe")
        p = os.path.join(PLCOPEN, u"%s.xml" % name)
        write(p, xml)
        made.append((name, p, len(locs), n))

# deklaraciyu peredaem cherez textual_declaration posle importa -> nelzya:
# POU bez deklaracii ne sozdastsya. Poetomu deklaraciyu vstavlyaem v XML.
log(u"сгенерировано файлов: %d" % len(made))

# ---------------------------------------------------------------- proekt
BASE = os.path.join(BUILD, u"vol_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"vol_bs.project"):
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
    log(u"GVL_MEM создан")
except Exception:
    log(u"GVL_MEM: %s" % traceback.format_exc().strip().splitlines()[-1])


def children():
    names = set()
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.add(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        pass
    return names


log(u"")
log(u"%-14s %6s  %s" % (u"POU", u"блоков", u"результат"))
log(u"-" * 44)
rows = []
for name, p, nvars, n in made:
    try:
        app.import_xml(p, False)
    except Exception:
        log(u"%-14s %6d  ИСКЛЮЧЕНИЕ" % (name, n))
        rows.append((name, n, u"ИСКЛ"))
        continue
    ok = name in children()
    log(u"%-14s %6d  %s" % (name, n, u"СОЗДАН" if ok else u"НЕ СОЗДАН"))
    rows.append((name, n, u"+" if ok else u"-"))

log(u"")
okA = [r for r in rows if r[0].startswith(u"SYN_A") and r[2] == u"+"]
okB = [r for r in rows if r[0].startswith(u"SYN_B") and r[2] == u"+"]
log(u"вариант A (MOVE локальной переменной): %d из %d" % (len(okA), len(BIGS)))
log(u"вариант B (MOVE Mem[...]):            %d из %d" % (len(okB), len(BIGS)))
if len(okA) + len(okB) > 0:
    log(u"ВЫВОД: ограничение по объёму НЕ подтверждено -- большие однородные схемы создаются.")
else:
    log(u"ВЫВОД: большие однородные схемы ТОЖЕ не создаются -- ограничение по объёму ПОДТВЕРЖДЕНО.")

log(u"=== PROBE_VOLUME END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
