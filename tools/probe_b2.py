# -*- coding: utf-8 -*-
"""
probe_b2.py -- punkt 5 algоritma: VYPOLNENIE PLANA (bloker B2, poslednie gipotezy).

Uzhe oprovergnuto 8 gipotez po FB_CPU_Core. Ostalis dve:

  G-A: POU-TYPE. Uspeшno importirovavshiysya PRG_6502 byl "program",
       a yadro -- "functionBlock". Proveryaem, vliyaet li eto.
  G-B: SHEST ZAPISEY V GVL iz odnoy shemy. Yadro pishet A, X, Y, P, SP, PC.
       Ranee proveryalas ODNA zapis (C_GVL_RW) -- ona rabotala.

Stroim chetyre POU v chistom proekte:
  T1  functionBlock, 6 zapisey v GVL_CPU   -- gipoteza G-B
  T2  program,       6 zapisey v GVL_CPU   -- gipoteza G-A + G-B
  T3  functionBlock, 1 zapis  v GVL_CPU    -- kontrol
  T4  program,       1 zapis, s logikoy    -- kontrol program-tipa

Rezultat -> log/probe_b2.log
"""
import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = r"C:\Users\Ольга\OneDrive\Рабочий стол\CODESYS\CPM6502"
PLCOPEN = os.path.join(ROOT, "plcopen")
LOG = os.path.join(ROOT, "log", "probe_b2.log")
TPL = r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Templates\TemplatePlc210_01.project"
BUILD = r"C:\CPM6502_build"

GVL6 = [u"GVL_CPU.A", u"GVL_CPU.X", u"GVL_CPU.Y", u"GVL_CPU.P",
        u"GVL_CPU.SP", u"GVL_CPU.PC"]


def log(m):
    f = io.open(LOG, "a", encoding="utf-8")
    f.write(u"%s\n" % (m,))
    f.close()


f = io.open(LOG, "w", encoding="utf-8")
f.write(u"")
f.close()
log(u"=== PROBE_B2 START ===")
import scriptengine
from fbd import Sheet, interface, pou_xml


def make(kind, n_writes):
    """POU zadannogo tipa, delayushchiy n_writes zapisey v GVL_CPU."""
    s = Sheet(u"%s, записей в GVL: %d" % (kind, n_writes))
    src = s.var(u"IN", 0)
    add = s.blk(u"ADD", [(u"IN1", src), (u"IN2", s.const(u"BYTE#1", 0))], 1)
    for i in range(n_writes):
        if GVL6[i].endswith(u".PC"):
            w = s.blk(u"BYTE_TO_WORD", [(u"IN", add)], 2)
            s.assign(GVL6[i], w, 3)
        else:
            s.assign(GVL6[i], add, 3)
    if kind == u"functionBlock":
        ifc = interface(inputs=[(u"IN", u"BYTE")], outputs=[(u"DONE", u"BOOL")])
    else:
        ifc = interface(locals_=[(u"LOC", u"BYTE")])
    return pou_xml(u"B2_%s_%d" % (kind[:3].upper(), n_writes), kind, ifc, [s], None)


def children(app):
    names = []
    try:
        for ch in app.get_children():
            s = str(ch)
            if u"Name=" in s:
                names.append(s.split(u"Name=")[1].split(u",")[0])
    except Exception:
        log(traceback.format_exc())
    return names


BASE = os.path.join(BUILD, u"base_b2.project")
for junk in os.listdir(BUILD):
    if junk.startswith(u"base_b2.project"):
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

# GVL_CPU нужна, иначе записи не разрешатся
try:
    gvl = app.create_gvl(u"GVL_CPU")
    gvl.textual_declaration.replace(
        u"VAR_GLOBAL\n\tA : BYTE;\n\tX : BYTE;\n\tY : BYTE;\n\tP : BYTE;\n"
        u"\tSP : BYTE;\n\tPC : WORD;\nEND_GLOBAL_MARK\nEND_VAR\n".replace(u"END_GLOBAL_MARK\n", u""))
    log(u"GVL_CPU создана")
except Exception:
    log(u"GVL: %s" % traceback.format_exc().strip().splitlines()[-1])

CASES = [(u"functionBlock", 6), (u"program", 6), (u"functionBlock", 1), (u"program", 1)]
ok, bad = [], []
for kind, n in CASES:
    name = u"B2_%s_%d" % (kind[:3].upper(), n)
    xp = os.path.join(PLCOPEN, u"b2_%s.xml" % name)
    ff = io.open(xp, "w", encoding="utf-8")
    ff.write(make(kind, n))
    ff.close()
    try:
        app.import_xml(xp, False)
    except Exception:
        log(u"  %-18s ИСКЛЮЧЕНИЕ: %s" % (name, traceback.format_exc().strip().splitlines()[-1]))
        bad.append(name)
        continue
    got = name in children(app)
    log(u"  %-18s (%s, записей %d) -> %s" % (name, kind, n, u"СОЗДАН" if got else u"НЕ СОЗДАН"))
    (ok if got else bad).append(name)

log(u"")
log(u"СОЗДАНЫ   : %s" % (u", ".join(ok) or u"(нет)"))
log(u"НЕ СОЗДАНЫ: %s" % (u", ".join(bad) or u"(нет)"))
log(u"")
log(u"Толкование:")
log(u"  FB с 6 записями не создан, а с 1 создан  -> виноваты ШЕСТЬ записей в GVL (G-B)")
log(u"  program с 6 записями создан            -> pouType ни при чём (G-A опровергнута)")
log(u"  всё создано                            -> обе гипотезы опровергнуты")
try:
    proj.close()
except Exception:
    pass
log(u"=== PROBE_B2 END ===")
try:
    system.exit()
except Exception:
    pass
