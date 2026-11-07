# -*- coding: utf-8 -*-
"""
probe_volume2.py -- ogranichenie ne po BLOKAM, a po RAZMERU XML / chislu elementov.

Fakty:
  FB_Decoder6502.xml   647835 bajt  -> sozdaetsya
  FB_CPU_Core.xml      964157 bajt  -> NE sozdaetsya
  PRG_CORE_L10.xml     963773 bajt  -> NE sozdaetsya
  sintez 1000 MOVEs    ~350 KB      -> sozdaetsya

Znachit porog gde-to mezhdu 350 KB i 964 KB. Strogaya proverka:
strojim odnorodnye shemy N = 1500, 2000, 2500, 3000, 4000 blokov i smotrim
razmer fajla + rezultat importa.
"""
import io
import os
import sys
import traceback

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fbd

LOG = os.path.join(ROOT, "log", "probe_volume2.log")
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
log(u"=== PROBE_VOLUME2 START ===")
import scriptengine

BIGS = [1500, 2000, 2500, 3000, 4000]
made = []
for n in BIGS:
    name = u"BIG_%d" % n
    s = fbd.Sheet(u"", order_start=1)
    locs = []
    for k in range(n):
        locs.append((u"W%d" % k, u"WORD"))
        a = s.ref(u"Mem[%d]" % (k % 65536), 0)
        b = s.blk(u"MOVE", [(u"", a)], 1, width=80)
        s.assign(u"W%d" % k, b, 2)
    xml = fbd.pou_xml(name, u"program", fbd.interface(locals_=locs), [s], comment=u"probe")
    p = os.path.join(PLCOPEN, u"%s.xml" % name)
    write(p, xml)
    made.append((name, p, os.path.getsize(p), xml.count(u"<block ")))
log(u"сгенерировано: %d" % len(made))
log(u"")
log(u"%-10s %10s %8s" % (u"POU", u"байт", u"блоков"))
for name, p, sz, nb in made:
    log(u"%-10s %10d %8d" % (name, sz, nb))

BASE = os.path.join(BUILD, u"vol2_bs.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"vol2_bs.project"):
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
log(u"%-10s %10s %8s  %s" % (u"POU", u"байт", u"блоков", u"результат"))
log(u"-" * 52)
res = []
for name, p, sz, nb in made:
    exc = None
    try:
        app.import_xml(p, False)
    except Exception:
        exc = traceback.format_exc().strip().splitlines()[-1]
    ok = name in names()
    log(u"%-10s %10d %8d  %s%s" % (name, sz, nb,
                                   u"СОЗДАН" if ok else u"НЕ СОЗДАН",
                                   (u"  (искл: %s)" % exc) if exc else u""))
    res.append((sz, nb, ok))

OK = [r for r in res if r[2]]
NG = [r for r in res if not r[2]]
log(u"")
if OK and NG:
    log(u"СОЗДАНЫ при размере до %d байт" % max(r[0] for r in OK))
    log(u"НЕ СОЗДАНЫ начиная с %d байт" % min(r[0] for r in NG))
    log(u"ПОРОГ: между %d и %d байт XML" % (max(r[0] for r in OK), min(r[0] for r in NG)))
elif OK and not NG:
    log(u"ВСЕ СОЗДАНЫ (макс %d байт) -> ограничение по размеру НЕ подтверждено" % max(r[0] for r in OK))
else:
    log(u"ВСЕ НЕ СОЗДАНЫ (!) -> ограничение по размеру ПОДТВЕРЖДЕНО, начиная с %d байт" % min(r[0] for r in NG))
log(u"=== PROBE_VOLUME2 END ===")
try:
    proj.close()
except Exception:
    pass
try:
    system.exit()
except Exception:
    pass
